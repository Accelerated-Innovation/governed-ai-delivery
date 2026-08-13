#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""ADR approval attestation — the working-tree half.

`Accepted` was a word someone typed. The L4 governance rule gates
implementation on it and nothing in `cli/` or `ci/` had ever read it.
`governance/approval_policy.yaml` makes it derivable by naming which identities
hold approval authority; this module proves that policy is well-formed and
reports ADRs claiming `Accepted` with nothing standing behind the claim.

**What this module cannot do, by construction.** The working tree holds no
reviews, so it cannot prove an approval happened — only `ci/*/adr-approval-gate`
can, where the diff and the reviews API exist. The split is the same one the
defect lane draws: validate proves internal consistency, CI proves
correspondence with reality.

Modelled on `cli/fixes.py`: its own module, the `(issues, warnings)` ABI
(`CheckStatus` lives in `cli/validate.py`, which imports this, so sharing the
type would make a cycle), and silent when absent.

**Everything here is a warning, never an issue, except a malformed policy.**
That is the migration posture — warn on pre-existing, fail on changed — and it
is not politeness. govkit ships exactly one real ADR
(`docs/data/architecture/ADR/0001-...`), it says `Accepted`, it has no Approval
section at all, and it lands in every `--type data` install. A hard check would
have failed every data customer's repo on their next upgrade, which is the exact
defect class PR #133 existed to fix.
"""

import re
import subprocess
from pathlib import Path

import yaml

from .headers import compute_body_hash, has_editable_header, parse_editable_header

POLICY_REL = Path("governance") / "approval_policy.yaml"
SCHEMA_REL = Path("governance") / "schemas" / "approval_policy.schema.json"

# Where the shipped templates put ADRs, for every project type.
ADR_GLOB = "docs/*/architecture/ADR/*.md"
TEMPLATE_NAME = "TEMPLATE.md"

# The status the L4 rule gates implementation on.
GATE_STATUS = "Accepted"

# The one role that confers approval authority. AUTHORITY_AND_APPROVAL_CONTRACT.md:
# "a reviewer does not gain approval authority."
APPROVER_ROLE = "approver"

# Shipped inert. Mirrors repo-scope-check's REPO_OWNER and the fix-lane gate's
# SOURCE_PATHS, so a fresh install stays green rather than failing on arrival.
SENTINEL_LOGIN = "YOUR_APPROVER_LOGIN"

# The `## Status` line, as parsed in tests/test_adr_contract_consistency.py.
_STATUS_RE = re.compile(r"^## Status\s*\n(.+)$", re.MULTILINE)

# Two ADR vocabularies ship from govkit: the templates emit `## 10. Approval`
# (UI numbers it `## 11.`), the adr-author skill teaches `## Review`. A
# customer's ADR may carry either, so the parser tolerates both — and the
# numbered prefix, which `check_nfrs_sections`'s `^##\s+<name>` would miss.
_APPROVAL_SECTION_RE = re.compile(
    r"^##\s+(?:\d+\.\s*)?(?:Approval|Review)\b.*$", re.MULTILINE | re.IGNORECASE,
)

# A colon-terminated label with nothing after it. The shipped template's
# Approval section is three of these — bound to no identity, no date, no commit
# — so a section made only of them is empty for this purpose.
_EMPTY_LABEL_RE = re.compile(r"^\s*(?:[-*]\s*)?[A-Za-z][^:\n]*:\s*$", re.MULTILINE)


def discover_adrs(target: Path) -> list[Path]:
    """Every ADR in the target, template excluded.

    Returns [] when there is no docs tree — absence is not a finding. Never
    raises: an unreadable tree yields nothing rather than a traceback.
    """
    try:
        found = sorted(target.glob(ADR_GLOB))
    except OSError:
        return []
    return [p for p in found if p.is_file() and p.name != TEMPLATE_NAME]


def parse_adr_status(text: str) -> str | None:
    """The declared status, or None when there is no parseable `## Status`.

    The template's own line is the vocabulary menu
    (`Proposed | Accepted | Rejected | Superseded`), which is returned verbatim
    and so never equals `Accepted` — a menu is not a claim.
    """
    match = _STATUS_RE.search(text)
    return match.group(1).strip() if match else None


def _section_body(text: str, match: re.Match) -> str:
    nxt = re.search(r"^##\s", text[match.end():], re.MULTILINE)
    return text[match.end():match.end() + nxt.start()] if nxt else text[match.end():]


def has_approval_record(text: str) -> bool:
    """Does an Approval/Review section carry anything at all?

    Populated means real content after HTML comments and bare colon-terminated
    labels are stripped. `Approved by:` with nothing after the colon records
    nothing, which is precisely the state this work exists to end.
    """
    for match in _APPROVAL_SECTION_RE.finditer(text):
        body = _section_body(text, match)
        body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
        body = _EMPTY_LABEL_RE.sub("", body)
        if body.strip():
            return True
    return False


def is_govkit_authored(text: str) -> bool:
    """Is this ADR govkit's own decision, unmodified by the team?

    Reuses the edit-protection machinery rather than inventing a marker:
    `cli/headers.py` writes a `govkit:editable` header carrying a SHA-256 of the
    body it installed, so a matching hash means govkit wrote it and nobody has
    touched it since.

    A header with no `hash:` field — a pre-hash install — counts as govkit's.
    The alternative is warning a data customer about the ADR govkit put in their
    repo, and under a warn-only migration posture, a false silence costs less
    than a false alarm on a file the team never authored.
    """
    if not has_editable_header(text):
        return False
    fields = parse_editable_header(text) or {}
    if "hash" not in fields:
        return True
    return compute_body_hash(text) == fields["hash"]


def _load_policy(target: Path) -> tuple[dict | None, list[str]]:
    """Read the policy. Returns (data, issues); data is None when unusable."""
    path = target / POLICY_REL
    rel = POLICY_REL.as_posix()
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, [f"{rel} could not be read: {exc}"]
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return None, [f"{rel} could not be parsed: {exc}"]
    if not isinstance(data, dict):
        return None, [f"{rel} is not a YAML mapping"]
    if not isinstance(data.get("approvers"), list):
        return None, [f"{rel} must declare an `approvers` list"]
    return data, []


def _validate_against_schema(target: Path) -> tuple[list[str], list[str]]:
    """Instance validation with the three-tier degradation `check_eval_criteria`
    established: a missing schema or absent tool is a visible warning, never a
    silent pass."""
    rel = POLICY_REL.as_posix()
    schema = target / SCHEMA_REL
    if not schema.is_file():
        return [], [
            f"{rel} instance validation skipped — no approval_policy schema installed"
        ]
    try:
        result = subprocess.run(
            ["check-jsonschema", "--schemafile", str(schema), str(target / POLICY_REL)],
            capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return [], [
            f"{rel} instance validation skipped — "
            "install check-jsonschema for full validation"
        ]
    if result.returncode != 0:
        detail = (result.stdout or result.stderr or "").strip().splitlines()
        snippet = detail[-1] if detail else "schema validation failed"
        return [f"{rel} fails {schema.name}: {snippet}"], []
    return [], []


def resolve_approvers(policy: dict) -> list[str]:
    """The logins that actually hold approval authority.

    Reviewers are excluded by design, and so is the shipped sentinel: a policy
    nobody has edited authorises nobody. Both exclusions exist so "no findings"
    can never be mistaken for "attestation is on".
    """
    return [
        entry["login"]
        for entry in policy.get("approvers") or []
        if isinstance(entry, dict)
        and entry.get("role") == APPROVER_ROLE
        and isinstance(entry.get("login"), str)
        and entry["login"].strip()
        and entry["login"] != SENTINEL_LOGIN
    ]


def _in_scope(rel: str, prefixes: list) -> bool:
    if not prefixes:
        return True
    return any(rel.startswith(p) for p in prefixes if isinstance(p, str))


def check_approval_policy(target: Path) -> tuple[list[str], list[str]]:
    """Return (issues, warnings) for the target's ADR approval attestation.

    Silent when the repo has neither ADRs nor a policy — a repo that never
    adopted this sees no change, the same contract the defect lane carries.
    """
    adrs = discover_adrs(target)
    policy_path = target / POLICY_REL
    rel = POLICY_REL.as_posix()

    if not adrs and not policy_path.is_file():
        return [], []

    if not policy_path.is_file():
        return [], [
            f"{len(adrs)} ADR(s) present but no {rel} — `Accepted` cannot be "
            "derived from an approval until the policy names who may give one "
            "(run `govkit upgrade` to install it)"
        ]

    policy, issues = _load_policy(target)
    if policy is None:
        return issues, []

    schema_issues, warnings = _validate_against_schema(target)
    if schema_issues:
        return schema_issues, warnings

    approvers = resolve_approvers(policy)
    if not approvers:
        warnings.append(
            f"{rel} names no approver — attestation is not configured. Replace "
            f"{SENTINEL_LOGIN} with the login(s) that hold approval authority "
            "here; a reviewer does not gain it (AUTHORITY_AND_APPROVAL_CONTRACT.md)"
        )

    warnings += _check_adrs(target, adrs, policy.get("require_approval_for") or [])
    return [], warnings


def _check_adrs(target: Path, adrs: list[Path], scope: list) -> list[str]:
    warnings = []
    for path in adrs:
        rel = path.relative_to(target).as_posix()
        if not _in_scope(rel, scope):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            warnings.append(f"{rel} could not be read: {exc}")
            continue
        if parse_adr_status(text) != GATE_STATUS:
            continue
        # govkit's own decision, unmodified. Requiring a customer's approver to
        # attest a decision govkit made for them is incoherent.
        if is_govkit_authored(text):
            continue
        if has_approval_record(text):
            continue
        warnings.append(
            f"{rel} claims {GATE_STATUS} with no approval record — "
            f"{GATE_STATUS} is derived from an approving review by an approver "
            f"in {POLICY_REL.as_posix()}, which the adr-approval-check CI gate "
            "verifies against the head SHA"
        )
    return warnings
