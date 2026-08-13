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
            # Deliberately not under features/ — materializing a path there
            # would create a directory list_user_features treats as a feature.
            "source": "docs/backend/architecture/API_CONVENTIONS.md",
            "reference": "Section 4: pagination state",
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


def _materialize(target: Path, data: dict) -> None:
    """Create the files a record references, so eligibility checks resolve.
    Tests that assert on *non*-resolution deliberately skip this."""
    rels = [data["expectation"]["source"], data["reproduction"]["test"], *data["surface"]["paths"]]
    for rel in rels:
        f = target / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x", encoding="utf-8")


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
        _materialize(tmp_path, _valid_record("alpha"))
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
        _materialize(tmp_path, _valid_record("alpha"))
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


class TestValidateIntegration:
    """`run_validation` gains a second artifact family, exactly as extensions
    did: silent when absent, its own exit code, combined via max()."""

    def _target(self, tmp_path: Path, level: str = "4") -> Path:
        import json

        (tmp_path / ".govkit").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".govkit" / "marker.json").write_text(
            json.dumps({
                "version": "0.18.0", "level": level, "agent": "claude-code",
                "options": {"type": "api", "ci": "github"},
                "applied_at": "2026-08-13T00:00:00Z",
            }),
            encoding="utf-8",
        )
        # Empty features/ isolates the fix lane: list_user_features returns [],
        # so the only thing that can move the exit code is the fix record.
        (tmp_path / "features").mkdir(exist_ok=True)
        return tmp_path

    def test_absent_lane_is_silent(self, tmp_path, capsys):
        """Repos without a defect lane must see no output change at all."""
        from cli.validate import run_validation

        target = self._target(tmp_path)
        assert run_validation(target) == 0
        assert "fix" not in capsys.readouterr().out.lower()

    def test_valid_record_passes_and_is_reported(self, tmp_path, capsys):
        from cli.validate import run_validation

        target = self._target(tmp_path)
        _install_schema(target)
        _materialize(target, _valid_record("alpha"))
        _write_record(target, "alpha", _valid_record("alpha"))
        assert run_validation(target) == 0
        assert "alpha" in capsys.readouterr().out

    def test_invalid_record_fails_the_run(self, tmp_path):
        from cli.validate import run_validation

        target = self._target(tmp_path)
        data = _valid_record("alpha")
        del data["risk"]
        _write_record(target, "alpha", data)
        assert run_validation(target) == 1

    def test_lane_is_not_checked_at_l3(self, tmp_path):
        """L3 ships no artifact model; the defect lane starts at L4."""
        from cli.validate import run_validation

        target = self._target(tmp_path, level="3")
        data = _valid_record("alpha")
        del data["risk"]
        _write_record(target, "alpha", data)
        assert run_validation(target) == 0

    def test_lane_is_checked_at_l5(self, tmp_path):
        from cli.validate import run_validation

        target = self._target(tmp_path, level="5")
        data = _valid_record("alpha")
        del data["risk"]
        _write_record(target, "alpha", data)
        assert run_validation(target) == 1

    def test_warning_alone_does_not_fail(self, tmp_path, capsys):
        """No schema installed is a visible gap, not a failure."""
        from cli.validate import run_validation

        target = self._target(tmp_path)
        _materialize(target, _valid_record("alpha"))
        _write_record(target, "alpha", _valid_record("alpha"))
        assert run_validation(target) == 0
        assert "schema" in capsys.readouterr().out


