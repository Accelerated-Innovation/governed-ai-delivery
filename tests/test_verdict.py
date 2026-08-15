"""`govkit verdict` — did an autonomous run earn the right to open a PR?

An agent cannot answer this about itself. Across five real headless runs —
a clean fix, a correct refusal, a stop at the ADR gate, and two bad outcomes —
`claude -p` returned `subtype: success` and exit 0 every single time. The
calling harness has to derive the verdict from the working tree and the gates,
which is the same move `govkit evidence` makes for quality: measure it, do not
accept the producer's account of it.

`AUTONOMOUS_BUGFIX_AGENT_ANALYSIS.md` §5.3 puts it as the single most important
decision — "the calling harness, not govkit, has to be what says no". This
command is govkit supplying the measurement that harness says no *with*; the
decision, and the exit code it branches on, stay with the caller.

The four outcomes are deliberately distinct, because collapsing them is how
autonomy goes wrong. A refusal reported as failure invites a retry loop, and a
retry loop against a gate the agent cannot legitimately clear is exactly the
pressure that produces self-certification (§4).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from cli.verdict import BLOCKED, FIXED, REFUSED, REJECTED, assess

# Stand-ins for a real suite. RED_GREEN is content-sensitive: it passes only
# when the fix is present, so reverting the source genuinely turns it red —
# which is the behaviour the gate is checking for.
RED_GREEN = [
    sys.executable, "-c",
    "import sys,pathlib;"
    "sys.exit(0 if 'min(' in pathlib.Path('src/calc.py').read_text() else 1)",
]
FAILS = [sys.executable, "-c", "raise SystemExit(1)"]
PASSES = [sys.executable, "-c", "raise SystemExit(0)"]


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A committed baseline: one source file, one test, one contract."""
    r = tmp_path / "proj"
    (r / "src").mkdir(parents=True)
    (r / "tests").mkdir()
    (r / "docs").mkdir()
    (r / "src" / "calc.py").write_text("def rate(p):\n    return p\n", encoding="utf-8")
    (r / "tests" / "test_calc.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (r / "docs" / "CONTRACT.md").write_text("# Contract\n\nRate is clamped.\n", encoding="utf-8")
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@e.com")
    _git(r, "config", "user.name", "T")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "baseline")
    return r


def _fix_record(repo: Path, *, source: str = "docs/CONTRACT.md",
                paths: list[str] | None = None, fix_id: str = "rate-clamp") -> None:
    d = repo / "fixes" / fix_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "fix.yaml").write_text(
        yaml.safe_dump({
            "version": 1, "id": fix_id, "summary": "rate not clamped",
            "expectation": {"source": source, "reference": "Rate is clamped"},
            "failure": {"observed": "returns unclamped"},
            "surface": {"paths": paths if paths is not None else ["src/calc.py"]},
            "reproduction": {"test": "tests/test_calc.py"},
            "risk": {k: False for k in (
                "architecture", "security_auth", "data_handling",
                "public_contract", "nfr", "cross_service")},
            "introduces_new_behavior": False,
        }, sort_keys=False),
        encoding="utf-8",
    )


def _edit_source(repo: Path) -> None:
    (repo / "src" / "calc.py").write_text(
        "def rate(p):\n    return min(p, 100)\n", encoding="utf-8")


def _adr(repo: Path, status: str, name: str = "0001-rates.md") -> None:
    d = repo / "docs" / "backend" / "architecture" / "ADR"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(f"# ADR-0001\n\n## Status\n{status}\n", encoding="utf-8")


def _run(repo: Path, **kw):
    kw.setdefault("source_roots", ("src/",))
    kw.setdefault("test_command", RED_GREEN)
    # The govkit-validate gate spawns a full interpreter, which costs ~3s per
    # case and says nothing about the gate under test. TestValidateGate covers
    # it once, on its own.
    kw.setdefault("run_validate", False)
    return assess(repo, **kw)


# ---------------------------------------------------------------------------
# The four outcomes
# ---------------------------------------------------------------------------


