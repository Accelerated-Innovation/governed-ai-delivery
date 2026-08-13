"""Discovery and validation for the defect lane's fix records.

Modelled on `cli/extensions.py` — the repo's existing second artifact family.
Like extensions, this is a separate directory, a separate module, a distinct
check ABI, and silent when absent. It deliberately does **not** reuse the feature
check protocol: `list_user_features` applies no content filter, so anything under
`features/` gets the five-artifact gauntlet, and `_run_feature_checks` hardcodes
the `features/` prefix in its output.

The ABI returns `(issues, warnings)` rather than the feature `(CheckStatus, str)`
because `CheckStatus` lives in `cli/validate.py`, which imports this module —
sharing the type would make a cycle. Warnings carry the same
"visible gaps, not silent green" contract `check_eval_criteria` uses.
"""

from pathlib import Path

import pytest
import yaml

from cli.fixes import (
    FIX_RECORD_SKELETON,
    discover_fix_records,
    validate_fix_record,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_SRC = REPO_ROOT / "governance" / "schemas" / "fix_record.schema.json"


def _valid_record(record_id: str = "task-filter-reset") -> dict:
    return {
        "version": 1,
        "id": record_id,
        "summary": "Filter resets when navigating back",
        "expectation": {
            "source": "features/sample/acceptance.feature",
            "reference": "Scenario: Filter persists",
        },
        "failure": {"observed": "Filter discarded on back-navigation"},
        "surface": {"paths": ["src/hooks/useTaskFilter.ts"]},
        "reproduction": {"test": "src/hooks/useTaskFilter.test.ts"},
        "risk": {
            "architecture": False,
            "security_auth": False,
            "data_handling": False,
            "public_contract": False,
            "nfr": False,
            "cross_service": False,
        },
        "introduces_new_behavior": False,
    }


def _write_record(target: Path, record_id: str, data) -> Path:
    d = target / "fixes" / record_id
    d.mkdir(parents=True, exist_ok=True)
    path = d / "fix.yaml"
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _install_schema(target: Path) -> None:
    """Mirror what `govkit apply` ships: the schema as a governed file."""
    dest = target / "governance" / "schemas"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "fix_record.schema.json").write_text(
        SCHEMA_SRC.read_text(encoding="utf-8"), encoding="utf-8"
    )


class TestDiscovery:
    def test_no_fixes_dir_is_silent(self, tmp_path):
        """Existing repos must see no change — absence is not a finding."""
        assert discover_fix_records(tmp_path) == []

    def test_empty_fixes_dir(self, tmp_path):
        (tmp_path / "fixes").mkdir()
        assert discover_fix_records(tmp_path) == []

    def test_finds_records(self, tmp_path):
        _write_record(tmp_path, "alpha", _valid_record("alpha"))
        _write_record(tmp_path, "beta", _valid_record("beta"))
        found = discover_fix_records(tmp_path)
        assert [r.id for r in found] == ["alpha", "beta"]

    def test_ignores_dotdirs_and_loose_files(self, tmp_path):
        _write_record(tmp_path, "alpha", _valid_record("alpha"))
        (tmp_path / "fixes" / ".scratch").mkdir()
        (tmp_path / "fixes" / "README.md").write_text("notes", encoding="utf-8")
        assert [r.id for r in discover_fix_records(tmp_path)] == ["alpha"]

    def test_missing_fix_yaml_is_an_error_not_a_crash(self, tmp_path):
        (tmp_path / "fixes" / "alpha").mkdir(parents=True)
        found = discover_fix_records(tmp_path)
        assert len(found) == 1
        assert found[0].errors

    def test_unparseable_yaml_is_an_error_not_a_crash(self, tmp_path):
        _write_record(tmp_path, "alpha", "key: [unclosed\n")
        found = discover_fix_records(tmp_path)
        assert len(found) == 1
        assert found[0].errors


class TestValidation:
    def test_valid_record_has_no_issues(self, tmp_path):
        _install_schema(tmp_path)
        _write_record(tmp_path, "alpha", _valid_record("alpha"))
        record = discover_fix_records(tmp_path)[0]
        issues, _ = validate_fix_record(record, tmp_path)
        assert issues == []

    def test_id_must_match_directory_name(self, tmp_path):
        _install_schema(tmp_path)
        _write_record(tmp_path, "alpha", _valid_record("something-else"))
        record = discover_fix_records(tmp_path)[0]
        issues, _ = validate_fix_record(record, tmp_path)
        assert any("directory" in i for i in issues), issues

    @pytest.mark.parametrize(
        "key", ["version", "summary", "expectation", "failure", "surface", "reproduction", "risk"],
    )
    def test_missing_required_key_is_an_issue(self, tmp_path, key):
        """The structural pre-check runs in-process, so a malformed record fails
        even where check-jsonschema is unavailable."""
        data = _valid_record("alpha")
        del data[key]
        _write_record(tmp_path, "alpha", data)
        record = discover_fix_records(tmp_path)[0]
        issues, _ = validate_fix_record(record, tmp_path)
        assert any(key in i for i in issues), issues

    def test_discovery_error_passes_through(self, tmp_path):
        (tmp_path / "fixes" / "alpha").mkdir(parents=True)
        record = discover_fix_records(tmp_path)[0]
        issues, _ = validate_fix_record(record, tmp_path)
        assert issues

    def test_missing_schema_warns_rather_than_passing_silently(self, tmp_path):
        """No schema installed is a visible gap, not silent green."""
        _write_record(tmp_path, "alpha", _valid_record("alpha"))
        record = discover_fix_records(tmp_path)[0]
        issues, warnings = validate_fix_record(record, tmp_path)
        assert issues == []
        assert any("schema" in w for w in warnings), warnings


class TestSkeleton:
    def test_skeleton_is_valid_yaml(self):
        assert isinstance(yaml.safe_load(FIX_RECORD_SKELETON.format(id="sample")), dict)

    def test_skeleton_validates_against_the_shipped_schema(self):
        """Pins the generator to the schema. There is no template file, so this
        is what stops `govkit fix init` output drifting from what validates."""
        import json

        from jsonschema import Draft202012Validator

        schema = json.loads(SCHEMA_SRC.read_text(encoding="utf-8"))
        instance = yaml.safe_load(FIX_RECORD_SKELETON.format(id="sample"))
        errors = list(Draft202012Validator(schema).iter_errors(instance))
        assert not errors, "\n".join(e.message for e in errors)

    def test_skeleton_carries_the_requested_id(self):
        instance = yaml.safe_load(FIX_RECORD_SKELETON.format(id="my-defect"))
        assert instance["id"] == "my-defect"
