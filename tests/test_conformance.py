"""Real legacy and pack adapters, required evidence, and read-only reporting."""

import json

import pytest
import yaml

from cli.check_models import State
from cli.conformance import inspect_repository
from cli.pack_loading import bundled_catalog
from cli.pack_store import apply_install, preview_install
from tests.test_capability_packs import profile
from tests.test_pack_store import snapshot, write_profile


def marker(target, *, level="4"):
    (target / ".govkit").mkdir(exist_ok=True)
    (target / ".govkit/marker.json").write_text(
        json.dumps(
            {
                "version": "0.21.1",
                "level": level,
                "agent": "codex",
                "options": {"type": "api", "ci": "github"},
            }
        )
    )


def result(report, identifier):
    return next(r for r in report.results if r.spec.id == identifier)


def test_broken_feature_extension_and_policy_report_independent_findings(tmp_path, capsys):
    marker(tmp_path)
    (tmp_path / "features/broken").mkdir(parents=True)
    extension = tmp_path / "extensions/broken"
    extension.mkdir(parents=True)
    (extension / "manifest.yaml").write_text("id: broken\n")
    policy = tmp_path / "governance/approval_policy.yaml"
    policy.parent.mkdir(parents=True)
    policy.write_text("invalid: [\n")
    before = snapshot(tmp_path)
    report = inspect_repository(tmp_path)
    assert result(report, "legacy:features").outcome.state is State.FAIL
    assert result(report, "legacy:extensions").outcome.state is State.FAIL
    assert result(report, "legacy:approval-policy").outcome.state is State.FAIL
    assert report.exit_code == 1
    assert snapshot(tmp_path) == before
    assert capsys.readouterr().out == ""


def test_absent_or_unreadable_required_evidence_never_passes(tmp_path):
    write_profile(tmp_path, profile([], checks=["security"]))
    report = inspect_repository(tmp_path)
    assert result(report, "security").outcome.state is State.UNKNOWN
    assert report.exit_code == 1
    (tmp_path / ".govkit/profile.yaml").write_bytes(b"\xff")
    report = inspect_repository(tmp_path)
    assert result(report, "govkit:profile").outcome.state is State.UNKNOWN
    assert report.exit_code == 1


def test_legacy_doctor_has_failing_findings_without_claiming_silent_checks_passed(tmp_path):
    marker(tmp_path)
    (tmp_path / ".agents/skills/broken").mkdir(parents=True)
    (tmp_path / ".agents/skills/broken/SKILL.md").write_text("{{govkit_type}}")
    report = inspect_repository(tmp_path)
    doctor = result(report, "legacy:doctor")
    assert doctor.outcome.state is not State.PASS
    assert any(f.code == "D015" for f in doctor.outcome.findings)
    assert all(e.limitations for e in doctor.outcome.evidence)


def test_pack_controls_need_explicit_execution_and_remain_independent_of_skills(tmp_path):
    import shutil

    path = write_profile(tmp_path, profile(["llm-evaluation"], checks=["llm-exact-match"]))
    apply_install(preview_install(path, tmp_path, bundled_catalog(), govkit_version="0.21.1"))
    results = tmp_path / "results.json"
    results.write_text('{"cases":[{"id":"hello","expected":"hello","actual":"hello"}]}')
    before = snapshot(tmp_path)
    skipped = inspect_repository(tmp_path)
    assert result(skipped, "llm-exact-match").outcome.state is State.SKIPPED
    assert skipped.exit_code == 1
    assert snapshot(tmp_path) == before
    report = inspect_repository(
        tmp_path,
        execute_pack_checks=("llm-exact-match",),
        pack_arguments={"llm-exact-match": ("--results", "results.json")},
    )
    assert result(report, "llm-exact-match").outcome.state is State.PASS
    assert report.exit_code == 0
    assert snapshot(tmp_path) == before
    shutil.rmtree(tmp_path / ".agents/skills")
    report = inspect_repository(
        tmp_path,
        execute_pack_checks=("llm-exact-match",),
        pack_arguments={"llm-exact-match": ("--results", "results.json")},
    )
    assert result(report, "llm-exact-match").outcome.state is State.PASS
    assert result(report, "govkit:pack-lock").outcome.state is State.FAIL
    assert report.exit_code == 1
    results.write_text('{"cases":[{"id":"hello","expected":"hello","actual":"wrong"}]}')
    report = inspect_repository(
        tmp_path,
        execute_pack_checks=("llm-exact-match",),
        pack_arguments={"llm-exact-match": ("--results", "results.json")},
    )
    assert result(report, "llm-exact-match").outcome.state is State.FAIL
    assert report.exit_code == 1