class TestOutcomes:
    def test_untouched_tree_is_a_refusal_not_a_failure(self, repo):
        """§5.3: stalling is a first-class success. Coding it as failure is what
        invites a retry loop against a gate the agent cannot honestly clear."""
        verdict, code, _gates = _run(repo)
        assert (verdict, code) == (REFUSED, 2)

    def test_a_complete_defect_fix_is_certified(self, repo):
        _edit_source(repo)
        _fix_record(repo)
        verdict, code, gates = _run(repo)
        assert (verdict, code) == (FIXED, 0), [g for g in gates if g.status == "fail"]

    def test_feature_artifacts_without_code_is_blocked_not_rejected(self, repo):
        """Authoring a feature package and stopping is the ADR gate working.
        It needs a human, not a bug report."""
        (repo / "features" / "rates").mkdir(parents=True)
        (repo / "features" / "rates" / "plan.md").write_text("# plan\n", encoding="utf-8")
        _adr(repo, "Proposed")
        verdict, code, _gates = _run(repo)
        assert (verdict, code) == (BLOCKED, 3)

    def test_a_fix_record_with_no_fix_is_rejected(self, repo):
        """A record describes a repair. Without the repair it is a claim about
        work that was not done — broken, not blocked."""
        _fix_record(repo)
        verdict, code, _gates = _run(repo)
        assert (verdict, code) == (REJECTED, 1)


# ---------------------------------------------------------------------------
# Individual gates
# ---------------------------------------------------------------------------


def _fail_names(gates) -> list[str]:
    return [g.gate for g in gates if g.status == "fail"]


class TestGates:
    def test_source_changed_with_no_governing_artifact(self, repo):
        _edit_source(repo)
        verdict, _c, gates = _run(repo)
        assert verdict == REJECTED
        assert "governing-artifact" in _fail_names(gates)

    def test_inventing_a_feature_package_alongside_a_fix_is_rejected(self, repo):
        """§4's self-certification: five artifacts authored to clear a gate."""
        _edit_source(repo)
        _fix_record(repo)
        (repo / "features" / "rates").mkdir(parents=True)
        (repo / "features" / "rates" / "plan.md").write_text("# plan\n", encoding="utf-8")
        verdict, _c, gates = _run(repo)
        assert verdict == REJECTED
        assert "defect-lane-only" in _fail_names(gates)

    def test_an_agent_authored_accepted_adr_is_rejected(self, repo):
        """`Accepted` is a derived state. An author may only write `Proposed`."""
        _edit_source(repo)
        _fix_record(repo)
        _adr(repo, "Accepted")
        verdict, _c, gates = _run(repo)
        assert verdict == REJECTED
        assert "adr-not-self-accepted" in _fail_names(gates)

    def test_a_proposed_adr_is_fine(self, repo):
        _edit_source(repo)
        _fix_record(repo)
        _adr(repo, "Proposed")
        _verdict, _c, gates = _run(repo)
        assert "adr-not-self-accepted" not in _fail_names(gates)

    def test_the_adr_template_is_not_read_as_a_claim(self, repo):
        """TEMPLATE.md carries the whole vocabulary menu, including Accepted."""
        _edit_source(repo)
        _fix_record(repo)
        _adr(repo, "Proposed | Accepted | Rejected | Superseded", name="TEMPLATE.md")
        _verdict, _c, gates = _run(repo)
        assert "adr-not-self-accepted" not in _fail_names(gates)

    def test_modifying_the_cited_source_is_rejected(self, repo):
        """Observed in a real run: the agent restored a deleted contract, cited
        it, and every govkit gate went green. Condition 1 asks the change to
        cite a source that ALREADY established the behavior; editing that source
        in the same change manufactures its own eligibility."""
        _edit_source(repo)
        _fix_record(repo)
        (repo / "docs" / "CONTRACT.md").write_text(
            "# Contract\n\nRate is clamped.\n\n## New rule\n", encoding="utf-8")
        verdict, _c, gates = _run(repo)
        assert verdict == REJECTED
        assert "citation-predates-fix" in _fail_names(gates)

    def test_source_outside_the_declared_surface_is_rejected(self, repo):
        _edit_source(repo)
        (repo / "src" / "sneaky.py").write_text("x = 1\n", encoding="utf-8")
        _fix_record(repo, paths=["src/calc.py"])
        verdict, _c, gates = _run(repo)
        assert verdict == REJECTED
        assert "surface-covers-diff" in _fail_names(gates)

    def test_a_test_file_is_not_expected_in_the_surface(self, repo):
        """surface.paths describes what was repaired; the regression test is the
        proof of the repair, not part of it."""
        _edit_source(repo)
        (repo / "tests" / "test_calc.py").write_text(
            "def test_ok():\n    assert True\n\ndef test_new():\n    assert True\n",
            encoding="utf-8")
        _fix_record(repo, paths=["src/calc.py"])
        _verdict, _c, gates = _run(repo)
        assert "surface-covers-diff" not in _fail_names(gates)


