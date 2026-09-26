"""Canonical change reports can be shared without losing execution or exposing prose."""

import json
import socket
import subprocess
from copy import deepcopy
from dataclasses import replace

import pytest

from cli import paths
from cli.change_conformance import parse_change_report
from cli.check_models import (
    CheckOutcome,
    CheckResult,
    CheckSpec,
    Evidence,
    Execution,
    Finding,
    State,
)
from cli.check_runner import normalize
from cli.posture import reference
from cli.posture_change import export_change_posture, parse_change_posture, render_change_posture
from cli.schema_validation import canonical_json, content_digest
from tests.test_change_conformance import configure_transition, git, inspect, setup, transition
from tests.test_discovery import write
from tests.test_pack_store import snapshot
from tests.test_workflows import request


def changed(tmp_path, *, kind="enhancement", llm=False, execute=True, good=True):
    target, trusted, base = setup(tmp_path, llm=llm)
    if not good:
        write(target, "results.json", '{"cases":[{"id":"hello","expected":"hi","actual":"wrong"}]}')
        git(target, "add", "results.json")
        git(target, "commit", "-qm", "failing evaluation fixture")
        base = git(target, "rev-parse", "HEAD")
    write(target, "src/service.py", "# good updated\n")
    checks = ("project:tests", "llm-exact-match") if llm else ("project:tests",)
    doc = request(kind)
    if llm:
        doc["impacts"]["llm"] = True
    source = inspect(
        target,
        trusted,
        base,
        doc,
        execute_checks=checks if execute else (),
        pack_arguments={"llm-exact-match": ("--results", "results.json")}
        if llm and execute
        else {},
    )
    return target, trusted, source


def redigest(document):
    document["digest"] = content_digest(
        canonical_json({k: v for k, v in document.items() if k != "digest"}).encode()
    )
    return document


def replace_recorded_spec(source, **changes):
    return replace(
        source,
        checks=replace(
            source.checks,
            results=tuple(
                replace(c, spec=replace(c.spec, **changes)) if c.spec.id == "project:tests" else c
                for c in source.checks.results
            ),
        ),
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("scope", ("src/narrow",)),
        ("source_policy", "substituted-policy.md"),
        ("reason", "a different obligation"),
    ],
)
def test_export_rejects_narrowed_or_substituted_planned_control_metadata(tmp_path, field, value):
    target, trusted, source = changed(tmp_path)
    source = replace_recorded_spec(source, **{field: value})
    assert parse_change_report(source.document).document == source.document
    before = snapshot(target), snapshot(trusted)

    with pytest.raises(ValueError, match="planned control"):
        export_change_posture(source.document)

    assert (snapshot(target), snapshot(trusted)) == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("scope_refs", [reference("scope", "src/narrow")]),
        ("policy_ref", reference("source", "substituted-policy.md")),
        ("reason_ref", reference("reason", "a different obligation")),
    ],
)
def test_replay_rejects_redigested_narrowed_or_substituted_control_metadata(tmp_path, field, value):
    _, _, source = changed(tmp_path)
    doc = export_change_posture(source.document).document
    control = next(
        c for c in doc["results"]["controls"] if c["ref"] == reference("control", "project:tests")
    )
    control[field] = value
    redigest(doc)

    with pytest.raises(ValueError, match="planned control"):
        parse_change_posture(doc)


def test_export_accepts_canonical_scope_union_without_losing_planned_metadata(tmp_path):
    _, _, source = changed(tmp_path)
    original = next(c.spec for c in source.checks.results if c.spec.id == "project:tests")
    source = replace_recorded_spec(source, scope=tuple(sorted({*original.scope, "additional"})))
    assert parse_change_report(source.document).document == source.document

    doc = export_change_posture(source.document).document

    control = next(
        c for c in doc["results"]["controls"] if c["ref"] == reference("control", "project:tests")
    )
    assert set(control["scope_refs"]) == {
        reference("scope", s) for s in (*original.scope, "additional")
    }
    assert control["policy_ref"] == reference("source", original.source_policy)
    assert control["reason_ref"] == reference("reason", original.reason)
    assert parse_change_posture(doc).document == doc


@pytest.mark.parametrize("section", ["controls", "artifacts", "decisions"])
@pytest.mark.parametrize("tamper", ["section", "index", "leading-zero"])
def test_replay_rejects_source_pointers_that_do_not_match_the_record(tmp_path, section, tamper):
    target, trusted, base = setup(tmp_path)
    write(target, "src/service.py", "# good changed\n")
    source = inspect(target, trusted, base, request(llm=True))
    doc = export_change_posture(source.document).document
    records = doc["results"]["controls"] if section == "controls" else doc["workflow"][section]
    assert records
    prefix = "/checks/results" if section == "controls" else "/plan/" + section
    records[0]["local_ref"] = {
        "section": "/plan/checks/0",
        "index": prefix + "/1",
        "leading-zero": prefix + "/00",
    }[tamper]
    redigest(doc)

    with pytest.raises(ValueError):
        parse_change_posture(doc)


