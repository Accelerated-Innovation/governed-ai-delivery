"""`govkit fix init` — scaffolds one fix record for the defect lane.

Mirrors `govkit init`'s level gate: the defect lane is L4+, because L3
(Foundations) ships agent rules and architecture contracts only and has no
artifact model at all.

Unlike `govkit init`, it does not require an existing `features/` directory —
`fixes/` is created on demand and is never shipped by apply.
"""

import argparse
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from cli.cmd_fix import cmd_fix_init, register

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_SRC = REPO_ROOT / "governance" / "schemas" / "fix_record.schema.json"


def _marker(target: Path, level: str = "4") -> None:
    (target / ".govkit").mkdir(parents=True, exist_ok=True)
    (target / ".govkit" / "marker.json").write_text(
        json.dumps({
            "version": "0.18.0",
            "level": level,
            "agent": "claude-code",
            "options": {"type": "api", "ci": "github"},
            "applied_at": "2026-08-13T00:00:00Z",
        }),
        encoding="utf-8",
    )


def _args(target: Path, fix_id: str = "sample", level: str | None = None):
    return argparse.Namespace(fix_id=fix_id, target=str(target), level=level)


class TestLevelGate:
    def test_errors_at_l3(self, tmp_path, capsys):
        _marker(tmp_path, level="3")
        with pytest.raises(SystemExit) as exc:
            cmd_fix_init(_args(tmp_path))
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "Level 4" in out
        assert not (tmp_path / "fixes").exists()

    def test_errors_with_no_marker(self, tmp_path, capsys):
        """No marker resolves to L3, matching govkit init."""
        with pytest.raises(SystemExit) as exc:
            cmd_fix_init(_args(tmp_path))
        assert exc.value.code == 1

    def test_explicit_level_flag_overrides_marker(self, tmp_path):
        _marker(tmp_path, level="3")
        cmd_fix_init(_args(tmp_path, level="4"))
        assert (tmp_path / "fixes" / "sample" / "fix.yaml").is_file()

    def test_works_at_l5(self, tmp_path):
        _marker(tmp_path, level="5")
        cmd_fix_init(_args(tmp_path))
        assert (tmp_path / "fixes" / "sample" / "fix.yaml").is_file()


class TestScaffold:
    def test_creates_record_without_requiring_features_dir(self, tmp_path):
        """fixes/ is created on demand; apply never ships it."""
        _marker(tmp_path)
        assert not (tmp_path / "features").exists()
        cmd_fix_init(_args(tmp_path, "task-filter-reset"))
        assert (tmp_path / "fixes" / "task-filter-reset" / "fix.yaml").is_file()

    def test_record_carries_the_requested_id(self, tmp_path):
        _marker(tmp_path)
        cmd_fix_init(_args(tmp_path, "task-filter-reset"))
        data = yaml.safe_load(
            (tmp_path / "fixes" / "task-filter-reset" / "fix.yaml").read_text(encoding="utf-8")
        )
        assert data["id"] == "task-filter-reset"

    def test_scaffolded_record_validates_against_the_schema(self, tmp_path):
        """Structurally complete on creation — what fails is eligibility, which
        is the point: the placeholders must be replaced with resolvable paths."""
        _marker(tmp_path)
        cmd_fix_init(_args(tmp_path))
        data = yaml.safe_load(
            (tmp_path / "fixes" / "sample" / "fix.yaml").read_text(encoding="utf-8")
        )
        schema = json.loads(SCHEMA_SRC.read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema).iter_errors(data))
        assert not errors, "\n".join(e.message for e in errors)

    def test_refuses_to_overwrite_an_existing_record(self, tmp_path, capsys):
        _marker(tmp_path)
        cmd_fix_init(_args(tmp_path))
        existing = tmp_path / "fixes" / "sample" / "fix.yaml"
        existing.write_text("edited by hand\n", encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            cmd_fix_init(_args(tmp_path))
        assert exc.value.code == 1
        assert existing.read_text(encoding="utf-8") == "edited by hand\n"

    @pytest.mark.parametrize("bad_id", ["Has Spaces", "UPPER", "-leading", "with/slash"])
    def test_rejects_ids_the_schema_would_reject(self, tmp_path, bad_id, capsys):
        """Fail at creation rather than producing a record that cannot validate."""
        _marker(tmp_path)
        with pytest.raises(SystemExit) as exc:
            cmd_fix_init(_args(tmp_path, bad_id))
        assert exc.value.code == 1
        assert not (tmp_path / "fixes").exists()


class TestWiring:
    def test_registers_the_fix_init_subcommand(self):
        """A dropped registration is invisible to every other test here."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        register(subparsers)
        args = parser.parse_args(["fix", "init", "my-defect", "--target", "."])
        assert args.func is cmd_fix_init
        assert args.fix_id == "my-defect"

    def test_registered_in_the_main_dispatch_table(self):
        """Every registrar is imported as a bare `register`, so identity is in
        the defining module, not the function name."""
        from cli import govkit

        modules = [r.__module__ for r in govkit._REGISTRARS]
        assert "cli.cmd_fix" in modules, modules


class TestTargetValidation:
    """Consistent with `govkit extension add`: a bad --target is an error, not a
    directory tree conjured somewhere surprising."""

    def test_missing_target_errors_before_creating_anything(self, tmp_path, capsys):
        missing = tmp_path / "nope"
        with pytest.raises(SystemExit) as exc:
            cmd_fix_init(_args(missing))
        assert exc.value.code == 1
        assert not missing.exists(), "target was created despite being invalid"

    def test_file_as_target_errors(self, tmp_path, capsys):
        not_a_dir = tmp_path / "afile"
        not_a_dir.write_text("x", encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            cmd_fix_init(_args(not_a_dir))
        assert exc.value.code == 1

    def test_target_check_precedes_the_level_gate(self, tmp_path):
        """A missing target reads the marker from nowhere and would otherwise
        resolve to L3, reporting the wrong problem."""
        missing = tmp_path / "nope"
        with pytest.raises(SystemExit):
            cmd_fix_init(_args(missing, level="4"))
        assert not missing.exists()