class TestEligibility:
    """The four conditions, checked as far as a working-tree tool honestly can.

    `surface.paths` is *declared*, not derived from a diff, so cross-checking
    risk against it proves internal consistency — not correspondence with what
    the PR actually changed. That correspondence is CI's job, where the diff
    exists. Same split as declared-vs-computed averages in plan.md.
    """

    def _record_with(self, tmp_path: Path, **overrides) -> tuple:
        _install_schema(tmp_path)
        data = _valid_record("alpha")
        for key, value in overrides.items():
            data[key] = value
        _write_record(tmp_path, "alpha", data)
        return discover_fix_records(tmp_path)[0], tmp_path

    def _touch(self, tmp_path: Path, rel: str) -> None:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")

    def _fully_resolvable(self, tmp_path: Path) -> dict:
        data = _valid_record("alpha")
        _materialize(tmp_path, data)
        return data

    def test_fully_resolvable_record_passes(self, tmp_path):
        _install_schema(tmp_path)
        _write_record(tmp_path, "alpha", self._fully_resolvable(tmp_path))
        record = discover_fix_records(tmp_path)[0]
        issues, _ = validate_fix_record(record, tmp_path)
        assert issues == [], issues

    def test_unresolved_expectation_source_fails(self, tmp_path):
        """Condition 1 is otherwise pure assertion."""
        record, target = self._record_with(tmp_path)
        issues, _ = validate_fix_record(record, target)
        assert any("expectation.source" in i for i in issues), issues

    def test_missing_reproduction_test_fails(self, tmp_path):
        """Condition 2: no regression test, no light lane."""
        self._touch(tmp_path, "docs/backend/architecture/API_CONVENTIONS.md")
        self._touch(tmp_path, "src/hooks/useTaskFilter.ts")
        record, target = self._record_with(tmp_path)
        issues, _ = validate_fix_record(record, target)
        assert any("reproduction.test" in i for i in issues), issues

    def test_missing_surface_path_fails(self, tmp_path):
        self._touch(tmp_path, "docs/backend/architecture/API_CONVENTIONS.md")
        self._touch(tmp_path, "src/hooks/useTaskFilter.test.ts")
        record, target = self._record_with(tmp_path)
        issues, _ = validate_fix_record(record, target)
        assert any("surface.paths" in i for i in issues), issues

    @pytest.mark.parametrize(
        "flag",
        ["architecture", "security_auth", "data_handling", "public_contract", "nfr", "cross_service"],
    )
    def test_any_risk_flag_true_promotes_to_the_feature_lane(self, tmp_path, flag):
        """A `true` is not a waiver — it means this change is out of the lane."""
        data = self._fully_resolvable(tmp_path)
        data["risk"][flag] = True
        _install_schema(tmp_path)
        _write_record(tmp_path, "alpha", data)
        record = discover_fix_records(tmp_path)[0]
        issues, _ = validate_fix_record(record, tmp_path)
        assert any("feature lane" in i for i in issues), issues
        assert any(flag in i for i in issues), issues

    def test_new_behavior_promotes_to_the_feature_lane(self, tmp_path):
        """Condition 3."""
        data = self._fully_resolvable(tmp_path)
        data["introduces_new_behavior"] = True
        _install_schema(tmp_path)
        _write_record(tmp_path, "alpha", data)
        record = discover_fix_records(tmp_path)[0]
        issues, _ = validate_fix_record(record, tmp_path)
        assert any("feature lane" in i for i in issues), issues

    @pytest.mark.parametrize(
        "path, flag",
        [
            ("docs/backend/architecture/ARCH_CONTRACT.md", "architecture"),
            ("features/sample/nfrs.md", "nfr"),
            ("governance/backend/schemas/eval_criteria.schema.json", "public_contract"),
            # Area-agnostic schemas have no <area> segment; a pattern requiring
            # one silently missed them, which a real-CLI run caught.
            ("governance/schemas/fix_record.schema.json", "public_contract"),
        ],
    )
    def test_touching_a_governed_area_contradicts_a_false_flag(self, tmp_path, path, flag):
        """The other half of the two-sided check: a false beside a change in a
        govkit-owned namespace is a contradiction the record must not carry."""
        data = self._fully_resolvable(tmp_path)
        data["surface"]["paths"] = [path]
        self._touch(tmp_path, path)
        _install_schema(tmp_path)
        _write_record(tmp_path, "alpha", data)
        record = discover_fix_records(tmp_path)[0]
        issues, _ = validate_fix_record(record, tmp_path)
        assert any(flag in i for i in issues), issues

    def test_undecidable_flags_are_not_guessed(self, tmp_path):
        """govkit owns no namespace that definitionally means 'security' or
        'data handling', so those declarations stand alone rather than being
        cross-checked against an invented glob."""
        data = self._fully_resolvable(tmp_path)
        data["surface"]["paths"] = ["src/auth/session.ts"]
        self._touch(tmp_path, "src/auth/session.ts")
        _install_schema(tmp_path)
        _write_record(tmp_path, "alpha", data)
        record = discover_fix_records(tmp_path)[0]
        issues, _ = validate_fix_record(record, tmp_path)
        assert issues == [], issues


