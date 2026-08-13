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
"""Defect lane — discovery and validation of `fixes/<id>/fix.yaml`.

The L4 contract is feature-shaped: five prose artifacts for every governed
change. A defect that restores already-established behavior carries one
schema-backed record instead.

Modelled on `cli/extensions.py`, the repo's existing second artifact family:
a separate directory, a separate module, a distinct check ABI, and silent when
absent. It deliberately does not reuse the feature protocol — `list_user_features`
applies no content filter, so anything under `features/` is put through the
five-artifact gauntlet, and `_run_feature_checks` hardcodes the `features/`
prefix in its output.

The ABI returns `(issues, warnings)` rather than the feature `(CheckStatus, str)`:
`CheckStatus` lives in `cli/validate.py`, which imports this module, so sharing
the type would create a cycle. Warnings carry the same "visible gaps, not silent
green" contract as `check_eval_criteria`.
"""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath

import yaml

FIXES_DIR = "fixes"
FIX_RECORD_FILE = "fix.yaml"
SCHEMA_REL = Path("governance") / "schemas" / "fix_record.schema.json"

# Mirrors the schema's top-level `required`. Checked in-process so a malformed
# record fails even where check-jsonschema is unavailable.
_REQUIRED_KEYS = (
    "version",
    "id",
    "summary",
    "expectation",
    "failure",
    "surface",
    "reproduction",
    "risk",
    "introduces_new_behavior",
)

# Written by `govkit fix init`. There is no shipped template file: a third copy
# of this shape would be a drift surface, so the generator is pinned directly to
# the schema by test_skeleton_validates_against_the_shipped_schema.
FIX_RECORD_SKELETON = """\
version: 1
id: {id}
summary: TODO - one line stating the defect, in the language of the behavior

# Condition 1 - what already established this behavior. A fix that cannot cite a
# source is introducing behavior, not restoring it, and belongs in the feature
# lane. This path must resolve.
expectation:
  source: TODO/path/to/spec-contract-or-adr
  reference: TODO - the scenario, section, or clause

failure:
  observed: TODO - what actually happens
  reported_in: TODO - issue or incident reference

# Condition 4 input. Cross-checked against the risk flags below.
surface:
  paths:
    - TODO/path/to/changed/file

# Condition 2 - the test that fails before the fix and passes after. Must resolve.
reproduction:
  test: TODO/path/to/regression_test
  scenario: TODO - the test case name

# Condition 4. Every flag is required so an omission cannot read as false.
# A `true` does not waive anything - it means the change belongs in the feature
# lane, and govkit validate will say so.
risk:
  architecture: false
  security_auth: false
  data_handling: false
  public_contract: false
  nfr: false
  cross_service: false

# Condition 3. `true` promotes the change to the feature lane.
introduces_new_behavior: false

evidence: []
"""


@dataclass
class FixRecord:
    """One `fixes/<id>/fix.yaml`. `errors` carries discovery failures — a
    missing or unparseable record — so discovery never raises."""

    id: str
    root: Path
    path: Path
    data: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def rel(self) -> str:
        return f"{FIXES_DIR}/{self.id}/{FIX_RECORD_FILE}"


def discover_fix_records(target: Path) -> list[FixRecord]:
    """Scan `<target>/fixes/*/fix.yaml`.

    Returns [] when the directory is absent — repos without a defect lane see
    no change. Dot-directories and loose files are skipped. Never raises: a
    record that cannot be read carries the reason in `.errors`.
    """
    root = target / FIXES_DIR
    try:
        if not root.is_dir():
            return []
        entries = sorted(root.iterdir())
    except OSError:
        return []

    records = []
    for entry in entries:
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        records.append(_load_record(entry))
    return records


def _load_record(root: Path) -> FixRecord:
    path = root / FIX_RECORD_FILE
    record = FixRecord(id=root.name, root=root, path=path)
    if not path.is_file():
        record.errors.append(f"{record.rel} not found")
        return record
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        record.errors.append(f"{record.rel} could not be parsed: {exc}")
        return record
    if not isinstance(data, dict):
        record.errors.append(f"{record.rel} is not a YAML mapping")
        return record
    record.data = data
    return record


def _check_required_keys(record: FixRecord) -> list[str]:
    missing = [k for k in _REQUIRED_KEYS if k not in record.data]
    if not missing:
        return []
    return [f"{record.rel} missing required key(s): {', '.join(missing)}"]


_RISK_FLAGS = (
    "architecture",
    "security_auth",
    "data_handling",
    "public_contract",
    "nfr",
    "cross_service",
)

_MAPPING_SECTIONS = ("expectation", "failure", "surface", "reproduction", "risk")