@pytest.mark.parametrize("kind,workflow", [("enhancement", "bounded"), ("feature", "full-feature")])
def test_projection_preserves_actual_workflow_controls_and_findings_without_writes(
    tmp_path, kind, workflow
):
    target, trusted, source = changed(tmp_path, kind=kind)
    before = snapshot(target), snapshot(trusted)

    report = export_change_posture(source.document)

    doc = report.document
    assert doc["kind"] == "change-posture"
    assert doc["workflow"]["selected"] == workflow
    assert doc["coverage"]["maintenance"] == "not-supplied"
    assert doc["coverage"]["origin"] == "unauthenticated-snapshot"
    assert doc["results"]["summary"] == source.checks.summary
    assert doc["results"]["exit_code"] == source.exit_code
    assert doc["results"]["state"] == source.state.value
    assert [
        (c["ref"], c["required"], c["state"], c["execution"], len(c["findings"]))
        for c in doc["results"]["controls"]
    ] == [
        (
            reference("control", c["id"]),
            c["required"],
            c["state"],
            c["execution"],
            len(c["findings"]),
        )
        for c in source.document["checks"]["results"]
    ]
    human = render_change_posture(report)
    for c in doc["results"]["controls"]:
        assert c["ref"] in human and c["state"] in human and c["execution"] in human
        for f in c["findings"]:
            assert f["ref"] in human and f["action_ref"] in human
    assert parse_change_posture(json.loads(report.to_json())).document == doc
    assert export_change_posture(deepcopy(source.document)).to_json() == report.to_json()
    assert (snapshot(target), snapshot(trusted)) == before


@pytest.mark.parametrize(
    "execute,good,state", [(True, True, "pass"), (True, False, "fail"), (False, True, "skipped")]
)
def test_actual_llm_evaluation_remains_independent_of_small_workflow(
    tmp_path, execute, good, state
):
    _, _, source = changed(tmp_path, llm=True, execute=execute, good=good)

    doc = export_change_posture(source.document).document

    assert doc["workflow"]["selected"] == "bounded"
    assert "llm-evaluation" in [c["label"] for c in doc["capabilities"]["change_required"]]
    evaluation = next(c for c in doc["results"]["controls"] if c["label"] == "llm-exact-match")
    assert evaluation["state"] == state
    assert evaluation["required"] is True
    assert evaluation["execution"] == ("executed" if execute else "not-run")
    assert doc["results"]["exit_code"] == source.exit_code == (0 if state == "pass" else 1)


@pytest.mark.parametrize(
    "state", [State.UNKNOWN, State.SKIPPED, State.WAIVED, State.NOT_APPLICABLE]
)
def test_required_unknown_skipped_waived_and_not_applicable_never_become_satisfied(tmp_path, state):
    _, _, source = changed(tmp_path)
    extra = CheckResult(
        CheckSpec("private-control", True, "private reason", "private policy", ("private/path",)),
        CheckOutcome(state, Execution.NOT_RUN, "private summary"),
    )
    # Use the canonical normalizer/serializer so this is a valid saved report.
    extra = replace(extra, outcome=normalize(extra.outcome))
    source = replace(source, checks=replace(source.checks, results=(*source.checks.results, extra)))

    doc = export_change_posture(source.document).document

    control = next(
        c for c in doc["results"]["controls"] if c["ref"] == reference("control", "private-control")
    )
    assert control["state"] == state.value and control["execution"] == "not-run"
    assert doc["results"]["summary"][state.value] >= 1
    assert doc["results"]["summary"]["required_satisfied"] < doc["results"]["summary"]["required"]
    assert doc["results"]["exit_code"] == 1


def test_projection_does_not_copy_private_identity_prose_paths_or_evidence(tmp_path):
    _, _, source = changed(tmp_path)
    sentinel = "private-person-prompt-token-url"
    proof = Evidence(sentinel, (sentinel,), sentinel, "tool-execution", "a" * 64, (sentinel,))
    extra = CheckResult(
        CheckSpec(sentinel, False, sentinel, sentinel, (sentinel,)),
        normalize(CheckOutcome(State.PASS, Execution.EXECUTED, sentinel, evidence=(proof,))),
    )
    source = replace(source, checks=replace(source.checks, results=(*source.checks.results, extra)))
    assert sentinel in source.to_json()

    report = export_change_posture(source.document)

    assert sentinel not in report.to_json() + render_change_posture(report)
    assert str(tmp_path) not in report.to_json()
    assert '"level"' not in report.to_json()
    assert "local_ref" in report.to_json()