def test_missing_pack_lock_cannot_hide_required_pack_controls(tmp_path):
    write_profile(tmp_path, profile(["llm-evaluation"], checks=["llm-exact-match"]))
    report = inspect_repository(tmp_path)
    assert result(report, "govkit:pack-lock").outcome.state is State.UNKNOWN
    assert result(report, "llm-exact-match").outcome.state is State.UNKNOWN
    assert report.exit_code == 1


def test_identical_explicit_inputs_have_identical_local_and_ci_reports(tmp_path, monkeypatch):
    write_profile(tmp_path, profile([]))
    local = inspect_repository(tmp_path).to_json()
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert inspect_repository(tmp_path).to_json() == local


def test_inspection_never_migrates_a_legacy_marker_or_calls_an_external_tool(
    tmp_path, monkeypatch, capsys
):
    import socket
    import subprocess

    (tmp_path / ".govkit").write_text(
        json.dumps({"version": "0.6.0", "level": "4", "agent": "codex", "options": {"type": "api"}})
    )
    feature = tmp_path / "features/example"
    feature.mkdir(parents=True)
    (feature / "eval_criteria.yaml").write_text("version: 1\nmode: standard\n")

    def forbidden(*args, **kwargs):
        raise AssertionError("Inspection invoked an external boundary")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    before = snapshot(tmp_path)
    report = inspect_repository(tmp_path)
    assert result(report, "legacy:features").outcome.state is State.FAIL
    assert snapshot(tmp_path) == before
    assert (tmp_path / ".govkit").is_file()
    assert not (tmp_path / ".govkit.legacy.bak").exists()
    assert capsys.readouterr().err == ""


def test_readable_extension_and_policy_prove_their_narrow_structural_contract(tmp_path):
    import shutil

    from cli import paths

    write_profile(tmp_path, profile([]))
    root = tmp_path / "extensions/example"
    root.mkdir(parents=True)
    (root / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "example",
                "name": "Example",
                "version": "1.0.0",
                "extension_type": "skills",
                "contract_sets": [],
            }
        )
    )
    policy = tmp_path / "governance/approval_policy.yaml"
    policy.parent.mkdir()
    policy.write_text("version: 1\napprovers:\n  - login: example-user\n    role: approver\n")
    (policy.parent / "schemas").mkdir()
    shutil.copyfile(
        paths.GOVERNANCE_DIR / "schemas/approval_policy.schema.json",
        policy.parent / "schemas/approval_policy.schema.json",
    )
    report = inspect_repository(tmp_path)
    assert result(report, "legacy:extensions").outcome.state is State.PASS
    assert result(report, "legacy:approval-policy").outcome.state is State.PASS
    assert (
        "authenticate"
        in result(report, "legacy:approval-policy").outcome.evidence[0].limitations[0]
    )


def test_nonlocal_schema_references_stay_unknown_without_network(tmp_path, monkeypatch):
    import socket

    write_profile(tmp_path, profile([], checks=["legacy:approval-policy"]))
    policy = tmp_path / "governance/approval_policy.yaml"
    schema = tmp_path / "governance/schemas/approval_policy.schema.json"
    schema.parent.mkdir(parents=True)
    schema.write_text('{"$ref":"https://example.invalid/schema.json"}')
    policy.write_text("version: 1\napprovers:\n  - login: example-user\n    role: approver\n")
    monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("Network lookup"))
    report = inspect_repository(tmp_path)
    assert result(report, "legacy:approval-policy").outcome.state is State.UNKNOWN
    assert report.exit_code == 1


