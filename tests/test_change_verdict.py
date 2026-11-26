"""`govkit conform --feature`: done, continue or escalate for one feature (L07a).

A real Git repository, the real engine and real result files. The feature and
its ignore rules are committed before the comparison base, so the change under
inspection is the edit each test makes.
"""

import json
import sys

import pytest

from cli import evidence_record
from cli.change_conformance import feature_verdict_document, parse_feature_verdict
from cli.check_models import State
from cli.govkit import main
from cli.schema_validation import DocumentError, validate_document
from tests.test_change_conformance import git, inspect, result, setup
from tests.test_discovery import write
from tests.test_evidence_report import ACCEPTANCE, BY_ID, FEATURE, PASSING, _junit
from tests.test_workflows import request

CHECK = "evidence:feature"
DEFINITION = f"features/{FEATURE}/acceptance.feature"
TESTS = ("project:tests",)


def _project(tmp_path):
    target, trusted, _ = setup(tmp_path)
    path = trusted / "conformance.json"
    config = json.loads(path.read_text())
    config["impact_rules"].append({"paths": ["features"], "impacts": {}})
    path.write_text(json.dumps(config))
    write(target, DEFINITION, ACCEPTANCE)
    write(target, ".gitignore", f"junit.xml\n{evidence_record.NAME}\n")
    git(target, "add", ".")
    git(target, "commit", "-qm", "feature")
    return target, trusted, git(target, "rev-parse", "HEAD")


def _results(target, cases=PASSING, record=True):
    _junit(target, cases)
    if record:
        evidence_record.write_record(target)


def _changed(tmp_path, cases=PASSING):
    """A project whose change is one edited source file, with recorded results."""
    target, trusted, base = _project(tmp_path)
    write(target, "src/service.py", "# good updated\n")
    _results(target, cases)
    return target, trusted, base


def _inspect(target, trusted, base, **kwargs):
    kwargs.setdefault("execute_checks", TESTS)
    return inspect(target, trusted, base, feature=FEATURE, **kwargs)


def _codes(report):
    return [(reason["state"], reason["code"]) for reason in report.verdict["reasons"]]


def _with(cases, name, status):
    return [(test, status if test == name else was, scenario) for test, was, scenario in cases]


FIRST = PASSING[0][0]


def test_done_when_the_change_and_every_result_pass(tmp_path):
    report = _inspect(*_changed(tmp_path))
    assert report.verdict["state"] == "done" and report.verdict["reasons"] == []
    checked = result(report, CHECK)
    assert checked.outcome.state is State.PASS and checked.spec.required
    assert checked.spec.scope == (f"features/{FEATURE}",)
    assert report.evidence["outcome"] == "PASS"


def test_without_a_feature_there_is_no_such_check_and_no_answer(tmp_path):
    target, trusted, base = _changed(tmp_path)
    report = inspect(target, trusted, base, execute_checks=TESTS)
    assert CHECK not in {r.spec.id for r in report.checks.results}
    assert report.verdict is None and report.evidence is None
    with pytest.raises(ValueError, match="--feature"):
        feature_verdict_document(report)


def test_a_failed_scenario_is_work_for_the_agent(tmp_path):
    report = _inspect(*_changed(tmp_path, _with(PASSING, FIRST, "fail")))
    assert report.verdict["state"] == "continue"
    assert _codes(report) == [("continue", "result-failed")]
    assert report.verdict["reasons"][0]["requirements"] == [BY_ID]
    checked = result(report, CHECK).outcome
    assert checked.state is State.FAIL and report.exit_code == 1
    assert [f.code for f in checked.findings if f.category == "evidence"] == ["result-failed"]


def test_results_from_before_the_last_edit_are_work_for_the_agent(tmp_path):
    target, trusted, base = _changed(tmp_path)
    write(target, "src/service.py", "# good updated again\n")
    report = _inspect(target, trusted, base)
    assert _codes(report) == [("continue", "results-stale")]
    assert result(report, CHECK).outcome.state is State.UNKNOWN


