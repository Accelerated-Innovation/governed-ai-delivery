"""Behavior tests for the ADR approval gate's embedded checker.

This gate exists because `govkit validate` structurally cannot do its job: the
working tree holds no reviews, so validate can prove `governance/approval_policy.yaml`
is well-formed and report an ADR claiming `Accepted` with nothing behind it, but
it can never prove an approval happened. Only the reviews API can, and only CI
has it.

Following `tests/test_fix_lane_gate_checks.py`: extract the heredoc, execute it
against fixtures, and pin the two platform embeddings identical so they cannot
drift. Asserting on the YAML text would prove only that words are present —
these tests run the checker.

Like the fix-lane gate, this one is deliberately self-contained. It never
invokes govkit: a blocking gate must not depend on an unpinned PyPI release, and
`run_validation` exits 0 on a missing marker, so a gate delegating to it could be
switched off from inside the PR it is reviewing.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE_PATHS = {
    "github": REPO_ROOT / "ci" / "github" / "adr-approval-gate.yml",
    "azure": REPO_ROOT / "ci" / "azure" / "adr-approval-gate.yml",
}

HEAD_SHA = "2f8c1ab9d4e6f70123456789abcdef0123456789"
OLD_SHA = "1111111111111111111111111111111111111111"
APPROVER = "octo-architect"
SENTINEL = "YOUR_APPROVER_LOGIN"
ADR_REL = "docs/backend/architecture/ADR/0001-service-layer.md"


def _extract_checker(gate_path: Path) -> str:
    raw = gate_path.read_text(encoding="utf-8")
    marker = "python - <<'EOF'\n"
    start = raw.index(marker) + len(marker)
    body = []
    for line in raw[start:].splitlines():
        if line.strip() == "EOF":
            break
        body.append(line)
    return textwrap.dedent("\n".join(body)) + "\n"


def _adr(status: str = "Accepted", approval: str | None = None) -> str:
    text = (
        "# ADR-0001: Introduce a service layer\n\n"
        f"## Status\n{status}\n\n## 1. Context\n\nWhy.\n"
    )
    if approval:
        text += f"\n## 10. Approval\n{approval}\n"
    return text


def _govkit_authored(body: str, tamper: bool = False) -> str:
    """Reproduce what `cli.headers.prepend_header_to_file` writes on install."""
    from cli.headers import format_editable_header

    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if tamper:
        body += "\n## 2. Decision\n\nOurs now.\n"
    return format_editable_header(baseline="0.18.0", body_hash=digest) + body


def _policy(
    approvers: list[dict] | None = None, **extra,
) -> dict:
    if approvers is None:
        approvers = [{"login": APPROVER, "role": "approver"}]
    return {"version": 1, "approvers": approvers, **extra}


def _run(
    tmp_path: Path,
    changed: list[str],
    *,
    files: dict[str, str] | None = None,
    policy: dict | str | None = None,
    reviews: list[dict] | None = None,
    head_sha: str = HEAD_SHA,
    platform: str = "github",
) -> subprocess.CompletedProcess:
    for rel, text in (files or {}).items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    if policy is not None:
        path = tmp_path / "governance" / "approval_policy.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            policy if isinstance(policy, str)
            else yaml.safe_dump(policy, sort_keys=False),
            encoding="utf-8",
        )

    (tmp_path / "reviews.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in (reviews or [])), encoding="utf-8",
    )

    script = tmp_path / "_gate.py"
    script.write_text(_extract_checker(GATE_PATHS[platform]), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        input="\n".join(changed),
        capture_output=True,
        text=True,
        env={"HEAD_SHA": head_sha, "PATH": "", "SYSTEMROOT": ""},
    )


def _approval(login: str = APPROVER, commit: str = HEAD_SHA, state: str = "APPROVED"):
    return {"login": login, "state": state, "commit_id": commit}


def test_checker_extraction_is_not_empty():
    """Non-vacuous guard: a changed heredoc marker would make every test below
    run an empty script and trivially pass."""
    body = _extract_checker(GATE_PATHS["github"])
    assert "approval_policy.yaml" in body and "commit_id" in body, body[:300]


class TestNothingToAttest:
    def test_no_adr_changed_passes(self, tmp_path):
        result = _run(tmp_path, [], policy=_policy())
        assert result.returncode == 0, result.stdout
        assert "No ADR changed" in result.stdout

    def test_the_template_is_not_an_adr(self, tmp_path):
        """`Proposed | Accepted | Rejected | Superseded` is the vocabulary menu.
        Editing the template is not accepting a decision."""
        result = _run(
            tmp_path,
            ["docs/backend/architecture/ADR/TEMPLATE.md"],
            files={
                "docs/backend/architecture/ADR/TEMPLATE.md":
                    _adr(status="Proposed | Accepted | Rejected | Superseded"),
            },
            policy=_policy(),
        )
        assert result.returncode == 0, result.stdout

    def test_a_proposed_adr_needs_no_approval(self, tmp_path):
        """The agent authors Proposed and stops; that is the point of the skill
        change, and this is the gate agreeing with it."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr(status="Proposed")},
            policy=_policy(),
        )
        assert result.returncode == 0, result.stdout
        assert "nothing to attest" in result.stdout

    def test_a_deleted_adr_is_not_read(self, tmp_path):
        """--diff-filter=d keeps deletions out of the list; if one slipped
        through, the checker must not crash on the missing file."""
        result = _run(tmp_path, [], policy=_policy())
        assert result.returncode == 0, result.stdout


