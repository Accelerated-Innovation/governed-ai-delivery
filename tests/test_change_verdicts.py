"""One conformance run that judges every feature a change touches (L08b)."""

import json

import pytest

from cli import evidence_record
from cli.change_conformance import feature_verdicts_document, parse_feature_verdicts
from cli.check_models import State
from cli.schema_validation import DocumentError
from tests.test_change_conformance import git, inspect, setup
from tests.test_change_verdict import CRITERIA, FEATURE, FULL, PASSING, TESTS, _with
from tests.test_discovery import write
from tests.test_evidence_report import _junit
from tests.test_validate import make_full_feature
from tests.test_workflows import request

OTHER, UNTOUCHED = "08_refunds", "09_untouched"
# The second feature's scenarios, bound by id so its tests are its own.
OTHER_FULL = """Feature: Refunds

  @nfr-performance @scenario:refund-is-fast
  Scenario: A refund is fast
    Given a refund
    Then it completes quickly

  @nfr-security @scenario:refund-needs-approval
  Scenario: A refund needs approval
    Given a refund
    Then it waits for approval
"""
OTHER_CASES = [
    ("test_refund_fast", "pass", f"{OTHER}#scenario:refund-is-fast"),
    ("test_refund_approval", "pass", f"{OTHER}#scenario:refund-needs-approval"),
]
# Work on feature definitions is a full feature, not bounded work under a contract.
SCOPE = {**request("feature"), "scope": ["src", "features"]}


def _project(tmp_path):
    target, trusted, _ = setup(tmp_path, project_type="api")
    path = trusted / "conformance.json"
    config = json.loads(path.read_text())
    config["impact_rules"].append({"paths": ["features"], "impacts": {}})
    path.write_text(json.dumps(config))
    for name, definition in ((FEATURE, FULL), (OTHER, OTHER_FULL), (UNTOUCHED, OTHER_FULL)):
        make_full_feature(
            target / "features" / name,
            **{"acceptance.feature": definition, "eval_criteria.yaml": CRITERIA},
        )
    write(target, ".gitignore", f"junit.xml\n{evidence_record.NAME}\n")
    git(target, "add", ".")
    git(target, "commit", "-qm", "features")
    return target, trusted, git(target, "rev-parse", "HEAD")


def _touch(target, *names):
    for name in names:
        with (target / "features" / name / "architecture_preflight.md").open("a") as stream:
            stream.write("\nReviewed again.\n")


def _results(target, cases):
    _junit(target, cases)
    evidence_record.write_record(target)


def _inspect(target, trusted, base, **kwargs):
    kwargs.setdefault("execute_checks", TESTS)
    return inspect(target, trusted, base, doc=SCOPE, changed_features=True, **kwargs)


def _states(report):
    return {verdict["feature"]: verdict["state"] for _, verdict in report.answers}


def _ids(report, prefix):
    return sorted(r.spec.id for r in report.checks.results if r.spec.id.startswith(prefix))


def test_a_change_that_touches_no_feature_judges_none(tmp_path):
    target, trusted, base = _project(tmp_path)
    write(target, "src/service.py", "# good updated\n")
    report = _inspect(target, trusted, base)
    assert report.answers == () and _ids(report, "evidence:feature") == []
    plain = inspect(target, trusted, base, doc=SCOPE, execute_checks=TESTS)
    assert report.document == plain.document and plain.answers is None
    document = feature_verdicts_document(report)
    assert document["features"] == [] and parse_feature_verdicts(document) == document


def test_each_touched_feature_gets_its_own_checks_and_answer(tmp_path):
    target, trusted, base = _project(tmp_path)
    _touch(target, FEATURE, OTHER)
    _results(target, [*PASSING, *OTHER_CASES])
    report = _inspect(target, trusted, base)
    assert _states(report) == {FEATURE: "done", OTHER: "done"}
    assert _ids(report, "evidence:feature") == [
        f"evidence:feature[{FEATURE}]",
        f"evidence:feature[{OTHER}]",
    ]
    assert len(_ids(report, "feature:")) == 14
    assert not any(UNTOUCHED in r.spec.id for r in report.checks.results)
    assert report.exit_code == 0 and report.verdict is None and report.evidence is None


def test_one_feature_short_does_not_change_the_other_answer(tmp_path):
    target, trusted, base = _project(tmp_path)
    _touch(target, FEATURE, OTHER)
    (target / "features" / OTHER / "plan.md").unlink()
    _results(target, [*_with(PASSING, PASSING[0][0], "skip"), *OTHER_CASES])
    report = _inspect(target, trusted, base)
    assert _states(report) == {FEATURE: "escalate", OTHER: "continue"}
    answers = {verdict["feature"]: verdict for _, verdict in report.answers}
    assert [(r["code"], r["check"]) for r in answers[FEATURE]["reasons"]] == [
        ("result-skipped", f"evidence:feature[{FEATURE}]")
    ]
    assert {(r["code"], r["check"]) for r in answers[OTHER]["reasons"]} == {
        ("check-failed", f"feature:completeness[{OTHER}]")
    }
    # A feature that is not done fails the run through its own required checks.
    assert report.exit_code == 1
    assert report.checks.state is State.FAIL