def _nonempty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _check_nested_structure(record: FixRecord) -> list[str]:
    """Enforce the nested contract in-process, not only via check-jsonschema.

    The record is the *whole* governance artifact for a defect-lane change, so a
    structurally incomplete one cannot be allowed through on a warning when the
    schema or the validator binary is unavailable. Reduced coverage is worth a
    warning; a missing `expectation.source` is not.

    Mirrors `governance/schemas/fix_record.schema.json`. Kept deliberately
    narrow — required-and-typed only — so the schema stays the detailed
    authority and this does not become a second, drifting copy of it.
    """
    data = record.data
    wrong_type = [
        f"{record.rel} {section} must be a mapping"
        for section in _MAPPING_SECTIONS
        if section in data and not isinstance(data[section], dict)
    ]
    if wrong_type:
        # Everything below indexes into these sections.
        return wrong_type

    issues = []
    if not _nonempty_str((data.get("expectation") or {}).get("source")):
        issues.append(f"{record.rel} expectation.source must be a non-empty string")
    if not _nonempty_str((data.get("failure") or {}).get("observed")):
        issues.append(f"{record.rel} failure.observed must be a non-empty string")
    if not _nonempty_str((data.get("reproduction") or {}).get("test")):
        issues.append(f"{record.rel} reproduction.test must be a non-empty string")

    paths = (data.get("surface") or {}).get("paths")
    if not isinstance(paths, list) or not paths or not all(_nonempty_str(p) for p in paths):
        issues.append(
            f"{record.rel} surface.paths must be a non-empty list of strings"
        )

    risk = data.get("risk") or {}
    issues += [
        f"{record.rel} risk.{flag} must be present and boolean"
        for flag in _RISK_FLAGS
        if not isinstance(risk.get(flag), bool)
    ]
    if not isinstance(data.get("introduces_new_behavior"), bool):
        issues.append(f"{record.rel} introduces_new_behavior must be boolean")
    return issues


def _check_id_matches_directory(record: FixRecord) -> list[str]:
    declared = record.data.get("id")
    if declared is None or declared == record.id:
        return []
    return [
        f"{record.rel} declares id '{declared}' but sits in directory "
        f"'{record.id}' — they must match"
    ]


# Risk flags govkit can contradict from a path alone, because govkit *owns* the
# namespace and its meaning is definitional rather than inferred.
#
# security_auth, data_handling and cross_service are deliberately absent. There
# is no govkit-owned directory that definitionally means "security" or "data
# handling", and services are declared in skill_context.yaml rather than implied
# by a path. Inventing a glob for those would manufacture false contradictions;
# those declarations stand alone here and are checked against the real diff in CI.
_GOVERNED_AREA_PATTERNS = {
    "architecture": re.compile(r"^docs/[^/]+/architecture/"),
    "nfr": re.compile(r"^features/[^/]+/nfrs\.md$"),
    # The area segment is optional: per-type schemas live at
    # governance/<area>/schemas/, area-agnostic ones at governance/schemas/.
    "public_contract": re.compile(r"^governance/([^/]+/)?schemas/"),
}


def _posix(path: str) -> str:
    """Normalise separators for pattern matching.

    Only a leading `./` is stripped, and only once. The previous
    `lstrip("./")` removed *every* leading `.` and `/`, which turned `../x`
    into `x` — silently erasing an escape — and `.hidden/x` into `hidden/x`.
    """
    return path.replace("\\", "/").removeprefix("./")


def _check_safe_path(
    label: str, path: object, target: Path, hint: str, *, must_be_file: bool = True,
) -> list[str]:
    """Resolve `path` against `target` and require it to be relative, contained,
    existing, and a file.

    Mirrors `cli/extensions.py::_check_safe_file_path`. A fix record is authored
    — often by an agent — so "does this path exist" is the wrong question on its
    own; "is it inside the repository it claims to describe" is the one that
    stops an absolute path or a `..` from reaching outside.
    """
    if not isinstance(path, str) or not path.strip():
        return [f"{label} must be a non-empty string"]
    # Path.is_absolute() is host-specific: "/etc/passwd" is not absolute on
    # Windows (no drive), and "C:\\x" is not absolute on POSIX. Check both so
    # neither flavour slips through on either platform.
    if PurePosixPath(path).is_absolute() or PureWindowsPath(path).is_absolute():
        return [f"{label}: {path!r} must be relative to the repository, not absolute"]
    base = target.resolve()
    candidate = (target / path).resolve(strict=False)
    if not candidate.is_relative_to(base):
        return [f"{label}: {path!r} resolves outside the repository"]
    if not candidate.exists():
        return [f"{label} '{path}' does not resolve — {hint}"]
    if must_be_file and not candidate.is_file():
        return [f"{label}: {path!r} is not a file"]
    return []


