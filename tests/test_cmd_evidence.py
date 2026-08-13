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


def _args(target: Path):
    return argparse.Namespace(target=str(target))


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
