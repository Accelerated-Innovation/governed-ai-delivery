"""`govkit evidence` — report measured evidence per dimension.

Deliberately a separate command from `validate`. `validate` checks that governed
*artifacts* are well-formed; this reports what an executed tool *observed*. They
answer different questions and fail for different reasons, and collapsing them
would put a forecast and an observation behind the same verdict.
"""

import argparse
from pathlib import Path

import pytest

from cli.cmd_evidence import cmd_evidence, register


def _args(
    target: Path,
    fast_max_seconds: float | None = None,
    feature: str | None = None,
    json: bool = False,
):
    return argparse.Namespace(
        target=str(target), fast_max_seconds=fast_max_seconds, feature=feature, json=json
    )


def _passing_junit(target: Path) -> None:
    (target / "junit.xml").write_text(
        '<?xml version="1.0"?><testsuites><testsuite name="s" tests="2" '
        'failures="0" errors="0"><testcase classname="s" name="a" time="0.01"/>'
        '<testcase classname="s" name="b" time="0.02"/></testsuite></testsuites>',
        encoding="utf-8",
    )


class TestTargetValidation:
    def test_missing_target_errors(self, tmp_path):
        with pytest.raises(SystemExit) as exc:
            cmd_evidence(_args(tmp_path / "nope"))
        assert exc.value.code == 1

    def test_file_as_target_errors(self, tmp_path):
        f = tmp_path / "afile"
        f.write_text("x", encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            cmd_evidence(_args(f))
        assert exc.value.code == 1


class TestReporting:
    def test_empty_analysis_exits_non_zero(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as exc:
            cmd_evidence(_args(tmp_path))
        assert exc.value.code == 1
        assert "analysed nothing" in capsys.readouterr().out.lower()

    def test_every_dimension_is_printed(self, tmp_path, capsys):
        """A dimension missing from the output is indistinguishable from one
        that passed."""
        from cli.evidence import DIMENSIONS

        _passing_junit(tmp_path)
        with pytest.raises(SystemExit):
            cmd_evidence(_args(tmp_path))
        out = capsys.readouterr().out
        missing = [d for d in DIMENSIONS if d not in out]
        assert not missing, missing

    def test_measured_pass_exits_zero(self, tmp_path, capsys):
        import json

        _passing_junit(tmp_path)
        (tmp_path / "axe.json").write_text(json.dumps({"violations": []}), encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            cmd_evidence(_args(tmp_path))
        assert exc.value.code == 0, capsys.readouterr().out

    def test_failure_exits_non_zero(self, tmp_path):
        (tmp_path / "junit.xml").write_text(
            '<?xml version="1.0"?><testsuites><testsuite name="s" tests="1" '
            'failures="1" errors="0"><testcase classname="s" name="a" time="0.01">'
            '<failure message="x"/></testcase></testsuite></testsuites>',
            encoding="utf-8",
        )
        with pytest.raises(SystemExit) as exc:
            cmd_evidence(_args(tmp_path))
        assert exc.value.code == 1

    def test_unmeasured_dimensions_are_labelled_inconclusive(self, tmp_path, capsys):
        _passing_junit(tmp_path)
        with pytest.raises(SystemExit):
            cmd_evidence(_args(tmp_path))
        assert "INCONCLUSIVE" in capsys.readouterr().out


class TestWiring:
    def test_registers_the_subcommand(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        register(sub)
        args = parser.parse_args(["evidence", "--target", "."])
        assert args.func is cmd_evidence

    def test_registered_in_the_main_dispatch_table(self):
        from cli import govkit

        assert "cli.cmd_evidence" in [r.__module__ for r in govkit._REGISTRARS]


class TestProjectTypeFromMarker:
    """The command reads the type govkit already recorded, rather than asking
    the user to repeat it — and degrades to reporting everything when it cannot."""

    def _marker(self, target: Path, project_type: str) -> None:
        import json

        (target / ".govkit").mkdir(parents=True, exist_ok=True)
        (target / ".govkit" / "marker.json").write_text(
            json.dumps({
                "version": "0.18.0", "level": "4", "agent": "claude-code",
                "options": {"type": project_type, "ci": "github"},
                "applied_at": "2026-08-13T00:00:00Z",
            }),
            encoding="utf-8",
        )

    def test_data_project_is_not_told_about_virtues(self, tmp_path, capsys):
        self._marker(tmp_path, "data")
        _passing_junit(tmp_path)
        with pytest.raises(SystemExit):
            cmd_evidence(_args(tmp_path))
        out = capsys.readouterr().out
        assert "Working" in out
        for absent in ("Unique", "Simple", "Clear", "Isolated"):
            assert absent not in out, f"{absent} reported for a data project"

    def test_backend_project_is_not_told_about_accessibility(self, tmp_path, capsys):
        self._marker(tmp_path, "api")
        _passing_junit(tmp_path)
        with pytest.raises(SystemExit):
            cmd_evidence(_args(tmp_path))
        assert "Accessibility" not in capsys.readouterr().out

    def test_ui_project_keeps_accessibility(self, tmp_path, capsys):
        self._marker(tmp_path, "ui-react")
        _passing_junit(tmp_path)
        with pytest.raises(SystemExit):
            cmd_evidence(_args(tmp_path))
        assert "Accessibility" in capsys.readouterr().out

    def test_missing_marker_reports_everything(self, tmp_path, capsys):
        """No marker is not a licence to report less."""
        from cli.evidence import DIMENSIONS

        _passing_junit(tmp_path)
        with pytest.raises(SystemExit):
            cmd_evidence(_args(tmp_path))
        out = capsys.readouterr().out
        assert not [d for d in DIMENSIONS if d not in out]


class TestFeatureReport:
    """`--feature` reports one feature's scenarios against the test results."""

    ACCEPTANCE = "Feature: F\n  Scenario: It works\n    Then ok\n"

    def _feature(self, target: Path, passing: bool = True) -> None:
        directory = target / "features" / "01_first"
        directory.mkdir(parents=True)
        (directory / "acceptance.feature").write_text(self.ACCEPTANCE, encoding="utf-8")
        child = "" if passing else '<failure message="x"/>'
        (target / "junit.xml").write_text(
            '<?xml version="1.0"?><testsuite name="s" tests="1" failures="0" errors="0">'
            f'<testcase classname="s" name="test_it_works" time="0.01">{child}</testcase>'
            "</testsuite>",
            encoding="utf-8",
        )

    def _run(self, capsys, *args, **kwargs):
        with pytest.raises(SystemExit) as exc:
            cmd_evidence(_args(*args, **kwargs))
        captured = capsys.readouterr()
        return exc.value.code, captured.out, captured.err

    def test_a_passing_feature_exits_zero(self, tmp_path, capsys):
        self._feature(tmp_path)
        code, out, _ = self._run(capsys, tmp_path, feature="01_first")
        assert code == 0, out
        assert "it-works" in out and "PASS" in out

    def test_a_failing_feature_exits_one(self, tmp_path, capsys):
        self._feature(tmp_path, passing=False)
        code, out, _ = self._run(capsys, tmp_path, feature="01_first")
        assert code == 1
        assert "FAIL" in out

    def test_json_prints_only_the_report(self, tmp_path, capsys):
        import json

        from cli.schema_validation import validate_document

        self._feature(tmp_path)
        code, out, _ = self._run(capsys, tmp_path, feature="01_first", json=True)
        report = json.loads(out)
        validate_document(report, "evidence-report")
        assert (code, report["outcome"]) == (0, "PASS")

    def test_json_keeps_the_exit_code_of_the_outcome(self, tmp_path, capsys):
        self._feature(tmp_path, passing=False)
        code, _, _ = self._run(capsys, tmp_path, feature="01_first", json=True)
        assert code == 1

    def test_an_unknown_feature_exits_two_and_prints_no_report(self, tmp_path, capsys):
        self._feature(tmp_path)
        code, out, err = self._run(capsys, tmp_path, feature="nope", json=True)
        assert code == 2
        assert out == ""
        assert "nope" in err and "01_first" in err

    def test_json_needs_a_feature(self, tmp_path, capsys):
        code, out, err = self._run(capsys, tmp_path, json=True)
        assert code == 2
        assert out == ""
        assert "--feature" in err

    def test_the_duration_ceiling_is_not_silently_ignored(self, tmp_path, capsys):
        self._feature(tmp_path)
        code, _, err = self._run(capsys, tmp_path, feature="01_first", fast_max_seconds=0.2)
        assert code == 2
        assert "--fast-max-seconds" in err

    def test_the_legacy_marker_is_not_read(self, tmp_path, capsys, monkeypatch):
        """A feature report needs no level and no project type."""

        def _never(_target):
            raise AssertionError("the marker was read")

        monkeypatch.setattr("cli.cmd_evidence.read_govkit_marker", _never)
        self._feature(tmp_path)
        code, _, _ = self._run(capsys, tmp_path, feature="01_first")
        assert code == 0

    def test_the_flags_are_registered(self):
        parser = argparse.ArgumentParser()
        register(parser.add_subparsers(dest="command"))
        args = parser.parse_args(["evidence", "--feature", "01_first", "--json"])
        assert (args.feature, args.json) == ("01_first", True)

    def test_without_a_feature_the_output_is_unchanged(self, tmp_path, capsys):
        _passing_junit(tmp_path)
        _, out, _ = self._run(capsys, tmp_path)
        assert "measured quality evidence" in out
        assert "feature" not in out.lower()