def test_results_that_were_never_recorded_are_work_for_the_agent(tmp_path):
    target, trusted, base = _project(tmp_path)
    write(target, "src/service.py", "# good updated\n")
    _results(target, record=False)
    assert _codes(_inspect(target, trusted, base)) == [("continue", "results-unrecorded")]


def test_no_results_at_all_is_work_for_the_agent(tmp_path):
    target, trusted, base = _project(tmp_path)
    write(target, "src/service.py", "# good updated\n")
    report = _inspect(target, trusted, base)
    assert _codes(report) == [("continue", "result-missing")]
    assert len(report.verdict["reasons"][0]["requirements"]) == 3


def test_a_skipped_test_needs_a_person(tmp_path):
    report = _inspect(*_changed(tmp_path, _with(PASSING, FIRST, "skip")))
    assert report.verdict["state"] == "escalate"
    assert _codes(report) == [("escalate", "result-skipped")]


def test_a_required_check_that_did_not_run_needs_a_person(tmp_path):
    target, trusted, base = _changed(tmp_path)
    report = _inspect(target, trusted, base, execute_checks=())
    assert report.verdict["state"] == "escalate"
    assert {reason["code"] for reason in report.verdict["reasons"]} == {"check-not-satisfied"}
    assert "project:tests" in {reason["check"] for reason in report.verdict["reasons"]}


def test_a_failing_project_command_is_work_for_the_agent(tmp_path):
    target, trusted, base = _project(tmp_path)
    write(target, "src/service.py", "# broken\n")
    _results(target)
    report = _inspect(target, trusted, base)
    assert report.verdict["state"] == "continue"
    assert ("continue", "check-failed") in _codes(report)


def test_a_weakened_definition_needs_a_person_before_anything_else(tmp_path):
    target, trusted, base = _project(tmp_path)
    kept = ACCEPTANCE.replace("200 ms", "900 ms")
    assert kept != ACCEPTANCE
    write(target, DEFINITION, kept)
    _results(target, _with(PASSING, FIRST, "fail"))
    document = request()
    document["scope"] = ["src", "features"]
    report = _inspect(target, trusted, base, doc=document)
    assert report.verdict["state"] == "escalate"
    assert _codes(report)[0] == ("escalate", "definition-changed")
    assert ("continue", "result-failed") in _codes(report)


def test_an_unknown_feature_is_refused_before_anything_runs(tmp_path):
    target, trusted, base = _changed(tmp_path)
    with pytest.raises(ValueError, match="matched no feature directory"):
        inspect(target, trusted, base, feature="nowhere", execute_checks=TESTS)


def test_the_answer_document_holds_both_reports_and_replays(tmp_path):
    report = _inspect(*_changed(tmp_path, _with(PASSING, FIRST, "fail")))
    document = feature_verdict_document(report)
    validate_document(document, "feature-verdict")
    assert document["kind"] == "govkit.feature-verdict"
    assert document["state"] == "continue" and document["exit_code"] == 1
    assert document["change"] == report.document and document["evidence"] == report.evidence
    assert parse_feature_verdict(json.loads(json.dumps(document))) == document


@pytest.mark.parametrize(
    "edit",
    [
        lambda d: d.update(state="done", exit_code=0, reasons=[]),
        lambda d: d["evidence"].update(outcome="PASS"),
        lambda d: d["reasons"][0].update(code="result-missing"),
        lambda d: d["change"]["checks"]["results"].pop(),
        lambda d: d.update(feature="another"),
    ],
)
def test_an_edited_answer_document_does_not_replay(tmp_path, edit):
    report = _inspect(*_changed(tmp_path, _with(PASSING, FIRST, "fail")))
    document = json.loads(json.dumps(feature_verdict_document(report)))
    edit(document)
    with pytest.raises(DocumentError):
        parse_feature_verdict(document)


