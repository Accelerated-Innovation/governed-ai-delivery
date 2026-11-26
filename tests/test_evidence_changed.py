"""`govkit evidence --changed-since`: every feature a change touches (L08a).

Real Git, the real command and real result files.
"""

import argparse
import subprocess

import pytest

from cli import evidence_record, tree_identity
from cli import evidence_report as er
from cli.cmd_evidence import cmd_evidence, register
from tests.test_evidence_report import ACCEPTANCE, PASSING, _junit

FIRST, SECOND = "07_invoice_approval", "08_refunds"
IGNORED = f"junit.xml\n{evidence_record.NAME}\n"


def git(target, *args):
    return subprocess.run(
        ["git", "-C", str(target), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _write(target, relative, text):
    path = target / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def project(tmp_path):
    """Two features and a source file, committed. Returns the target and the base."""
    for name in (FIRST, SECOND):
        _write(tmp_path, f"features/{name}/acceptance.feature", ACCEPTANCE)
    _write(tmp_path, "features/starter_backend/acceptance.feature", ACCEPTANCE)
    _write(tmp_path, "src/service.py", "# service\n")
    _write(tmp_path, ".gitignore", IGNORED)
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "base")
    return tmp_path, git(tmp_path, "rev-parse", "HEAD")


def _run(target, capsys, *options):
    parser = argparse.ArgumentParser()
    register(parser.add_subparsers())
    arguments = parser.parse_args(["evidence", "--target", str(target), *options])
    with pytest.raises(SystemExit) as stopped:
        cmd_evidence(arguments)
    return stopped.value.code, capsys.readouterr()


def _results(target, cases=PASSING):
    _junit(target, cases)
    evidence_record.write_record(target)


class TestWhichFeatures:
    def test_a_change_elsewhere_touches_no_feature(self, project):
        target, base = project
        _write(target, "src/service.py", "# changed\n")
        assert er.changed_features(target, base) == er.Changed((), ())

    def test_an_unstaged_edit_touches_its_feature(self, project):
        target, base = project
        _write(target, f"features/{SECOND}/nfrs.md", "# NFRs\n")
        assert er.changed_features(target, base).present == (SECOND,)

    def test_staged_committed_and_untracked_files_all_count(self, project):
        target, base = project
        _write(target, f"features/{FIRST}/plan.md", "# Plan\n")
        git(target, "add", ".")
        git(target, "commit", "-qm", "plan")
        _write(target, f"features/{SECOND}/acceptance.feature", ACCEPTANCE + "\n")
        git(target, "add", ".")
        _write(target, "features/09_new/acceptance.feature", ACCEPTANCE)
        assert er.changed_features(target, base).present == (FIRST, SECOND, "09_new")

    def test_supplied_paths_outside_the_features_directory_do_not_count(self, project):
        target, base = project
        supplied = [f"src/{FIRST}/service.py", f"features/{SECOND}/plan.md", "features/README.md"]
        assert er.changed_features(target, base, paths=supplied) == er.Changed((SECOND,), ())

    def test_a_removed_feature_is_listed_and_not_judged(self, project):
        target, base = project
        git(target, "rm", "-rq", f"features/{SECOND}")
        assert er.changed_features(target, base) == er.Changed((), (SECOND,))

    def test_a_feature_directory_replaced_by_a_file_is_listed_as_removed(self, project):
        target, base = project
        git(target, "rm", "-rq", f"features/{SECOND}")
        _write(target, f"features/{SECOND}", "not a directory\n")
        assert er.changed_features(target, base) == er.Changed((), (SECOND,))

    def test_a_starter_and_a_loose_file_are_not_features(self, project):
        target, base = project
        _write(target, "features/starter_backend/plan.md", "# Plan\n")
        _write(target, "features/README.md", "# Features\n")
        assert er.changed_features(target, base) == er.Changed((), ())

    def test_an_ignored_file_does_not_count(self, project):
        target, base = project
        _write(target, f"features/{FIRST}/junit.xml", "<testsuites/>")
        assert er.changed_features(target, base).present == ()

    @pytest.mark.parametrize("base", ["no-such-ref", "", "--output=x"])
    def test_a_base_that_names_no_commit_is_refused(self, project, base):
        with pytest.raises(er.SelectionError, match="--changed-since"):
            er.changed_features(project[0], base)

    def test_paths_are_relative_to_a_target_below_the_repository_root(self, tmp_path):
        target = tmp_path / "service"
        _write(target, f"features/{FIRST}/acceptance.feature", ACCEPTANCE)
        git(tmp_path, "init", "-q")
        git(tmp_path, "config", "user.email", "test@example.invalid")
        git(tmp_path, "config", "user.name", "Test")
        git(tmp_path, "add", ".")
        git(tmp_path, "commit", "-qm", "base")
        _write(target, f"features/{FIRST}/plan.md", "# Plan\n")
        _write(tmp_path, "features/elsewhere/plan.md", "# Plan\n")
        assert tree_identity.changed_paths(target, "HEAD", "features") == [
            f"features/{FIRST}/plan.md"
        ]


class TestCommand:
    def test_no_feature_touched_judges_none_and_exits_zero(self, project, capsys):
        target, base = project
        _write(target, "src/service.py", "# changed\n")
        code, output = _run(target, capsys, "--changed-since", base)
        assert code == 0 and "no feature was judged" in output.out

    def test_a_touched_feature_that_passes_exits_zero(self, project, capsys):
        target, base = project
        _write(target, f"features/{FIRST}/plan.md", "# Plan\n")
        _results(target)
        code, output = _run(target, capsys, "--changed-since", base)
        assert code == 0, output.out
        assert f"feature {FIRST}" in output.out and SECOND not in output.out
        assert "All 1 changed feature(s) passed." in output.out

    def test_each_touched_feature_is_reported_and_one_short_fails_the_run(self, project, capsys):
        target, base = project
        for name in (FIRST, SECOND):
            _write(target, f"features/{name}/plan.md", "# Plan\n")
        _write(target, f"features/{SECOND}/acceptance.feature", "Feature: Empty\n")
        _results(target)
        code, output = _run(target, capsys, "--changed-since", base)
        assert code == 1
        assert f"feature {FIRST}" in output.out and f"feature {SECOND}" in output.out
        assert "1 of 2 changed feature(s) did not pass." in output.out

    def test_results_that_were_not_recorded_do_not_pass(self, project, capsys):
        target, base = project
        _write(target, f"features/{FIRST}/plan.md", "# Plan\n")
        _junit(target, PASSING)
        code, output = _run(target, capsys, "--changed-since", base)
        assert code == 1 and "unrecorded" in output.out

    def test_a_removed_feature_is_named(self, project, capsys):
        target, base = project
        git(target, "rm", "-rq", f"features/{SECOND}")
        code, output = _run(target, capsys, "--changed-since", base)
        assert code == 0 and f"removed  {SECOND} (not judged)" in output.out

    def test_a_bad_base_exits_two(self, project, capsys):
        code, output = _run(project[0], capsys, "--changed-since", "no-such-ref")
        assert code == 2 and "names no commit" in output.err and output.out == ""

    @pytest.mark.parametrize(
        "extra",
        [["--feature", FIRST], ["--json"], ["--record"], ["--fast-max-seconds", "1"]],
    )
    def test_it_does_not_combine_with_the_other_modes(self, project, capsys, extra):
        target, base = project
        code, output = _run(target, capsys, "--changed-since", base, *extra)
        assert code == 2 and "--changed-since" in output.err

    def test_without_the_option_the_command_is_unchanged(self, project, capsys):
        target, _ = project
        code, output = _run(target, capsys)
        assert "measured quality evidence" in output.out and "changed since" not in output.out