def test_execution_error_preserves_canonical_unknown_even_with_error_finding(tmp_path):
    _, _, source = changed(tmp_path)
    extra = CheckResult(
        CheckSpec("unavailable", True, "reason", "policy", ("src",)),
        normalize(
            CheckOutcome(
                State.FAIL,
                Execution.ERROR,
                "failed to run",
                findings=(
                    Finding(
                        "unavailable", "error", "environment", "unable to run", "configure provider"
                    ),
                ),
            )
        ),
    )
    source = replace(source, checks=replace(source.checks, results=(*source.checks.results, extra)))
    assert parse_change_report(source.document).document == source.document

    doc = export_change_posture(source.document).document

    control = next(
        c for c in doc["results"]["controls"] if c["ref"] == reference("control", "unavailable")
    )
    assert control["state"] == "unknown" and control["execution"] == "error"
    assert control["findings"][0]["severity"] == "error"


def test_repository_identity_must_match_the_replayed_profile(tmp_path):
    _, _, source = changed(tmp_path)
    source = replace(
        source,
        checks=replace(
            source.checks, identity=replace(source.checks.identity, repository="another-repository")
        ),
    )
    assert parse_change_report(source.document).document == source.document

    with pytest.raises(ValueError, match="repository"):
        export_change_posture(source.document)


def test_export_replays_offline_without_reinspecting_or_executing(tmp_path, monkeypatch):
    _, _, source = changed(tmp_path)
    from cli import change_conformance

    def forbidden(*args, **kwargs):
        raise AssertionError("Export must not collect or execute")

    monkeypatch.setattr(change_conformance, "capture_observation", forbidden)
    monkeypatch.setattr(change_conformance, "plan_request", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)

    doc = export_change_posture(source.document).document

    assert doc["results"]["summary"] == source.checks.summary


def test_missing_planned_control_is_not_exported_as_complete_coverage(tmp_path):
    _, _, source = changed(tmp_path)
    source = replace(
        source,
        checks=replace(
            source.checks,
            results=tuple(c for c in source.checks.results if c.spec.id != "project:tests"),
        ),
    )
    assert parse_change_report(source.document).document == source.document

    with pytest.raises(ValueError, match="planned control"):
        export_change_posture(source.document)


@pytest.mark.parametrize(
    "tamper", ["digest", "summary", "state", "execution", "duplicate", "raw", "label"]
)
def test_replay_rejects_inconsistent_or_privacy_unsafe_exports(tmp_path, tamper):
    _, _, source = changed(tmp_path)
    doc = export_change_posture(source.document).document
    control = doc["results"]["controls"][0]
    if tamper == "digest":
        doc["digest"] = "0" * 64
    elif tamper == "summary":
        doc["results"]["summary"]["required_satisfied"] += 1
    elif tamper == "state":
        doc["results"]["exit_code"] = 1
    elif tamper == "execution":
        control["execution"] = "not-run"
    elif tamper == "duplicate":
        doc["results"]["controls"].append(deepcopy(control))
    elif tamper == "raw":
        control["summary"] = "private source prose"
    else:
        control["label"] = "llm-exact-match"
    if tamper != "digest":
        redigest(doc)

    with pytest.raises(ValueError):
        parse_change_posture(doc)


def test_bundled_change_example_validates_and_replays():
    doc = json.loads((paths.GOVERNANCE_DIR / "examples/posture/change.json").read_text())
    assert parse_change_posture(doc).document == doc


def test_accepted_transition_and_exception_descriptors_remain_visible_without_architecture_text(
    tmp_path,
):
    target, trusted, base = setup(tmp_path, transitions=[transition()])
    configure_transition(trusted)
    write(target, "src/service.py", "# good change\n")
    source = inspect(target, trusted, base)

    report = export_change_posture(source.document)

    architecture = report.document["architecture"]
    assert architecture["observed"] == []  # No discovery snapshot was supplied.
    assert architecture["accepted_contracts"][0]["scope_refs"] == [reference("scope", "src")]
    entry = architecture["transitions"][0]
    assert entry["mode"] == "improve" and entry["applies_to"] == "new-and-changed"
    assert entry["exceptions"][0]["expires_at"] == "2026-12-31"
    assert entry["exceptions"][0]["scope_refs"] == [reference("scope", "src/old.py")]
    human = render_change_posture(report)
    assert entry["ref"] in human and "2026-12-31" in human
    assert "architecture.md" not in report.to_json() + human


def test_shared_privacy_descriptor_schemas_stay_compatible():
    root = paths.GOVERNANCE_DIR / "schemas"
    maintenance = json.loads((root / "posture-export.schema.json").read_text())
    change = json.loads((root / "change-posture.schema.json").read_text())
    assert change["properties"]["architecture"] == maintenance["properties"]["architecture"]
    assert (
        change["properties"]["configured_controls"]
        == maintenance["properties"]["configured_controls"]
    )
    for name in ("capability", "version", "transition", "exception"):
        assert change["$defs"][name] == maintenance["$defs"][name]
