"""Protocol invariants established before the check/evidence implementation."""

import json
from dataclasses import replace

import pytest

from cli.check_models import (
    CheckContext,
    CheckOutcome,
    CheckSpec,
    Evidence,
    Execution,
    Finding,
    Identity,
    State,
)
from cli.check_runner import CheckRegistry, load_report, run_checks


def spec(identifier="quality", *, required=True):
    return CheckSpec(identifier, required, "Required by accepted policy", "policy.md", (".",))


def proof(*, origin="local-check"):
    return Evidence(
        "tests/results.xml",
        (".",),
        "fixture-check",
        origin,
        "a" * 64,
        ("The fixture proves execution only within its declared scope.",),
    )


def passed(context):
    return CheckOutcome(State.PASS, Execution.EXECUTED, "Measured fixture", evidence=(proof(),))


def test_failed_crashed_and_missing_checks_do_not_suppress_other_results(tmp_path):
    context = CheckContext(tmp_path, Identity("fixture"))
    registry = CheckRegistry()
    registry.register("pass", passed)
    registry.register(
        "fail",
        lambda _: CheckOutcome(
            State.FAIL, Execution.EXECUTED, "Known failure", evidence=(proof(),)
        ),
    )

    def crash(_):
        raise OSError("Unreadable dependency")

    registry.register("crash", crash)
    report = run_checks(
        context, (spec("missing"), spec("fail"), spec("pass"), spec("crash")), registry
    )
    by_id = {result.spec.id: result for result in report.results}
    assert by_id["pass"].outcome.state is State.PASS
    assert by_id["fail"].outcome.state is State.FAIL
    assert by_id["crash"].outcome.state is State.UNKNOWN
    assert by_id["crash"].outcome.execution is Execution.ERROR
    assert by_id["missing"].outcome.state is State.UNKNOWN
    assert report.exit_code == 1


@pytest.mark.parametrize(
    "state", [State.UNKNOWN, State.SKIPPED, State.NOT_APPLICABLE, State.WAIVED, State.WARN]
)
def test_required_nonpass_states_are_never_counted_as_pass(tmp_path, state):
    registry = CheckRegistry()
    registry.register(
        "quality", lambda _: CheckOutcome(state, Execution.NOT_RUN, "No independent result")
    )
    report = run_checks(CheckContext(tmp_path, Identity("fixture")), (spec(),), registry)
    assert report.exit_code == 1
    assert report.summary["pass"] == 0
    assert report.summary["required_satisfied"] == 0


@pytest.mark.parametrize(
    "origin,execution",
    [
        ("agent-assertion", Execution.EXECUTED),
        ("unverified-artifact", Execution.EXECUTED),
        ("local-check", Execution.NOT_RUN),
    ],
)
def test_pass_requires_execution_and_independent_provenance(tmp_path, origin, execution):
    registry = CheckRegistry()
    registry.register(
        "quality",
        lambda _: CheckOutcome(
            State.PASS, execution, "Claimed pass", evidence=(proof(origin=origin),)
        ),
    )
    report = run_checks(CheckContext(tmp_path, Identity("fixture")), (spec(),), registry)
    assert report.results[0].outcome.state is State.UNKNOWN
    assert report.exit_code == 1


def test_result_identity_serialization_replay_and_tampering(tmp_path):
    identity = Identity(
        "fixture", revision="abc", profile_digest="a" * 64, observed_at="2026-09-23T12:00:00Z"
    )
    registry = CheckRegistry()
    registry.register("quality", passed)
    report = run_checks(CheckContext(tmp_path, identity), (spec(),), registry)
    assert report.exit_code == 0
    encoded = report.to_json()
    assert encoded == run_checks(CheckContext(tmp_path, identity), (spec(),), registry).to_json()
    path = tmp_path / "result.json"
    path.write_text(encoded)
    assert load_report(path).to_json() == encoded
    document = json.loads(encoded)
    assert document["identity"]["revision"] == "abc"
    assert document["identity"]["change_digest"] is None
    assert document["results"][0]["findings"][0]["source_policy"] == "policy.md"
    document["results"][0]["evidence"][0]["origin"] = "agent-assertion"
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError):
        load_report(path)


def test_optional_selection_cannot_replace_required_spec_and_empty_run_is_unknown(tmp_path):
    context = CheckContext(tmp_path, Identity("fixture"))
    registry = CheckRegistry()
    registry.register("quality", passed)
    report = run_checks(context, (replace(spec(), required=False), spec()), registry)
    assert len(report.results) == 1 and report.results[0].spec.required
    empty = run_checks(context, (), registry)
    assert empty.exit_code == 1 and empty.state is State.UNKNOWN
    with pytest.raises(ValueError, match="Duplicate"):
        registry.register("quality", passed)


@pytest.mark.parametrize("kind", ["exit", "output"])
def test_protocol_violations_are_visible_without_printing_or_exiting(tmp_path, capsys, kind):
    def broken(_):
        if kind == "exit":
            raise SystemExit(0)
        print("A check must return findings, not print them")
        return passed(None)

    registry = CheckRegistry()
    registry.register("broken", broken)
    registry.register("quality", passed)
    report = run_checks(
        CheckContext(tmp_path, Identity("fixture")), (spec("broken"), spec()), registry
    )
    assert len(report.results) == 2 and report.exit_code == 1
    assert report.results[0].outcome.state is State.UNKNOWN
    assert capsys.readouterr().out == ""


def test_malformed_check_result_is_isolated_like_an_exception(tmp_path):
    registry = CheckRegistry()
    registry.register(
        "broken",
        lambda _: CheckOutcome(
            State.PASS,
            Execution.EXECUTED,
            "Invalid result",
            findings=(Finding("x", "invalid-severity", "check", "bad", "fix"),),
            evidence=(proof(),),
        ),
    )
    registry.register("quality", passed)
    report = run_checks(
        CheckContext(tmp_path, Identity("fixture")), (spec("broken"), spec()), registry
    )
    assert report.results[0].outcome.state is State.UNKNOWN
    assert report.results[1].outcome.state is State.PASS
    assert report.exit_code == 1


@pytest.mark.parametrize("corruption", ["version", "extra", "summary", "finding-id", "duplicate"])
def test_raw_result_reader_rejects_incompatible_or_inconsistent_records(tmp_path, corruption):
    registry = CheckRegistry()
    registry.register("quality", passed)
    document = run_checks(
        CheckContext(tmp_path, Identity("fixture")), (spec(),), registry
    ).to_document()
    if corruption == "version":
        document["schema_version"] = 2
    elif corruption == "extra":
        document["authenticated"] = True
    elif corruption == "summary":
        document["summary"]["required_satisfied"] = 2
    elif corruption == "finding-id":
        document["results"][0]["findings"][0]["id"] = "finding:" + "0" * 64
    else:
        document["results"].append(document["results"][0])
    path = tmp_path / "result.json"
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError):
        load_report(path)


def test_bundled_check_result_examples_validate_and_replay():
    from cli import paths

    examples = sorted((paths.GOVERNANCE_DIR / "examples/check-results").glob("*.json"))
    assert len(examples) == 3
    reports = [load_report(path) for path in examples]
    assert {report.state for report in reports} == {State.PASS, State.FAIL, State.UNKNOWN}
    assert all(report.identity.repository == "example-service" for report in reports)
