"""`change:protected` in actual-change conformance (L06b).

A real Git repository and the real engine. The declaration is in the accepted
conformance configuration, held in the trusted policy checkout.
"""

import json

import pytest

from cli.check_models import State
from tests.test_change_conformance import git, inspect, result, setup
from tests.test_discovery import write
from tests.test_protected_change import BODY, DECLARED, TEST

CHECK = "change:protected"
WORKFLOW = ".github/workflows/ci.yml"


def _project(tmp_path, declared=DECLARED):
    target, trusted, _ = setup(tmp_path)
    if declared is not None:
        path = trusted / "conformance.json"
        config = json.loads(path.read_text())
        config["protected"] = declared
        path.write_text(json.dumps(config))
    write(target, TEST, BODY)
    write(target, WORKFLOW, "on: push\n")
    git(target, "add", ".")
    git(target, "commit", "-qm", "tests")
    return target, trusted, git(target, "rev-parse", "HEAD")


def _found(outcome):
    return sorted((f.code, f.location) for f in outcome.findings if f.category == "change")


def test_without_a_declaration_there_is_no_such_check(tmp_path):
    target, trusted, base = _project(tmp_path, declared=None)
    write(target, TEST, "def test_routes():\n    pass\n")
    assert CHECK not in {r.spec.id for r in inspect(target, trusted, base).checks.results}


def test_adding_tests_passes(tmp_path):
    target, trusted, base = _project(tmp_path)
    write(target, TEST, BODY + "\n\ndef test_more():\n    assert True\n")
    write(target, "tests/test_new.py", "def test_new():\n    assert True\n")
    outcome = result(inspect(target, trusted, base), CHECK).outcome
    assert outcome.state is State.PASS and _found(outcome) == []
    assert "2 changed files" in outcome.summary


def test_a_change_elsewhere_passes_with_nothing_checked(tmp_path):
    target, trusted, base = _project(tmp_path)
    write(target, "src/service.py", "# good updated\n")
    assert result(inspect(target, trusted, base), CHECK).outcome.state is State.PASS


def test_weakening_fails_and_names_each_file(tmp_path):
    target, trusted, base = _project(tmp_path)
    write(target, TEST, BODY.replace("'manager'", "routing.route(12000)"))
    write(target, WORKFLOW, "on: workflow_dispatch\n")
    write(target, "tests/test_new.py", "@pytest.mark.skip\ndef test_new():\n    assert False\n")
    report = inspect(target, trusted, base)
    checked = result(report, CHECK)
    assert checked.outcome.state is State.FAIL and report.exit_code == 1
    assert _found(checked.outcome) == [
        ("escape-marker-added", "tests/test_new.py"),
        ("protected-file-changed", WORKFLOW),
        ("test-altered", TEST),
    ]
    assert checked.spec.required


def test_a_committed_deletion_is_seen(tmp_path):
    target, trusted, base = _project(tmp_path)
    git(target, "rm", "-q", TEST)
    git(target, "commit", "-qm", "drop the failing test")
    assert _found(result(inspect(target, trusted, base), CHECK).outcome) == [("test-removed", TEST)]


def test_a_declaration_in_the_inspected_tree_is_not_read(tmp_path):
    """Only the trusted checkout declares; the change cannot narrow it."""
    target, trusted, base = _project(tmp_path)
    write(target, "conformance.json", json.dumps({"protected": {"tests": []}}))
    write(target, TEST, "def test_routes():\n    pass\n")
    assert result(inspect(target, trusted, base), CHECK).outcome.state is State.FAIL


@pytest.mark.parametrize("path", ["../outside", "/abs", "tests/*.py"])
def test_a_declared_path_must_be_a_literal_path_in_the_repository(tmp_path, path):
    target, trusted, base = _project(tmp_path, declared={"tests": [path]})
    write(target, "src/service.py", "# good updated\n")
    report = inspect(target, trusted, base)
    assert result(report, "change:policy").outcome.state is State.UNKNOWN
    assert report.exit_code == 1


def test_the_report_with_the_check_is_a_valid_replayable_document(tmp_path):
    from cli.change_conformance import parse_change_report

    target, trusted, base = _project(tmp_path)
    write(target, WORKFLOW, "on: workflow_dispatch\n")
    report = inspect(target, trusted, base)
    assert parse_change_report(report.document).document == report.document