def _check_paths_resolve(record: FixRecord, target: Path) -> list[str]:
    """Conditions 1 and 2 are assertions until their paths resolve — inside the
    repository, and at a file rather than a directory."""
    issues = []
    issues += _check_safe_path(
        f"{record.rel} expectation.source",
        (record.data.get("expectation") or {}).get("source"),
        target,
        "a fix that cannot cite what established the behavior is introducing it, "
        "and belongs in the feature lane",
    )
    issues += _check_safe_path(
        f"{record.rel} reproduction.test",
        (record.data.get("reproduction") or {}).get("test"),
        target,
        "the light lane requires a test that fails before the fix",
    )
    for path in (record.data.get("surface") or {}).get("paths") or []:
        issues += _check_safe_path(
            f"{record.rel} surface.paths",
            path,
            target,
            "surface.paths names the files the fix changes",
        )
    return issues


def _check_lane_membership(record: FixRecord) -> list[str]:
    """A declared risk is not a waiver. Any `true` means this change is outside
    the light lane — it belongs in the feature lane, and where the contract
    requires it, behind an ADR."""
    issues = []
    raised = sorted(
        flag for flag, value in (record.data.get("risk") or {}).items() if value is True
    )
    if raised:
        issues.append(
            f"{record.rel} declares risk.{', risk.'.join(raised)} — this change "
            "belongs in the feature lane, not the fix lane"
        )
    if record.data.get("introduces_new_behavior") is True:
        issues.append(
            f"{record.rel} declares introduces_new_behavior — restoring "
            "established behavior is what this lane is for; new behavior "
            "belongs in the feature lane"
        )
    return issues


def _check_risk_matches_surface(record: FixRecord) -> list[str]:
    """The other side of the two-sided check: a `false` beside a change in a
    govkit-owned namespace is a contradiction.

    Note this compares two *declared* fields — `surface.paths` is authored, not
    derived from a diff — so it proves the record is internally consistent, not
    that it matches what the PR changed. That correspondence is CI's job, where
    the diff exists.
    """
    risk = record.data.get("risk") or {}
    paths = [_posix(p) for p in ((record.data.get("surface") or {}).get("paths") or []) if isinstance(p, str)]
    issues = []
    for flag, pattern in _GOVERNED_AREA_PATTERNS.items():
        if risk.get(flag) is not False:
            continue
        hits = [p for p in paths if pattern.search(p)]
        if hits:
            issues.append(
                f"{record.rel} declares risk.{flag} false but changes "
                f"{', '.join(hits)} — that is a {flag} change, so the record "
                "contradicts itself"
            )
    return issues


def _validate_against_schema(
    record: FixRecord, target: Path,
) -> tuple[list[str], list[str]]:
    """Instance validation, with the three-tier degradation `check_eval_criteria`
    established: a missing schema or absent tool is a visible warning, never a
    silent pass."""
    schema = target / SCHEMA_REL
    if not schema.is_file():
        return [], [
            f"{record.rel} instance validation skipped — "
            "no fix_record schema installed"
        ]
    try:
        result = subprocess.run(
            ["check-jsonschema", "--schemafile", str(schema), str(record.path)],
            capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return [], [
            f"{record.rel} instance validation skipped — "
            "install check-jsonschema for full validation"
        ]
    if result.returncode != 0:
        detail = (result.stdout or result.stderr or "").strip().splitlines()
        snippet = detail[-1] if detail else "schema validation failed"
        return [f"{record.rel} fails {schema.name}: {snippet}"], []
    return [], []


def validate_fix_record(
    record: FixRecord, target: Path,
) -> tuple[list[str], list[str]]:
    """Return (issues, warnings) for one fix record.

    Issues fail the run; warnings surface a gap without failing it. Structural
    checks run first and short-circuit — there is no value in schema output
    about a record that is missing half its keys.
    """
    if record.errors:
        return list(record.errors), []

    issues = [
        *_check_required_keys(record),
        *_check_id_matches_directory(record),
    ]
    if issues:
        return issues, []

    # In-process nested checks run regardless of tooling availability, and the
    # schema check still runs so its warning is visible alongside them — a
    # reader needs to know coverage was reduced *and* what was already wrong.
    nested = _check_nested_structure(record)
    schema_issues, warnings = _validate_against_schema(record, target)
    if nested or schema_issues:
        return nested + schema_issues, warnings

    # Eligibility runs only once the record is structurally sound — there is no
    # value in reasoning about conditions in a record missing half its fields.
    eligibility = [
        *_check_paths_resolve(record, target),
        *_check_lane_membership(record),
        *_check_risk_matches_surface(record),
    ]
    return eligibility, warnings
