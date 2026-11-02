"""Experiment references in request planning and change conformance (Phase A Increment 6)."""

import json
from pathlib import Path

import pytest

from cli import paths
from cli.change_conformance import inspect_change, parse_change_report
from cli.check_models import State
from cli.schema_validation import DocumentError
from cli.workflow_store import parse_workflow_plan
from cli.workflows import parse_request
from tests.test_change_conformance import git, result, setup
from tests.test_discovery import write
from tests.test_workflows import install, plan, request

GOLDENS = Path(__file__).parent / "fixtures/request-replay-v1"
SCENARIOS = paths.GOVERNANCE_DIR / "examples/experiments"
RECORD = "features/discovery/experiments.yaml"
LATER = "2026-11-10T00:00:00Z"  # the bundled scenarios' documented assessment time


def experiment_request(change="enhancement", record=RECORD, **impacts):
    document = request(change, **impacts)
    document["references"] = [{"kind": "experiment", "reference": record, "authority": "accepted"}]
    return document


def artifacts(report):
    return {a["id"] for a in report.document["artifacts"]}


def decision(report, code):
    return next((d for d in report.document["decisions"] if d["code"] == code), None)


# --- Baseline replay: inputs without experiment references are unchanged ------


@pytest.mark.parametrize("golden", sorted(GOLDENS.glob("*-plan.json")), ids=lambda p: p.stem)
def test_baseline_plans_replay_byte_identically(golden):
    document = json.loads(golden.read_text())
    assert parse_workflow_plan(document).document == document
    assert "experiment-record" not in {a["id"] for a in document["artifacts"]}


def test_baseline_change_report_replays_byte_identically():
    document = json.loads((GOLDENS / "feature-change-report.json").read_text())
    assert parse_change_report(document).document == document


# --- Request routing -------------------------------------------------------------


def copy_scenario(name, *targets):
    for target in targets:
        for path in (SCENARIOS / name).rglob("*"):
            if path.is_file() and path.name != "expected.json":
                write(target, path.relative_to(SCENARIOS / name).as_posix(), path.read_text())


@pytest.mark.parametrize("change", ["enhancement", "refactor", "maintenance"])
def test_bounded_work_with_an_experiment_reference_routes_full_feature(tmp_path, change):
    install(tmp_path)
    copy_scenario("relied", tmp_path)
    report = plan(tmp_path, experiment_request(change))
    assert report.document["workflow"] == "full-feature"
    assert report.ready, report.document["decisions"]
    escalated = decision(report, "experiment-escalated")
    assert escalated and escalated["blocking"] is False
    assert {"experiment-record", "architecture-preflight"} <= artifacts(report)
    record = next(a for a in report.document["artifacts"] if a["id"] == "experiment-record")
    assert "never self-approve" in record["reason"]


def test_defect_with_an_experiment_reference_never_takes_the_short_path(tmp_path):
    install(tmp_path)
    copy_scenario("relied", tmp_path)
    write(tmp_path, "tests/regression.py", "def test_regression(): assert True\n")
    document = experiment_request("defect")
    document["references"] += [
        {"kind": "established-behavior", "reference": "architecture.md", "authority": "accepted"},
        {"kind": "regression-test", "reference": "tests/regression.py", "authority": "accepted"},
    ]
    document["preference"] = "defect"
    report = plan(tmp_path, document)
    assert report.document["workflow"] == "full-feature"
    assert decision(report, "experiment-escalated")
    assert decision(report, "defect-ineligible") is None
    assert "fix-record" not in artifacts(report)


def test_architecture_work_keeps_its_workflow_and_adds_the_record(tmp_path):
    install(tmp_path)
    copy_scenario("relied", tmp_path)
    report = plan(tmp_path, experiment_request("enhancement", architecture=True))
    assert report.document["workflow"] == "architecture"
    assert decision(report, "experiment-escalated") is None
    assert "experiment-record" in artifacts(report)


def test_missing_experiment_record_blocks_planning(tmp_path):
    install(tmp_path)
    report = plan(tmp_path, experiment_request())
    assert not report.ready
    assert decision(report, "unavailable-reference")


