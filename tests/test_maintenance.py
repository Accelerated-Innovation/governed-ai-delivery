"""Canonical maintenance keeps independent evidence and actions separate."""

import json
import subprocess
from dataclasses import replace

import pytest

from cli.check_models import (
    CheckContext,
    CheckOutcome,
    CheckSpec,
    Evidence,
    Execution,
    Identity,
    State,
)
from cli.check_runner import CheckRegistry, run_checks
from cli.discovery import discover
from cli.maintenance import assess_repository, parse_assessment, verify_assessment
from cli.maintenance_operations import preview_operation
from cli.profiles import parse_profile
from tests.test_maintenance_inventory import installed
from tests.test_pack_store import snapshot
from tests.test_release_metadata import AS_OF, metadata, project, release


def dimensions(report):
    return {r["id"].removeprefix("maintenance:"): r for r in report.document["checks"]["results"]}


def actions(report):
    return {r["action"] for r in report.document["recommendations"]}


def test_assessment_keeps_simultaneous_dimensions_and_is_read_only(tmp_path):
    target, _ = installed(tmp_path)
    baseline = discover(target).document
    (target / "model.py").write_text("import openai\n")
    (target / ".agents/skills/sample-help/SKILL.md").write_text("User customization\n")
    before = snapshot(target)
    result = assess_repository(target, as_of=AS_OF, metadata=(metadata(),), baseline=baseline)
    assert set(dimensions(result)) == {"releases", "resources", "repository-fit", "ci"}
    assert {"upgrade-pack", "reconcile-customizations", "review-capability"} <= actions(result)
    assert dimensions(result)["resources"]["state"] != "pass"
    assert snapshot(target) == before
    for recommendation in result.document["recommendations"]:
        assert recommendation["evidence"]
        assert recommendation["prerequisites"]
        assert recommendation["preview"]["operation"]
        if recommendation["required"]:
            assert recommendation["source_policy"]
    assert parse_assessment(result.document).digest == result.digest


@pytest.mark.parametrize("status", ["failed", "unavailable", "cached"])
def test_unknown_release_evidence_does_not_hide_missing_resource(tmp_path, status):
    target, _ = installed(tmp_path)
    (target / ".agents/skills/sample-help/SKILL.md").unlink()
    report = assess_repository(
        target,
        as_of=AS_OF,
        metadata=(metadata(lookup_status=status, as_of="2026-09-20T00:00:00Z"),),
    )
    assert dimensions(report)["releases"]["state"] == "unknown"
    assert {"inspect-metadata", "refresh-resources"} <= actions(report)
    assert "upgrade-pack" not in actions(report)
    assert "upgrade-cli" not in actions(report)


def test_intentional_pin_and_incompatible_newer_release_do_not_require_upgrade(tmp_path):
    from cli.pack_loading import load_pack
    from cli.pack_store import apply_install, preview_install

    target, source = installed(tmp_path)
    profile_path = target / ".govkit/profile.yaml"
    profile_path.write_text(json.dumps(project(pin="1.0.0").document))
    apply_install(
        preview_install(profile_path, target, (load_pack(source),), govkit_version="0.21.1")
    )
    report = assess_repository(
        target,
        as_of=AS_OF,
        metadata=(metadata(release("1.0"), release("2.0", requires_govkit=">=9")),),
    )
    assert dimensions(report)["releases"]["state"] == "pass"
    assert not any(a.startswith("upgrade") for a in actions(report))
    assert report.document["inventory"]["candidates"][0]["excluded"]


def test_new_llm_usage_at_current_version_recommends_capability_review(tmp_path):
    target, _ = installed(tmp_path)
    baseline = discover(target).document
    (target / "model.py").write_text("import openai\n")
    result = assess_repository(
        target, as_of=AS_OF, metadata=(metadata(release("1.0")),), baseline=baseline
    )
    recommendation = next(
        r for r in result.document["recommendations"] if r["action"] == "review-capability"
    )
    assert recommendation["component"] == "llm-evaluation"
    assert recommendation["required"] is False
    assert recommendation["evidence"][0]["source"] == "model.py"
    assert "upgrade-cli" not in actions(result)
    assert result.document["identity"]["baseline_digest"]