def test_required_pack_control_keeps_accepted_policy_provenance(tmp_path):
    path = write_profile(tmp_path, profile(["llm-evaluation"], checks=["llm-exact-match"]))
    apply_install(preview_install(path, tmp_path, bundled_catalog(), govkit_version="0.21.1"))
    report = inspect_repository(tmp_path, execute_pack_checks=("llm-exact-match",))
    control = result(report, "llm-exact-match")
    assert control.spec.source_policy == "policy.md"
    assert "accepted" in control.spec.reason
    assert control.spec.required


def test_unreadable_adr_inventory_cannot_be_reported_as_verified_policy(tmp_path, monkeypatch):
    import shutil
    from pathlib import Path

    from cli import paths

    write_profile(tmp_path, profile([], checks=["legacy:approval-policy"]))
    policy = tmp_path / "governance/approval_policy.yaml"
    policy.parent.mkdir()
    policy.write_text("version: 1\napprovers:\n  - login: example-user\n    role: approver\n")
    (policy.parent / "schemas").mkdir()
    shutil.copyfile(
        paths.GOVERNANCE_DIR / "schemas/approval_policy.schema.json",
        policy.parent / "schemas/approval_policy.schema.json",
    )
    adr = tmp_path / "docs/backend/architecture/ADR"
    adr.mkdir(parents=True)
    (adr / "0001.md").write_text("## Status\nProposed\n")
    original = Path.iterdir

    def unreadable(path):
        if path == adr:
            raise PermissionError("Unreadable ADR inventory")
        return original(path)

    monkeypatch.setattr(Path, "iterdir", unreadable)
    report = inspect_repository(tmp_path)
    assert result(report, "legacy:approval-policy").outcome.state is State.UNKNOWN
    assert result(report, "govkit:profile").outcome.state is State.PASS
    assert report.exit_code == 1


def test_real_feature_artifact_checks_preserve_prediction_provenance(tmp_path):
    from tests.test_validate import make_full_feature

    marker(tmp_path)
    feature = tmp_path / "features/example"
    make_full_feature(feature)
    report = inspect_repository(tmp_path)
    findings = result(report, "legacy:features").outcome.findings
    assert any(f.severity == "info" and "valid Gherkin structure" in f.message for f in findings)
    prediction = next(f for f in findings if "prediction structure" in f.message)
    assert prediction.severity == "warning"
    assert prediction.evidence[0].origin == "agent-assertion"
    (feature / "acceptance.feature").write_text("Invalid Gherkin")
    report = inspect_repository(tmp_path)
    assert any(
        f.severity == "error" and "acceptance.feature" in f.message
        for f in result(report, "legacy:features").outcome.findings
    )


def test_required_approval_policy_path_must_be_a_file(tmp_path):
    write_profile(tmp_path, profile([], checks=["legacy:approval-policy"]))
    (tmp_path / "governance/approval_policy.yaml").mkdir(parents=True)
    report = inspect_repository(tmp_path)
    assert result(report, "legacy:approval-policy").outcome.state is State.UNKNOWN
    assert report.exit_code == 1


def test_legacy_internal_errors_do_not_export_exception_payloads(tmp_path, monkeypatch):
    from pathlib import Path

    marker(tmp_path)
    skills = tmp_path / ".agents/skills/example"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text("# Example")
    original = Path.rglob

    def unavailable(path, pattern):
        if path == skills.parent and pattern == "*.md":
            raise OSError("sensitive-exception-payload")
        return original(path, pattern)

    monkeypatch.setattr(Path, "rglob", unavailable)
    report = inspect_repository(tmp_path)
    finding = next(f for f in result(report, "legacy:doctor").outcome.findings if f.code == "D015")
    assert finding.category == "internal"
    assert "sensitive-exception-payload" not in report.to_json()
    assert result(report, "legacy:doctor").outcome.state is not State.PASS