def test_experiment_plans_replay(tmp_path):
    install(tmp_path)
    copy_scenario("relied", tmp_path)
    report = plan(tmp_path, experiment_request())
    assert parse_workflow_plan(report.document).document == report.document


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["references"][0].update(kind="experiments"),
        lambda d: d.update(waive_checks=["artifact:experiment-record"]),
    ],
)
def test_unknown_reference_kinds_and_waivers_are_still_rejected(mutate):
    document = experiment_request()
    mutate(document)
    with pytest.raises(DocumentError):
        parse_request(document)


# --- Change conformance -----------------------------------------------------------


def conform(tmp_path, scenario="relied", *, target_scenario=None, preflight=None):
    target, trusted, _ = setup(tmp_path)
    copy_scenario(scenario, trusted)
    if target_scenario is not False:
        copy_scenario(target_scenario or scenario, target)
    if preflight is not None:
        write(target, "docs/architecture-preflight.md", preflight)
    git(target, "add", ".")
    git(target, "commit", "-qm", "records", "--allow-empty")
    base = git(target, "rev-parse", "HEAD")
    write(target, "src/service.py", "# good changed\n")
    return inspect_change(
        target,
        parse_request(experiment_request()),
        base=base,
        policy_target=trusted,
        observed_at=LATER,
    )


def test_a_passed_fresh_relied_upon_record_passes_with_a_limitation(tmp_path):
    report = conform(tmp_path)
    checked = result(report, "artifact:experiment-record")
    assert checked.outcome.state is State.PASS, checked.outcome
    assert report.plan.document["workflow"] == "full-feature"
    evidence = checked.outcome.evidence
    assert evidence and evidence[0].origin == "local-check"
    assert evidence[0].source == RECORD
    assert any("does not authenticate execution" in text for text in evidence[0].limitations)
    assert parse_change_report(report.document).document == report.document


def test_a_missing_record_in_the_change_fails(tmp_path):
    report = conform(tmp_path, target_scenario=False)
    assert result(report, "artifact:experiment-record").outcome.state is State.FAIL


def test_stale_reliance_fails(tmp_path):
    report = conform(tmp_path, "stale")
    checked = result(report, "artifact:experiment-record")
    assert checked.outcome.state is State.FAIL
    assert "stale-reliance" in {f.code for f in checked.outcome.findings}


def test_an_outstanding_experiment_is_unknown_and_fails_the_exit_code(tmp_path):
    report = conform(tmp_path, "required")
    checked = result(report, "artifact:experiment-record")
    assert checked.outcome.state is State.UNKNOWN
    assert report.exit_code == 1


def outcome_block(status, extra=""):
    return (
        "# Architecture preflight\n\n```yaml\npreflight_outcome:\n"
        f"  status: {status}\n  reason: Recorded for the conformance test.\n{extra}```\n"
    )


@pytest.mark.parametrize(
    "status,extra,expected",
    [
        ("experiment-required", "  experiments:\n  - EXP-001\n", State.UNKNOWN),
        ("adr-required", "", State.UNKNOWN),
        ("blocked", "", State.FAIL),
        ("approved-for-planning", "", State.PASS),
    ],
)
def test_architecture_preflight_honors_a_declared_outcome(tmp_path, status, extra, expected):
    report = conform(tmp_path, preflight=outcome_block(status, extra))
    assert result(report, "artifact:architecture-preflight").outcome.state is expected


def test_an_invalid_outcome_block_fails_the_preflight_artifact(tmp_path):
    report = conform(tmp_path, preflight=outcome_block("maybe"))
    assert result(report, "artifact:architecture-preflight").outcome.state is State.FAIL


def test_a_preflight_without_a_block_behaves_as_before(tmp_path):
    report = conform(tmp_path)
    assert result(report, "artifact:architecture-preflight").outcome.state is State.PASS


def test_a_tampered_report_cannot_flip_the_record_state(tmp_path):
    document = conform(tmp_path, "required").document
    for item in document["checks"]["results"]:
        if item["id"] == "artifact:experiment-record":
            item["state"] = "pass"
    with pytest.raises(DocumentError):
        parse_change_report(document)


def test_posture_projection_preserves_the_experiment_artifact(tmp_path):
    from cli.posture import reference
    from cli.posture_change import export_change_posture

    report = conform(tmp_path)
    document = export_change_posture(report.document).document
    refs = {a["ref"] for a in document["workflow"]["artifacts"]}
    assert reference("artifact", "experiment-record") in refs
    assert len(document["results"]["controls"]) == len(report.checks.results)