def test_a_failure_of_the_change_itself_reaches_every_answer(tmp_path):
    target, trusted, base = _project(tmp_path)
    _touch(target, FEATURE, OTHER)
    write(target, "src/service.py", "# broken\n")
    _results(target, [*PASSING, *OTHER_CASES])
    report = _inspect(target, trusted, base)
    assert _states(report) == {FEATURE: "continue", OTHER: "continue"}
    for _, verdict in report.answers:
        assert "project:tests" in {reason["check"] for reason in verdict["reasons"]}


def test_a_path_elsewhere_that_shares_a_feature_name_does_not_select_it(tmp_path):
    target, trusted, base = _project(tmp_path)
    write(target, f"src/{FEATURE}/service.py", "# good\n")
    write(target, f"docs/{OTHER}/notes.md", "# notes\n")
    assert _inspect(target, trusted, base).answers == ()


def test_a_new_feature_directory_is_judged(tmp_path):
    target, trusted, base = _project(tmp_path)
    make_full_feature(
        target / "features" / "10_new",
        **{"acceptance.feature": OTHER_FULL, "eval_criteria.yaml": CRITERIA},
    )
    assert _states(_inspect(target, trusted, base)) == {"10_new": "continue"}


def test_one_named_feature_and_every_touched_feature_do_not_combine(tmp_path):
    target, trusted, base = _project(tmp_path)
    with pytest.raises(ValueError, match="not both"):
        _inspect(target, trusted, base, feature=FEATURE)


def test_a_configured_check_with_a_scoped_identifier_is_refused(tmp_path):
    target, trusted, base = _project(tmp_path)
    _touch(target, FEATURE)
    path = trusted / "conformance.json"
    config = json.loads(path.read_text())
    config["commands"].append(
        {
            "id": f"evidence:feature[{FEATURE}]",
            "argv": ["{python}", "-c", "pass"],
            "timeout_seconds": 5,
        }
    )
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="reserved for judging a feature"):
        _inspect(target, trusted, base)


@pytest.fixture
def answers(tmp_path):
    target, trusted, base = _project(tmp_path)
    _touch(target, FEATURE, OTHER)
    _results(target, [*_with(PASSING, PASSING[0][0], "fail"), *OTHER_CASES])
    return feature_verdicts_document(_inspect(target, trusted, base))


def test_the_answers_document_holds_the_change_once_and_replays(answers):
    assert answers["kind"] == "govkit.feature-verdicts"
    assert [a["feature"] for a in answers["features"]] == [FEATURE, OTHER]
    assert [a["state"] for a in answers["features"]] == ["continue", "done"]
    assert answers["change"]["kind"] == "change-results"
    assert parse_feature_verdicts(json.loads(json.dumps(answers))) == answers


@pytest.mark.parametrize(
    "edit",
    [
        lambda d: d["features"][0].update(state="done", exit_code=0, reasons=[]),
        lambda d: d["features"].pop(),
        lambda d: d["features"].reverse(),
        lambda d: d["features"][1]["evidence"].update(outcome="FAIL"),
        lambda d: d["features"][0].update(evidence=d["features"][1]["evidence"]),
        lambda d: d["features"][0].update(feature=UNTOUCHED),
        lambda d: d["change"]["checks"]["results"].pop(),
        lambda d: d["features"][0]["evidence"].update(feature=None),
        lambda d: d["features"][0]["evidence"].update(feature=["x"]),
    ],
)
def test_edited_answers_do_not_replay(answers, edit):
    document = json.loads(json.dumps(answers))
    edit(document)
    with pytest.raises(DocumentError):
        parse_feature_verdicts(document)


def test_answers_need_a_run_that_judged_the_touched_features(tmp_path):
    target, trusted, base = _project(tmp_path)
    with pytest.raises(ValueError, match="judged the touched features"):
        feature_verdicts_document(inspect(target, trusted, base, doc=SCOPE, execute_checks=TESTS))


def test_the_answers_schema_reuses_the_single_answer_definitions():
    from cli import paths

    def schema(name):
        path = paths.GOVERNANCE_DIR / "schemas" / f"{name}.schema.json"
        return json.loads(path.read_text(encoding="utf-8"))

    one, many = schema("feature-verdict"), schema("feature-verdicts")
    item = many["properties"]["features"]["items"]
    for key in ("state", "exit_code", "reasons", "evidence"):
        assert item["properties"][key] == one["properties"][key], key
    assert item["allOf"] == one["allOf"]
    assert many["properties"]["change"] == one["properties"]["change"]


def test_the_bundled_answers_example_validates_and_replays():
    from cli import paths

    example = paths.GOVERNANCE_DIR / "examples/feature-verdict/feature-verdicts.json"
    document = json.loads(example.read_text(encoding="utf-8"))
    assert parse_feature_verdicts(document) == document
    assert [answer["state"] for answer in document["features"]] == ["continue", "done"]