def test_unchanged_reviewed_discovery_does_not_repeat_setup(tmp_path):
    target, _ = installed(tmp_path)
    (target / "policy.md").write_text("Accepted team policy\n")
    baseline = discover(target).document
    result = assess_repository(target, as_of=AS_OF, baseline=baseline)
    assert not any(r["dimension"] == "repository-fit" for r in result.document["recommendations"])


def ci_repository(tmp_path):
    target, _ = installed(tmp_path)
    policy = project().document
    policy["integrations"]["ci"] = "github"
    policy["policy"]["required_checks"] = [{"id": "ci:integration"}]
    policy["maintenance"]["assessment_max_age_hours"] = 24
    (target / ".govkit/profile.yaml").write_text(json.dumps(parse_profile(policy).document))
    for args in (
        ("init",),
        ("add", "."),
        (
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-m",
            "fixture",
        ),
    ):
        subprocess.run(["git", "-C", str(target), *args], check=True, capture_output=True)
    return target


def ci_evidence(target, *, state=State.PASS, mismatch=None, scopes=((".",),)):
    from cli.maintenance_inventory import inventory_repository

    inventory = inventory_repository(target, as_of=AS_OF).document
    fields = inventory["identity"]
    identity = Identity(
        inventory["repository"],
        revision=fields["revision"],
        dirty_digest=fields["dirty_digest"],
        profile_digest=fields["profile_digest"],
        resolution_digest=fields["resolution_digest"],
        pack_lock_digest=fields["pack_lock_digest"],
        observed_at=AS_OF,
    )
    if mismatch:
        identity = replace(identity, **mismatch)
    registry = CheckRegistry()
    evidence = Evidence(
        "ci-run:fixture",
        (".",),
        "provider-fixture",
        "tool-execution",
        "a" * 64,
        ("Synthetic provider input, not live enforcement",),
    )
    registry.register(
        "ci:integration",
        lambda _: CheckOutcome(
            state, Execution.EXECUTED, "Required integration measured", evidence=(evidence,)
        ),
    )
    # The adapter must derive requirements from accepted policy, not this flag.
    return run_checks(
        CheckContext(target, identity),
        tuple(CheckSpec("ci:integration", False, "fixture", "fixture", scope) for scope in scopes),
        registry,
    ).to_document()


@pytest.mark.parametrize("state", [State.PASS, State.FAIL])
def test_ci_merged_root_and_narrow_scopes_retain_measured_outcome(tmp_path, state):
    target = ci_repository(tmp_path)
    provider = ci_evidence(target, state=state, scopes=((".",), ("src",)))
    assert set(provider["results"][0]["scope"]) == {".", "src"}
    report = assess_repository(target, as_of=AS_OF, ci_report=provider)
    assert dimensions(report)["ci"]["state"] == state.value


def test_ci_narrow_scope_alone_cannot_prove_repository_health(tmp_path):
    target = ci_repository(tmp_path)
    report = assess_repository(
        target, as_of=AS_OF, ci_report=ci_evidence(target, scopes=(("src",),))
    )
    assert dimensions(report)["ci"]["state"] == "unknown"
    assert "repair-ci" in actions(report)


def redigest_assessment(document):
    from cli.schema_validation import canonical_json, content_digest

    inventory = document["inventory"]
    inventory["digest"] = content_digest(
        canonical_json({k: v for k, v in inventory.items() if k != "digest"}).encode()
    )
    document["identity"]["inventory_digest"] = inventory["digest"]
    document["digest"] = content_digest(
        canonical_json({k: v for k, v in document.items() if k != "digest"}).encode()
    )
    return document


