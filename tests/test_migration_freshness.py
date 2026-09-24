"""Migration rechecks the clock without changing accepted operation digests."""

import json
import subprocess

import pytest

from cli import migration
from cli.check_models import CheckContext, CheckOutcome, CheckSpec, Execution, State
from cli.check_runner import CheckRegistry, parse_report, run_checks
from cli.maintenance import assess_repository
from tests.test_maintenance import ci_evidence, dimensions
from tests.test_migration import accepted, legacy
from tests.test_pack_store import snapshot
from tests.test_release_metadata import AS_OF, metadata, project, release

LATER = "2026-09-26T00:00:00Z"
WITHIN = "2026-09-24T13:00:00Z"


def measured_migration(tmp_path, *, release_age=24, ci_age=24):
    target = legacy(tmp_path)
    source = accepted(tmp_path, target)
    profile = json.loads(source.read_text())
    profile["maintenance"] = project().document["maintenance"]
    profile["maintenance"]["constraints"][0].update(component="govkit", compatibility=">=0.21,<1")
    profile["maintenance"].update(
        metadata_max_age_hours=release_age, assessment_max_age_hours=ci_age
    )
    source.write_text(json.dumps(profile))
    migration.apply_migration(migration.preview_migration(target, profile_path=source))
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
    provider = parse_report(ci_evidence(target))
    outcome = CheckOutcome(
        State.PASS,
        Execution.EXECUTED,
        "Measured synthetic CI",
        evidence=provider.results[0].outcome.evidence,
    )
    registry = CheckRegistry()
    checks = ("ci:integration", "migration:ci-enforcement")
    for identifier in checks:
        registry.register(identifier, lambda _: outcome)
    report = run_checks(
        CheckContext(target, provider.identity),
        tuple(CheckSpec(identifier, True, "fixture", "fixture", (".",)) for identifier in checks),
        registry,
    )
    assessment = assess_repository(
        target,
        as_of=AS_OF,
        metadata=(metadata(release("0.22.0", component="govkit")),),
        ci_report=report.to_document(),
    )
    assert dimensions(assessment)["ci"]["state"] == "pass"
    assert any(r["action"] == "upgrade-cli" for r in assessment.document["recommendations"])
    return target, source, assessment.document


@pytest.mark.parametrize("release_age,ci_age", [(24, 48), (48, 24)])
def test_migration_preview_rejects_expired_release_or_ci_evidence(
    tmp_path, monkeypatch, release_age, ci_age
):
    target, source, assessment = measured_migration(
        tmp_path, release_age=release_age, ci_age=ci_age
    )
    monkeypatch.setattr(migration, "_now", lambda: LATER, raising=False)
    before = snapshot(target)
    with pytest.raises(ValueError, match="[Ff]resh|[Ee]xpir|[Ss]tale"):
        migration.preview_migration(target, profile_path=source, assessment=assessment)
    assert snapshot(target) == before


def test_migration_apply_rejects_evidence_that_expired_after_preview(tmp_path, monkeypatch):
    target, source, assessment = measured_migration(tmp_path)
    monkeypatch.setattr(migration, "_now", lambda: AS_OF, raising=False)
    preview = migration.preview_migration(target, profile_path=source, assessment=assessment)
    monkeypatch.setattr(migration, "_now", lambda: LATER)
    before = snapshot(target)
    with pytest.raises(ValueError, match="[Ss]tale"):
        migration.apply_migration(preview)
    assert snapshot(target) == before


def test_fresh_migration_digest_is_stable_and_post_verification_uses_current_time(
    tmp_path, monkeypatch
):
    target, source, assessment = measured_migration(tmp_path)
    monkeypatch.setattr(migration, "_now", lambda: AS_OF, raising=False)
    preview = migration.preview_migration(target, profile_path=source, assessment=assessment)
    monkeypatch.setattr(migration, "_now", lambda: WITHIN)
    assert (
        migration.preview_migration(target, profile_path=source, assessment=assessment).digest
        == preview.digest
    )
    before = snapshot(target)
    result = migration.apply_migration(preview)
    assert result["maintenance"]["assessment"]["as_of"] == WITHIN
    assert (
        next(
            r
            for r in result["maintenance"]["assessment"]["checks"]["results"]
            if r["id"] == "maintenance:ci"
        )["state"]
        == "pass"
    )
    assert snapshot(target) == before


def test_post_operation_recheck_does_not_keep_evidence_that_expired_during_operation(
    tmp_path, monkeypatch
):
    target, source, assessment = measured_migration(tmp_path)
    monkeypatch.setattr(migration, "_now", lambda: AS_OF, raising=False)
    preview = migration.preview_migration(target, profile_path=source, assessment=assessment)
    clock = iter((WITHIN, LATER))
    monkeypatch.setattr(migration, "_now", lambda: next(clock))
    result = migration.apply_migration(preview)["maintenance"]["assessment"]
    assert result["as_of"] == LATER
    assert (
        next(r for r in result["checks"]["results"] if r["id"] == "maintenance:ci")["state"]
        == "unknown"
    )
    assert result["inventory"]["candidates"][0]["freshness"] == "stale"
    assert not any(r["action"] == "upgrade-cli" for r in result["recommendations"])