class TestRedBeforeGreen:
    """The one claim an agent cannot talk past. Every run in the experiment
    asserted red-before-green in its summary; this is what checks it."""

    def test_tests_that_still_pass_without_the_fix_are_rejected(self, repo):
        _edit_source(repo)
        _fix_record(repo)
        verdict, _c, gates = _run(repo, test_command=PASSES)
        assert verdict == REJECTED
        assert "red-before-green" in _fail_names(gates)

    def test_a_suite_failing_with_the_fix_applied_is_rejected(self, repo):
        _edit_source(repo)
        _fix_record(repo)
        # Fails whether or not the fix is present => the fix does not work.
        verdict, _c, gates = _run(repo, test_command=FAILS)
        assert verdict == REJECTED
        assert "red-before-green" in _fail_names(gates)

    def test_without_a_test_command_nothing_is_certified(self, repo):
        """Unmeasured is not verified — the contract `govkit evidence` states.
        A run that cannot be shown to reproduce its defect cannot be FIXED."""
        _edit_source(repo)
        _fix_record(repo)
        verdict, code, gates = _run(repo, test_command=None)
        assert (verdict, code) == (REJECTED, 1)
        assert "red-before-green" in _fail_names(gates)

    def test_the_working_tree_survives_the_check(self, repo):
        """It reverts the source to prove red, so it must put it back — a
        verdict tool that damages the tree is worse than none."""
        _edit_source(repo)
        _fix_record(repo)
        before = (repo / "src" / "calc.py").read_text(encoding="utf-8")
        _run(repo)
        assert (repo / "src" / "calc.py").read_text(encoding="utf-8") == before