@pytest.mark.parametrize("change", ["replace", "remove", "add"])
def test_saved_metadata_must_reproduce_the_assessed_release_facts(tmp_path, change):
    target, _ = installed(tmp_path)
    report = assess_repository(
        target, as_of=AS_OF, metadata=() if change == "add" else (metadata(),)
    )
    document = report.document
    document["inputs"]["metadata"] = [] if change == "remove" else [metadata(release("2.0"))]
    before = snapshot(target)
    with pytest.raises(ValueError, match="metadata|release"):
        verify_assessment(target, redigest_assessment(document), as_of=AS_OF)
    assert snapshot(target) == before


def test_expired_metadata_is_rejected_even_when_installed_policy_failure_is_unchanged(tmp_path):
    from cli.maintenance import validate_freshness

    target, _ = installed(tmp_path)
    policy = project().document
    policy["maintenance"]["constraints"][0].update(component="govkit", compatibility=">=9")
    (target / ".govkit/profile.yaml").write_text(json.dumps(policy))
    report = assess_repository(
        target, as_of=AS_OF, metadata=(metadata(release("0.22.0", component="govkit")),)
    )
    assert dimensions(report)["releases"]["state"] == "fail"
    with pytest.raises(ValueError, match="freshness"):
        validate_freshness(report.document, as_of="2026-09-26T00:00:00Z")


def test_explicit_new_metadata_is_allowed_and_omitted_sources_remain_unavailable(tmp_path):
    target, _ = installed(tmp_path)
    policy = project().document
    policy["maintenance"]["sources"].append(
        {"id": "other", "url": "https://example.invalid/other.json", "channels": ["stable"]}
    )
    (target / ".govkit/profile.yaml").write_text(json.dumps(policy))
    original = assess_repository(target, as_of=AS_OF, metadata=(metadata(),)).document

    updated = verify_assessment(
        target, original, as_of=AS_OF, metadata=(metadata(release("2.0")),)
    )["assessment"]

    assert updated["inventory"]["candidates"][0]["selected_target"] == "2.0"
    assert original["inventory"]["candidates"][0]["selected_target"] == "1.1.0"
    assert (
        next(m for m in updated["inventory"]["metadata"] if m["source_id"] == "other")[
            "lookup_status"
        ]
        == "unavailable"
    )


@pytest.mark.parametrize("state", [State.PASS, State.FAIL, State.UNKNOWN, State.SKIPPED])
def test_ci_reuses_canonical_results_and_cannot_waive_accepted_requirements(tmp_path, state):
    target = ci_repository(tmp_path)
    report = assess_repository(target, as_of=AS_OF, ci_report=ci_evidence(target, state=state))
    assert dimensions(report)["ci"]["required"]
    assert (
        dimensions(report)["ci"]["state"] == state.value
        if state in (State.PASS, State.FAIL)
        else dimensions(report)["ci"]["state"] == "unknown"
    )
    if state is not State.PASS:
        recommendation = next(
            r for r in report.document["recommendations"] if r["dimension"] == "ci"
        )
        assert recommendation["required"]
        assert recommendation["controls"] == ["ci:integration"]
        assert recommendation["source_policy"]


@pytest.mark.parametrize(
    "mismatch",
    [
        {"revision": "b" * 40},
        {"profile_digest": "b" * 64},
        {"observed_at": "2026-09-20T00:00:00Z"},
        {"observed_at": None},
        {"observed_at": "2026-09-25T00:00:00Z"},
    ],
)
def test_unbound_or_stale_ci_pass_is_unknown(tmp_path, mismatch):
    target = ci_repository(tmp_path)
    report = assess_repository(
        target, as_of=AS_OF, ci_report=ci_evidence(target, mismatch=mismatch)
    )
    assert dimensions(report)["ci"]["state"] == "unknown"
    assert "repair-ci" in actions(report)


def test_unavailable_ci_preserves_independent_release_recommendation(tmp_path):
    target = ci_repository(tmp_path)
    report = assess_repository(target, as_of=AS_OF, metadata=(metadata(),))
    assert dimensions(report)["ci"]["state"] == "unknown"
    assert {"upgrade-pack", "repair-ci"} <= actions(report)


