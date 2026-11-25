"""`change:definition` in actual-change conformance (L06a).

A real Git repository and the real engine: the check reads the snapshot that
`change_conformance` already captures, and is present only when the change
touches a feature definition file.
"""

from cli.check_models import State
from tests.test_change_conformance import git, inspect, result, setup
from tests.test_definition_change import ACCEPTANCE, CRITERIA, FEATURE, YAML
from tests.test_discovery import write

CHECK = "change:definition"


def _project(tmp_path):
    """A committed feature definition; the comparison base is that commit."""
    target, trusted, _ = setup(tmp_path)
    write(target, ACCEPTANCE, FEATURE)
    write(target, CRITERIA, YAML)
    git(target, "add", ".")
    git(target, "commit", "-qm", "feature")
    return target, trusted, git(target, "rev-parse", "HEAD")


def _found(outcome):
    """The check's own findings; the runner adds a summary finding of category "check"."""
    return [f for f in outcome.findings if f.category == "change"]


def _ids(report):
    return {r.spec.id for r in report.checks.results}


def test_a_change_that_touches_no_definition_has_no_such_check(tmp_path):
    target, trusted, base = _project(tmp_path)
    write(target, "src/service.py", "# good updated\n")
    assert CHECK not in _ids(inspect(target, trusted, base))


def test_adding_a_scenario_and_a_criterion_passes(tmp_path):
    target, trusted, base = _project(tmp_path)
    write(target, ACCEPTANCE, FEATURE + "\n    Scenario: New\n      Given something new\n")
    write(target, CRITERIA, YAML + "  - name: refusal-safety\n    threshold: 0.99\n")
    outcome = result(inspect(target, trusted, base), CHECK).outcome
    assert outcome.state is State.PASS
    assert _found(outcome) == []
    assert "2 definition files" in outcome.summary


def test_a_new_feature_passes(tmp_path):
    target, trusted, base = _project(tmp_path)
    write(target, "features/08_new/acceptance.feature", FEATURE)
    assert result(inspect(target, trusted, base), CHECK).outcome.state is State.PASS


def test_weakening_fails_and_names_each_requirement(tmp_path):
    target, trusted, base = _project(tmp_path)
    write(target, ACCEPTANCE, FEATURE.replace("12000", "1"))
    write(target, CRITERIA, YAML.replace("0.9", "0.5"))
    report = inspect(target, trusted, base)
    checked = result(report, CHECK)
    assert checked.outcome.state is State.FAIL
    assert report.exit_code == 1
    assert sorted((f.code, f.location) for f in _found(checked.outcome)) == [
        ("criterion-altered", CRITERIA),
        ("scenario-altered", ACCEPTANCE),
    ]
    assert all(f.severity == "error" for f in _found(checked.outcome))
    assert "07_invoice#scenario:routing" in _found(checked.outcome)[0].message
    assert checked.spec.required and set(checked.spec.scope) == {ACCEPTANCE, CRITERIA}


def test_a_deleted_definition_fails(tmp_path):
    target, trusted, base = _project(tmp_path)
    (target / ACCEPTANCE).unlink()
    outcome = result(inspect(target, trusted, base), CHECK).outcome
    assert outcome.state is State.FAIL
    assert [f.code for f in _found(outcome)] == ["definition-removed"]


def test_a_staged_or_committed_weakening_is_seen_too(tmp_path):
    target, trusted, base = _project(tmp_path)
    write(target, ACCEPTANCE, FEATURE.replace("a signed-in clerk", "anyone"))
    git(target, "add", ".")
    git(target, "commit", "-qm", "loosen the shared steps")
    outcome = result(inspect(target, trusted, base), CHECK).outcome
    assert outcome.state is State.FAIL
    assert {f.code for f in _found(outcome)} == {"shared-steps-changed"}


def test_a_base_that_cannot_be_compared_is_unknown(tmp_path):
    target, trusted, _ = setup(tmp_path)
    write(target, ACCEPTANCE, "Scenario: no feature line\n")
    git(target, "add", ".")
    git(target, "commit", "-qm", "broken")
    base = git(target, "rev-parse", "HEAD")
    write(target, ACCEPTANCE, FEATURE)
    report = inspect(target, trusted, base)
    assert result(report, CHECK).outcome.state is State.UNKNOWN
    assert report.exit_code == 1


def test_a_failure_outranks_an_unknown(tmp_path):
    target, trusted, _ = setup(tmp_path)
    write(target, ACCEPTANCE, "Scenario: no feature line\n")
    write(target, CRITERIA, YAML)
    git(target, "add", ".")
    git(target, "commit", "-qm", "base")
    base = git(target, "rev-parse", "HEAD")
    write(target, ACCEPTANCE, FEATURE)
    write(target, CRITERIA, YAML.replace("0.9", "0.5"))
    outcome = result(inspect(target, trusted, base), CHECK).outcome
    assert outcome.state is State.FAIL
    assert sorted(f.severity for f in _found(outcome)) == ["error", "warning"]


def test_the_report_with_the_check_is_a_valid_replayable_document(tmp_path):
    from cli.change_conformance import parse_change_report

    target, trusted, base = _project(tmp_path)
    write(target, ACCEPTANCE, FEATURE.replace("12000", "1"))
    report = inspect(target, trusted, base)
    assert parse_change_report(report.document).document == report.document