class TestCommittedRuns:
    """The agent may commit and open the PR itself, so a committed run must be
    judged exactly like an uncommitted one."""

    def test_a_committed_fix_is_certified_against_its_base(self, repo):
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                              capture_output=True, text=True).stdout.strip()
        _edit_source(repo)
        _fix_record(repo)
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "fix(calc): clamp the rate")
        verdict, code, gates = _run(repo, base=base)
        assert (verdict, code) == (FIXED, 0), [g.gate for g in gates if g.status == "fail"]

    def test_a_committed_run_that_edits_its_cited_source_is_still_caught(self, repo):
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                              capture_output=True, text=True).stdout.strip()
        _edit_source(repo)
        _fix_record(repo)
        (repo / "docs" / "CONTRACT.md").write_text("# Contract\n\nchanged\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "fix(calc): clamp the rate")
        verdict, _c, gates = _run(repo, base=base)
        assert verdict == REJECTED
        assert "citation-predates-fix" in _fail_names(gates)


class TestNoise:
    def test_build_artifacts_are_not_source(self, repo):
        """__pycache__ under a source root is not a change anyone declares."""
        _edit_source(repo)
        cache = repo / "src" / "__pycache__"
        cache.mkdir()
        (cache / "calc.cpython-311.pyc").write_bytes(b"\x00")
        _fix_record(repo, paths=["src/calc.py"])
        _verdict, _c, gates = _run(repo)
        assert "surface-covers-diff" not in _fail_names(gates)

    def test_the_first_changed_path_is_not_truncated(self, repo):
        """`git status --porcelain` encodes status in the first two columns, so
        the leading space of the first line is data. Stripping the whole output
        ate a character off exactly one path per run."""
        from cli.verdict import changed_files

        _edit_source(repo)
        (repo / "docs" / "CONTRACT.md").write_text("# c\n", encoding="utf-8")
        changed = changed_files(repo, "")
        assert all(not p.startswith("ocs/") for p in changed), changed
        assert "docs/CONTRACT.md" in changed


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


class TestWiring:
    def test_registers_the_subcommand(self):
        import argparse as ap

        from cli.cmd_verdict import cmd_verdict, register

        parser = ap.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        register(sub)
        args = parser.parse_args(["verdict", "--target", "."])
        assert args.func is cmd_verdict

    def test_registered_in_the_main_dispatch_table(self):
        from cli import govkit

        assert "cli.cmd_verdict" in [r.__module__ for r in govkit._REGISTRARS]


def _cli_args(repo: Path, **kw):
    import argparse as ap

    base = {
        "target": str(repo), "base": "", "source_roots": "src/",
        "test_command": "", "no_validate": True, "json": False,
    }
    base.update(kw)
    return ap.Namespace(**base)


class TestCli:
    def test_exit_code_carries_the_verdict(self, repo, capsys):
        """The harness branches on this, so it is the contract."""
        from cli.cmd_verdict import cmd_verdict

        with pytest.raises(SystemExit) as exc:
            cmd_verdict(_cli_args(repo))
        assert exc.value.code == 2  # untouched tree => REFUSED
        assert "REFUSED" in capsys.readouterr().out

    def test_source_roots_are_required_rather_than_guessed(self, repo, capsys):
        """`.govkit/skill_context.yaml` may record `source_root: ""`, which
        means 'no single root' — guessing from it would silently scope the
        checks to nothing."""
        from cli.cmd_verdict import cmd_verdict

        with pytest.raises(SystemExit) as exc:
            cmd_verdict(_cli_args(repo, source_roots=""))
        assert exc.value.code == 1
        assert "--source-roots is required" in capsys.readouterr().err

    def test_missing_target_is_reported_not_crashed(self, tmp_path, capsys):
        from cli.cmd_verdict import cmd_verdict

        with pytest.raises(SystemExit) as exc:
            cmd_verdict(_cli_args(tmp_path / "nope"))
        assert exc.value.code == 1
        assert "does not exist" in capsys.readouterr().err

    def test_json_output_is_machine_readable(self, repo, capsys):
        import json

        from cli.cmd_verdict import cmd_verdict

        _edit_source(repo)
        _fix_record(repo)
        with pytest.raises(SystemExit):
            cmd_verdict(_cli_args(repo, json=True,
                                  test_command=f'"{sys.executable}" -c "raise SystemExit(1)"'))
        payload = json.loads(capsys.readouterr().out)
        assert payload["verdict"] in {FIXED, REJECTED, REFUSED, BLOCKED}
        assert {g["gate"] for g in payload["gates"]}, payload


class TestValidateGate:
    """`govkit validate` is the one gate that shells out. Covered once here so
    the rest of the suite need not pay for it."""

    def test_a_govkit_governed_repo_passes_its_own_validate(self, repo):
        _edit_source(repo)
        _fix_record(repo)
        _verdict, _code, gates = _run(repo, run_validate=True)
        names = {g.gate for g in gates}
        assert "govkit-validate" in names, names

    def test_the_gate_is_absent_when_switched_off(self, repo):
        _edit_source(repo)
        _fix_record(repo)
        _verdict, _code, gates = _run(repo, run_validate=False)
        assert "govkit-validate" not in {g.gate for g in gates}
