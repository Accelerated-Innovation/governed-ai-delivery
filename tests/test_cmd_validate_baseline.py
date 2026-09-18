"""`govkit validate --baseline` — increment 10's command surface.

The check is only useful if it can be run, and its exit status is what a CI
gate reads. Two things matter here beyond wiring: a refusal must not be
reported as a pass, and the command must not be able to modify the tree it
is checking.
"""

from __future__ import annotations

import json
import subprocess

import pytest

from cli import cmd_validate

FEATURE = """\
Feature: Response approval

  @scenario:unapproved-blocked
  Scenario: An unapproved response cannot be sent
    Given a drafted response
    When the representative sends it
    Then the send is refused
"""


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


@pytest.fixture
def project(tmp_path):
    repo = tmp_path / "app"
    (repo / "features").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    (repo / "features" / "response-approval.feature").write_text(FEATURE, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "approved")
    revision = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True).stdout.strip()
    baseline = repo / "baseline.json"
    baseline.write_text(json.dumps({
        "version": 1,
        "commitment_key": "k",
        "sources": [{
            "source_key": "app",
            "repository": "https://example.invalid/app",
            "revision": revision,
            "path": "features",
            "kind": "repository",
        }],
        "selected_behavior": [{
            "ref": "app/response-approval#scenario:unapproved-blocked",
            "kind": "scenario",
            "id_source": "tag",
        }],
    }), encoding="utf-8")
    return repo, baseline


def run(target, baseline) -> tuple[int, str]:
    import argparse
    import contextlib
    import io

    args = argparse.Namespace(target=str(target), baseline=str(baseline))
    out = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            cmd_validate.cmd_validate_baseline(args)
        except SystemExit as exit_:
            code = exit_.code or 0
    return code, out.getvalue()


def test_an_unchanged_tree_exits_zero(project):
    repo, baseline = project

    code, output = run(repo, baseline)

    assert code == 0, output
    assert "no differences" in output.lower()


def test_a_semantic_change_exits_non_zero_and_names_the_clause(project):
    repo, baseline = project
    path = repo / "features" / "response-approval.feature"
    path.write_text(path.read_text().replace("Then the send is refused",
                                             "Then the send is queued"), encoding="utf-8")

    code, output = run(repo, baseline)

    assert code != 0
    assert "then" in output.lower()
    assert "development_token" in output


def test_a_refusal_exits_non_zero_rather_than_reporting_clean(project):
    """"I could not check" must never read as "nothing changed". A CI gate
    sees only the exit status."""
    repo, baseline = project
    path = repo / "features" / "response-approval.feature"
    path.write_text(path.read_text().replace("  @scenario:unapproved-blocked\n", ""),
                    encoding="utf-8")

    code, output = run(repo, baseline)

    assert code != 0
    assert "unresolvable" in output.lower()


def test_a_formatting_only_change_exits_zero(project):
    repo, baseline = project
    path = repo / "features" / "response-approval.feature"
    path.write_text(path.read_text().replace("    Given a drafted response",
                                             "        Given a drafted response   "),
                    encoding="utf-8")

    code, output = run(repo, baseline)

    assert code == 0, output


def test_the_command_does_not_modify_the_tree(project):
    repo, baseline = project
    path = repo / "features" / "response-approval.feature"
    path.write_text(path.read_text().replace("Then the send is refused",
                                             "Then the send is queued"), encoding="utf-8")
    before = path.read_text(encoding="utf-8")

    run(repo, baseline)

    assert path.read_text(encoding="utf-8") == before


def test_a_missing_baseline_file_is_refused_clearly(project, tmp_path):
    repo, _baseline = project

    code, output = run(repo, tmp_path / "absent.json")

    assert code != 0
    assert "baseline" in output.lower()