class TestFailsClosed:
    def test_unconfigured_policy_fails_on_an_accepted_adr(self, tmp_path):
        """The opposite of the fix-lane gate's inert sentinel, deliberately: an
        ADR cannot be accepted in a repo that declares nobody able to accept it."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy=_policy([{"login": SENTINEL, "role": "approver"}]),
            reviews=[_approval()],
        )
        assert result.returncode == 1, result.stdout
        assert "names no approver" in result.stdout

    def test_a_fresh_install_touching_no_adr_stays_green(self, tmp_path):
        """Failing closed must not mean failing on arrival."""
        result = _run(
            tmp_path, [], policy=_policy([{"login": SENTINEL, "role": "approver"}]),
        )
        assert result.returncode == 0, result.stdout

    def test_a_missing_policy_fails(self, tmp_path):
        result = _run(tmp_path, [ADR_REL], files={ADR_REL: _adr()}, reviews=[_approval()])
        assert result.returncode == 1, result.stdout
        assert "is missing" in result.stdout

    def test_a_malformed_policy_fails(self, tmp_path):
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy="approvers: [unclosed\n", reviews=[_approval()],
        )
        assert result.returncode == 1, result.stdout

    def test_a_policy_that_is_not_a_mapping_fails(self, tmp_path):
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy="- a\n- list\n", reviews=[_approval()],
        )
        assert result.returncode == 1, result.stdout

    def test_no_head_sha_fails_rather_than_matching_everything(self, tmp_path):
        """An empty HEAD_SHA against an empty commit_id would compare equal and
        wave through an unbound approval."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()}, policy=_policy(),
            reviews=[_approval(commit="")], head_sha="",
        )
        assert result.returncode == 1, result.stdout
        assert "head SHA" in result.stdout


class TestIdentityAndAuthority:
    def test_an_approver_at_the_head_sha_passes(self, tmp_path):
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()}, policy=_policy(),
            reviews=[_approval()],
        )
        assert result.returncode == 0, result.stdout
        assert APPROVER in result.stdout

    def test_no_approval_at_all_fails(self, tmp_path):
        """The whole point: `Accepted` was true because someone typed it."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()}, policy=_policy(),
        )
        assert result.returncode == 1, result.stdout
        assert "no authorised" in result.stdout

    def test_a_reviewer_cannot_accept_an_adr(self, tmp_path):
        """AUTHORITY_AND_APPROVAL_CONTRACT.md: 'a reviewer does not gain approval
        authority'. Their review is authenticated and still insufficient."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy=_policy([{"login": "octo-qa", "role": "reviewer"}]),
            reviews=[_approval(login="octo-qa")],
        )
        assert result.returncode == 1, result.stdout

    def test_an_identity_absent_from_the_policy_cannot_accept(self, tmp_path):
        """'Approval by an unauthorized identity' — a prohibited pattern. An
        authenticated review is not, by itself, an approval."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()}, policy=_policy(),
            reviews=[_approval(login="passing-stranger")],
        )
        assert result.returncode == 1, result.stdout

    def test_a_non_approving_review_does_not_count(self, tmp_path):
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()}, policy=_policy(),
            reviews=[_approval(state="COMMENTED")],
        )
        assert result.returncode == 1, result.stdout

    def test_an_approval_of_an_earlier_push_does_not_carry(self, tmp_path):
        """Approval is bound to a commit. Reusing it for a later one is
        'reusing stale activation authority' — the contract's own words."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()}, policy=_policy(),
            reviews=[_approval(commit=OLD_SHA)],
        )
        assert result.returncode == 1, result.stdout

    def test_a_scoped_approver_cannot_accept_outside_their_scope(self, tmp_path):
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy=_policy([{
                "login": APPROVER, "role": "approver",
                "scope": ["docs/data/architecture/ADR/"],
            }]),
            reviews=[_approval()],
        )
        assert result.returncode == 1, result.stdout

    def test_a_scoped_approver_accepts_inside_their_scope(self, tmp_path):
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy=_policy([{
                "login": APPROVER, "role": "approver",
                "scope": ["docs/backend/architecture/ADR/"],
            }]),
            reviews=[_approval()],
        )
        assert result.returncode == 0, result.stdout

    def test_every_accepted_adr_needs_its_own_cover(self, tmp_path):
        second = "docs/data/architecture/ADR/0002-marts.md"
        result = _run(
            tmp_path, [ADR_REL, second],
            files={ADR_REL: _adr(), second: _adr()},
            policy=_policy([{
                "login": APPROVER, "role": "approver",
                "scope": ["docs/backend/"],
            }]),
            reviews=[_approval()],
        )
        assert result.returncode == 1, result.stdout
        assert second in result.stdout