def test_operation_preview_rechecks_identity_and_protects_customizations(tmp_path):
    from cli.pack_loading import load_pack

    target, source = installed(tmp_path)
    manifest = source / "manifest.yaml"
    manifest.write_text(manifest.read_text().replace("1.0.0", "1.1.0"))
    (target / ".agents/skills/sample-help/SKILL.md").write_text("Keep my instructions")
    report = assess_repository(target, as_of=AS_OF, metadata=(metadata(),))
    recommendation = next(
        r for r in report.document["recommendations"] if r["action"] == "upgrade-pack"
    )
    before = snapshot(target)
    preview = preview_operation(
        target, report.document, recommendation["id"], catalog=(load_pack(source),), as_of=AS_OF
    )
    assert not preview["ready"]
    assert preview["protected_customizations"]
    assert preview["target_version"] == "1.1.0"
    assert snapshot(target) == before


def test_non_git_application_change_invalidates_assessed_proposal(tmp_path):
    target, _ = installed(tmp_path)
    report = assess_repository(target, as_of=AS_OF, metadata=(metadata(),))
    selected = next(r for r in report.document["recommendations"] if r["action"] == "upgrade-pack")
    (target / "model.py").write_text("import openai\n")
    with pytest.raises(ValueError, match="[Ss]tale"):
        preview_operation(target, report.document, selected["id"], as_of=AS_OF)


def test_expired_metadata_cannot_preview_a_previously_selected_upgrade(tmp_path):
    target, _ = installed(tmp_path)
    report = assess_repository(target, as_of=AS_OF, metadata=(metadata(),))
    selected = next(r for r in report.document["recommendations"] if r["action"] == "upgrade-pack")
    with pytest.raises(ValueError, match="[Ss]tale|fresh"):
        preview_operation(target, report.document, selected["id"], as_of="2026-10-01T00:00:00Z")


def test_marker_change_does_not_resolve_a_missing_resource(tmp_path):
    target, _ = installed(tmp_path)
    (target / ".agents/skills/sample-help/SKILL.md").unlink()
    before = assess_repository(target, as_of=AS_OF)
    (target / ".govkit/marker.json").write_text(json.dumps({"version": "0.22.0"}))
    result = verify_assessment(target, before.document, as_of=AS_OF)
    resource = next(
        r for r in before.document["recommendations"] if r["action"] == "refresh-resources"
    )
    assert resource["id"] in result["remaining"]
    assert resource["id"] not in result["resolved"]


def test_actual_resource_repair_is_verified_without_writes(tmp_path):
    target, _ = installed(tmp_path)
    skill = target / ".agents/skills/sample-help/SKILL.md"
    original = skill.read_bytes()
    skill.unlink()
    before = assess_repository(target, as_of=AS_OF)
    skill.write_bytes(original)
    snapshot_before = snapshot(target)
    result = verify_assessment(target, before.document, as_of=AS_OF)
    resource = next(
        r for r in before.document["recommendations"] if r["action"] == "refresh-resources"
    )
    assert resource["id"] in result["resolved"]
    assert snapshot(target) == snapshot_before


def test_tampered_assessment_is_rejected(tmp_path):
    target, _ = installed(tmp_path)
    document = assess_repository(target, as_of=AS_OF).document
    document["recommendations"] = []
    with pytest.raises(ValueError, match="digest"):
        parse_assessment(document)


def test_missing_profile_keeps_partial_assessment_with_supplied_metadata(tmp_path):
    target, _ = installed(tmp_path)
    (target / ".govkit/profile.yaml").unlink()
    report = assess_repository(target, as_of=AS_OF, metadata=(metadata(),))
    assert dimensions(report)["releases"]["state"] == "unknown"
    assert dimensions(report)["resources"]["state"] != "pass"
    assert report.document["inventory"]["recorded_install"] == "0.21.1"