def test_the_bundled_example_validates_and_replays():
    from cli import paths

    example = paths.REPO_ROOT / "governance/examples/feature-verdict/feature-verdict.json"
    document = json.loads(example.read_text(encoding="utf-8"))
    assert parse_feature_verdict(document) == document
    assert document["state"] == "continue"
    assert {reason["state"] for reason in document["reasons"]} == {"continue", "escalate"}


def _run(monkeypatch, capsys, tmp_path, project, *extra, feature=FEATURE):
    target, trusted, base = project
    source = write(tmp_path, "request.json", json.dumps(request()))
    arguments = ["govkit", "conform", "--target", str(target), "--request", str(source)]
    arguments += ["--base", base, "--policy-target", str(trusted)]
    arguments += ["--observed-at", "2026-09-23T12:00:00Z", "--execute-check", "project:tests"]
    monkeypatch.setattr(sys, "argv", arguments + ["--feature", feature, *extra])
    with pytest.raises(SystemExit) as stopped:
        main()
    return stopped.value.code, capsys.readouterr()


class TestCommand:
    def test_done_exits_zero_and_says_so(self, tmp_path, monkeypatch, capsys):
        code, output = _run(monkeypatch, capsys, tmp_path, _changed(tmp_path))
        assert code == 0
        assert f"Feature {FEATURE}: DONE" in output.out
        assert "stop condition, not a gate" in output.out
        assert "Conformance checks: PASS" in output.out

    def test_continue_exits_one_and_names_the_work(self, tmp_path, monkeypatch, capsys):
        project = _changed(tmp_path, _with(PASSING, FIRST, "fail"))
        code, output = _run(monkeypatch, capsys, tmp_path, project)
        assert code == 1
        assert f"Feature {FEATURE}: CONTINUE" in output.out
        assert "result-failed" in output.out and BY_ID in output.out
        assert "Fix the implementation" in output.out

    def test_escalate_exits_three(self, tmp_path, monkeypatch, capsys):
        project = _changed(tmp_path, _with(PASSING, FIRST, "skip"))
        code, output = _run(monkeypatch, capsys, tmp_path, project)
        assert code == 3 and f"Feature {FEATURE}: ESCALATE" in output.out

    def test_json_prints_the_answer_document(self, tmp_path, monkeypatch, capsys):
        project = _changed(tmp_path, _with(PASSING, FIRST, "skip"))
        code, output = _run(monkeypatch, capsys, tmp_path, project, "--json")
        document = json.loads(output.out)
        assert code == 3 and document["state"] == "escalate"
        assert parse_feature_verdict(document) == document

    def test_an_unknown_feature_exits_two(self, tmp_path, monkeypatch, capsys):
        code, output = _run(monkeypatch, capsys, tmp_path, _changed(tmp_path), feature="nowhere")
        assert code == 2 and "matched no feature directory" in output.err
        assert output.out == ""

    def test_a_feature_needs_the_change_options(self, tmp_path, monkeypatch, capsys):
        target, _, _ = _changed(tmp_path)
        arguments = ["govkit", "conform", "--target", str(target), "--feature", FEATURE]
        monkeypatch.setattr(sys, "argv", arguments)
        with pytest.raises(SystemExit) as stopped:
            main()
        assert stopped.value.code == 2
        assert "--feature requires --request" in capsys.readouterr().err

    def test_without_a_feature_the_output_is_what_it_was(self, tmp_path, monkeypatch, capsys):
        target, trusted, base = _changed(tmp_path)
        source = write(tmp_path, "request.json", json.dumps(request()))
        arguments = ["govkit", "conform", "--target", str(target), "--request", str(source)]
        arguments += ["--base", base, "--policy-target", str(trusted), "--json"]
        arguments += ["--observed-at", "2026-09-23T12:00:00Z", "--execute-check", "project:tests"]
        monkeypatch.setattr(sys, "argv", arguments)
        main()
        printed = json.loads(capsys.readouterr().out)
        expected = inspect(target, trusted, base, execute_checks=TESTS).document
        assert printed == expected and printed["kind"] == "change-results"