class TestPathSafety:
    """Record-authored paths must be repo-relative and contained.

    Mirrors `cli/extensions.py::_check_safe_file_path`. A record is authored by
    an agent, so "the path exists" is not the question — "the path is inside the
    repo it claims to describe" is.
    """

    def _record(self, tmp_path: Path, **overrides) -> tuple:
        _install_schema(tmp_path)
        data = _valid_record("alpha")
        _materialize(tmp_path, data)
        for dotted, value in overrides.items():
            section, _, key = dotted.partition(".")
            if key:
                data[section][key] = value
            else:
                data[section] = value
        _write_record(tmp_path, "alpha", data)
        return discover_fix_records(tmp_path)[0], tmp_path

    @pytest.mark.parametrize("abs_path", ["/etc/passwd", "C:\Windows\system.ini"])
    @pytest.mark.parametrize("field", ["expectation.source", "reproduction.test"])
    def test_absolute_paths_are_rejected(self, tmp_path, field, abs_path):
        """Path.is_absolute() is host-specific, so both flavours must be caught."""
        record, target = self._record(tmp_path, **{field: abs_path})
        issues, _ = validate_fix_record(record, target)
        assert any("absolute" in i for i in issues), issues

    @pytest.mark.parametrize("field", ["expectation.source", "reproduction.test"])
    def test_parent_escape_is_rejected(self, tmp_path, field):
        outside = tmp_path.parent / "outside.md"
        outside.write_text("x", encoding="utf-8")
        record, target = self._record(tmp_path, **{field: f"../{outside.name}"})
        issues, _ = validate_fix_record(record, target)
        assert any("outside" in i for i in issues), issues

    def test_surface_path_escape_is_rejected(self, tmp_path):
        outside = tmp_path.parent / "outside.py"
        outside.write_text("x", encoding="utf-8")
        record, target = self._record(tmp_path, **{"surface.paths": [f"../{outside.name}"]})
        issues, _ = validate_fix_record(record, target)
        assert any("outside" in i for i in issues), issues

    @pytest.mark.parametrize("field", ["expectation.source", "reproduction.test"])
    def test_directory_is_not_a_valid_citation(self, tmp_path, field):
        """A citation names a spec or a test, not a folder."""
        (tmp_path / "docs" / "backend" / "architecture").mkdir(parents=True, exist_ok=True)
        record, target = self._record(
            tmp_path, **{field: "docs/backend/architecture"}
        )
        issues, _ = validate_fix_record(record, target)
        assert any("not a file" in i for i in issues), issues

    def test_dot_slash_prefix_is_tolerated(self, tmp_path):
        """`./src/x.py` is the same path as `src/x.py` and must not be rejected,
        nor mangled — the old lstrip('./') turned '../x' into 'x', silently
        erasing an escape."""
        data = _valid_record("alpha")
        _materialize(tmp_path, data)
        data["surface"]["paths"] = ["./" + data["surface"]["paths"][0]]
        _install_schema(tmp_path)
        _write_record(tmp_path, "alpha", data)
        record = discover_fix_records(tmp_path)[0]
        issues, _ = validate_fix_record(record, tmp_path)
        assert issues == [], issues

    def test_governed_area_match_survives_a_dot_slash_prefix(self, tmp_path):
        """Normalization must not be able to hide a governed-area path."""
        data = _valid_record("alpha")
        _materialize(tmp_path, data)
        data["surface"]["paths"] = ["./features/sample/nfrs.md"]
        (tmp_path / "features" / "sample").mkdir(parents=True, exist_ok=True)
        (tmp_path / "features" / "sample" / "nfrs.md").write_text("x", encoding="utf-8")
        _install_schema(tmp_path)
        _write_record(tmp_path, "alpha", data)
        record = discover_fix_records(tmp_path)[0]
        issues, _ = validate_fix_record(record, tmp_path)
        assert any("nfr" in i for i in issues), issues


class TestNestedStructureWithoutSchemaTooling:
    """The record is the *whole* governance artifact for a defect-lane change.
    When the schema or check-jsonschema is unavailable, a warning is the right
    signal for reduced coverage — but an incomplete record must still fail.
    """

    def _issues(self, tmp_path: Path, data: dict) -> list[str]:
        # Deliberately no _install_schema: this is the degraded path.
        _write_record(tmp_path, "alpha", data)
        record = discover_fix_records(tmp_path)[0]
        issues, warnings = validate_fix_record(record, tmp_path)
        assert any("schema" in w for w in warnings), warnings
        return issues

    def test_expectation_without_a_source_fails(self, tmp_path):
        data = _valid_record("alpha")
        data["expectation"] = {"reference": "somewhere"}
        assert any("expectation.source" in i for i in self._issues(tmp_path, data))

    def test_empty_expectation_source_fails(self, tmp_path):
        data = _valid_record("alpha")
        data["expectation"]["source"] = "   "
        assert any("expectation.source" in i for i in self._issues(tmp_path, data))

    def test_reproduction_without_a_test_fails(self, tmp_path):
        data = _valid_record("alpha")
        data["reproduction"] = {}
        assert any("reproduction.test" in i for i in self._issues(tmp_path, data))

    def test_empty_surface_paths_fails(self, tmp_path):
        data = _valid_record("alpha")
        data["surface"]["paths"] = []
        assert any("surface.paths" in i for i in self._issues(tmp_path, data))

    def test_non_string_surface_path_fails(self, tmp_path):
        data = _valid_record("alpha")
        data["surface"]["paths"] = [123]
        assert any("surface.paths" in i for i in self._issues(tmp_path, data))

    @pytest.mark.parametrize(
        "flag",
        ["architecture", "security_auth", "data_handling", "public_contract", "nfr", "cross_service"],
    )
    def test_missing_risk_flag_fails(self, tmp_path, flag):
        data = _valid_record("alpha")
        del data["risk"][flag]
        assert any(flag in i for i in self._issues(tmp_path, data))

    def test_non_boolean_risk_flag_fails(self, tmp_path):
        data = _valid_record("alpha")
        data["risk"]["architecture"] = "no"
        assert any("architecture" in i for i in self._issues(tmp_path, data))

    def test_non_boolean_introduces_new_behavior_fails(self, tmp_path):
        data = _valid_record("alpha")
        data["introduces_new_behavior"] = "no"
        assert any("introduces_new_behavior" in i for i in self._issues(tmp_path, data))

    @pytest.mark.parametrize("section", ["expectation", "failure", "surface", "reproduction", "risk"])
    def test_non_mapping_section_fails(self, tmp_path, section):
        data = _valid_record("alpha")
        data[section] = "not a mapping"
        assert self._issues(tmp_path, data)