def test_recomputed_hash_does_not_validate_forged_recommendations(tmp_path):
    from cli.schema_validation import canonical_json, content_digest

    target, _ = installed(tmp_path)
    document = assess_repository(target, as_of=AS_OF).document
    document["recommendations"] = []
    document["digest"] = content_digest(
        canonical_json({k: v for k, v in document.items() if k != "digest"}).encode()
    )
    with pytest.raises(ValueError, match="recommendations|derived"):
        parse_assessment(document)


def test_unverified_lock_claim_does_not_invent_a_policy_required_file(tmp_path):
    target, _ = installed(tmp_path)
    lock_path = target / ".govkit/pack-lock.json"
    lock = json.loads(lock_path.read_text())
    lock["files"]["not-selected.md"] = "a" * 64
    lock["owners"]["not-selected.md"] = "sample"
    lock_path.write_text(json.dumps(lock))
    report = assess_repository(target, as_of=AS_OF)
    item = next(
        r for r in report.document["recommendations"] if r["resources"] == ["not-selected.md"]
    )
    assert not item["required"]
    assert item["severity"] != "error"
    assert dimensions(report)["resources"]["state"] != "pass"


@pytest.mark.parametrize("agent", ["codex", "claude-code", "copilot"])
def test_runtime_consolidated_maintenance_pilot(tmp_path, agent):
    from tests.wheel_maintenance_assessment_smoke import run_pilot

    run_pilot(tmp_path, agent)
    assert (tmp_path / "consumer/USER.md").read_text() == "Preserve user instructions\n"


def test_assessment_reader_rejects_oversized_input_before_parsing(tmp_path, monkeypatch):
    from cli import maintenance

    monkeypatch.setattr(maintenance, "MAX_ASSESSMENT_BYTES", 512, raising=False)
    record = tmp_path / "too-large.json"
    record.write_bytes(b"x" * 513)
    with pytest.raises(ValueError, match="size limit"):
        maintenance.read_assessment(record)


def test_generated_assessment_cannot_exceed_its_replay_size_limit(tmp_path, monkeypatch):
    from cli import maintenance

    target, _ = installed(tmp_path)
    monkeypatch.setattr(maintenance, "MAX_ASSESSMENT_BYTES", 512, raising=False)
    with pytest.raises(ValueError, match="size limit"):
        assess_repository(target, as_of=AS_OF)


def test_unverified_pack_version_is_not_promoted_to_required_policy_failure(tmp_path):
    target, _ = installed(tmp_path)
    lock_path = target / ".govkit/pack-lock.json"
    lock = json.loads(lock_path.read_text())
    lock["packs"][0]["version"] = "9.0"
    lock_path.write_text(json.dumps(lock))
    report = assess_repository(target, as_of=AS_OF, metadata=(metadata(),))
    items = [r for r in report.document["recommendations"] if r["dimension"] == "releases"]
    assert items and all(not r["required"] for r in items)
    assert dimensions(report)["releases"]["state"] == "unknown"


def test_dimension_report_describes_the_maintenance_coverage_it_actually_performed(tmp_path):
    target, _ = installed(tmp_path)
    report = assess_repository(target, as_of=AS_OF)
    checks = report.document["checks"]
    assert checks["kind"] == "maintenance-dimensions"
    assert all(
        "maintenance assessment are not performed" not in limit for limit in checks["limitations"]
    )


def test_new_ci_evidence_can_verify_an_integration_repair(tmp_path):
    target = ci_repository(tmp_path)
    before = assess_repository(target, as_of=AS_OF, ci_report=ci_evidence(target, state=State.FAIL))
    repaired = ci_evidence(target, state=State.PASS)
    result = verify_assessment(target, before.document, as_of=AS_OF, ci_report=repaired)
    original = next(r for r in before.document["recommendations"] if r["dimension"] == "ci")
    assert original["id"] in result["resolved"]
    assert next(
        r for r in result["assessment"]["checks"]["results"] if r["id"] == "maintenance:ci"
    )["required"]