class TestGovkitAuthoredAdrs:
    """govkit ships exactly one real ADR — `docs/data/architecture/ADR/0001-...`
    — it says Accepted, it has no approval record, and it lands in every
    `--type data` install at L3, L4 and L5 as a governed file `upgrade`
    rewrites. Without this carve-out the gate would fail every data customer's
    repo, which is the exact defect class PR #133 existed to fix."""

    DATA_ADR = "docs/data/architecture/ADR/0001-data-features-skip-prediction-gate.md"

    def test_an_unmodified_govkit_adr_needs_no_customer_approval(self, tmp_path):
        result = _run(
            tmp_path, [self.DATA_ADR],
            files={self.DATA_ADR: _govkit_authored(_adr())},
            policy=_policy(),
        )
        assert result.returncode == 0, result.stdout
        assert "govkit-authored" in result.stdout

    def test_editing_a_govkit_adr_makes_it_the_teams_decision(self, tmp_path):
        result = _run(
            tmp_path, [self.DATA_ADR],
            files={self.DATA_ADR: _govkit_authored(_adr(), tamper=True)},
            policy=_policy(),
        )
        assert result.returncode == 1, result.stdout

    def test_a_customer_adr_cannot_borrow_the_carve_out_without_a_real_hash(
        self, tmp_path,
    ):
        """A hand-written header with a wrong hash must not buy silence."""
        forged = (
            "<!-- govkit:editable\n  baseline: 0.18.0\n"
            f"  hash: {'0' * 64}\n  see: GOVKIT_SETUP_REVIEW.md\n-->\n\n"
        ) + _adr()
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: forged}, policy=_policy(),
        )
        assert result.returncode == 1, result.stdout


class TestScopeConfiguration:
    def test_require_approval_for_narrows_what_the_gate_covers(self, tmp_path):
        other = "docs/data/architecture/ADR/0002-marts.md"
        result = _run(
            tmp_path, [other], files={other: _adr()},
            policy=_policy(require_approval_for=["docs/backend/"]),
        )
        assert result.returncode == 0, result.stdout


def test_platform_embeddings_are_identical():
    github = _extract_checker(GATE_PATHS["github"])
    azure = _extract_checker(GATE_PATHS["azure"])
    assert github == azure, "github and azure adr-approval checkers have drifted"


@pytest.mark.parametrize("platform", sorted(GATE_PATHS))
def test_the_azure_embedding_behaves_identically(tmp_path, platform):
    """Running the azure copy proves the dedent equality above is not the only
    thing standing between the platforms."""
    result = _run(
        tmp_path, [ADR_REL], files={ADR_REL: _adr()}, policy=_policy(),
        reviews=[_approval()], platform=platform,
    )
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("platform", sorted(GATE_PATHS))
def test_gate_does_not_invoke_govkit(platform):
    """Self-contained by design, for the same reason the fix-lane gate is: a
    blocking gate must not depend on an unpinned PyPI release, and a gate
    delegating to `govkit validate` could be switched off from inside the PR it
    is reviewing."""
    text = GATE_PATHS[platform].read_text(encoding="utf-8")
    invocations = [
        ln for ln in text.splitlines()
        if ln.strip().startswith(("run: govkit", "- script: govkit", "govkit "))
    ]
    assert not invocations, invocations


def test_github_gate_declares_least_privilege_permissions():
    """The payload's first `permissions:` block. Reading reviews needs
    pull-requests: read; declaring the block drops every other scope to none, so
    contents: read has to be restated for checkout."""
    parsed = yaml.safe_load(GATE_PATHS["github"].read_text(encoding="utf-8"))
    assert parsed["permissions"] == {"contents": "read", "pull-requests": "read"}


def test_the_gate_job_name_is_the_one_the_docs_tell_teams_to_require():
    parsed = yaml.safe_load(GATE_PATHS["github"].read_text(encoding="utf-8"))
    assert "adr-approval-check" in parsed["jobs"]


@pytest.mark.parametrize("agent", ["claude-code", "codex", "copilot"])
@pytest.mark.parametrize("ci", ["github", "azure"])
def test_the_gate_ships_wherever_the_policy_does(agent, ci):
    """The policy without the gate is a file nothing reads — the state this
    work exists to end. They must arrive together."""
    from cli.manifest import load_manifest, resolve_variant_files

    manifest = load_manifest(agent)
    for project_type in ("api", "cli", "ui-react", "ui-angular", "ui-nextjs", "data"):
        for level in ("3", "4", "5"):
            if project_type == "data" and level == "5":
                continue  # data is an L3/L4 shape; dbt has no L5 tier.
            _files, shared, governed = resolve_variant_files(
                manifest,
                {"level": level, "type": project_type, "ci": ci,
                 "stack": "python-dbt" if project_type == "data" else "python-fastapi"},
            )
            where = f"{agent} {project_type} L{level} ({ci})"
            assert (
                (f"ci/{ci}/adr-approval-gate.yml" in governed)
                == ("governance/approval_policy.yaml" in shared)
            ), where
