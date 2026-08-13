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

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

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


def _check_id_matches_directory(record: FixRecord) -> list[str]:
    declared = record.data.get("id")
    if declared is None or declared == record.id:
        return []
    return [
        f"{record.rel} declares id '{declared}' but sits in directory "
        f"'{record.id}' — they must match"
    ]


def _validate_against_schema(
    record: FixRecord, target: Path,
) -> tuple[list[str], list[str]]:
    """Instance validation, with the three-tier degradation `check_eval_criteria`
    established: a missing schema or absent tool is a visible warning, never a
    silent pass."""
    schema = target / SCHEMA_REL
    if not schema.is_file():
        return [], [
            f"{record.rel} structure OK — no fix_record schema installed; "
            "instance validation skipped"
        ]
    try:
        result = subprocess.run(
            ["check-jsonschema", "--schemafile", str(schema), str(record.path)],
            capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return [], [
            f"{record.rel} structure OK — install check-jsonschema for full validation"
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

    return _validate_against_schema(record, target)
