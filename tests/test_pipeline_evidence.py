"""Offline CI facts retain identity, provenance and independent maintenance states."""

import json
import shutil

import pytest

from cli.maintenance import assess_repository, verify_assessment
from cli.pack_loading import bundled_catalog
from cli.pack_store import apply_install, preview_install
from cli.pipeline_evidence import collect_evidence
from cli.pipeline_runtime import run_bound
from cli.pipeline_store import apply_pipeline, preview_pipeline
from cli.schema_validation import content_digest
from cli.version import GOVKIT_VERSION
from tests.test_change_conformance import git
from tests.test_maintenance import dimensions
from tests.test_pack_store import snapshot
from tests.test_pipeline_render import settings
from tests.test_pipeline_runtime import fixture
from tests.test_provider_admission import event, policy

AS_OF = "2026-09-24T12:00:00Z"


def configured(tmp_path, provider="github", *, observation_limit=None, omit_conformance=False):
    target, trusted, _, req, _ = fixture(tmp_path, provider)
    source = trusted / ".govkit/profile.yaml"
    document = json.loads(source.read_text())
    document["maintenance"] = {"assessment_max_age_hours": 24}
    if omit_conformance:
        del document["policy"]["conformance"]
    source.write_text(json.dumps(document))
    apply_install(
        preview_install(source, trusted, bundled_catalog(), govkit_version=GOVKIT_VERSION)
    )
    if observation_limit is not None:
        path = trusted / "conformance.json"
        conformance = json.loads(path.read_text())
        conformance["observation_limits"] = {"max_file_bytes": observation_limit}
        path.write_text(json.dumps(conformance))
        for root in (target, trusted):
            (root / "src").mkdir(exist_ok=True)
            (root / "src/asset.bin").write_bytes(b"\0" * (1024 * 1024 + 1))
    shutil.copytree(trusted / ".govkit", target / ".govkit")
    shutil.copyfile(trusted / "conformance.json", target / "conformance.json")
    config = tmp_path / "settings.json"
    config.write_text(
        json.dumps(
            settings(
                execute_checks=[] if omit_conformance else ["project:tests"],
                admission=policy(provider),
            )
        )
    )
    proposed = preview_pipeline(source, target, config, bundled_catalog())
    apply_pipeline(proposed, proposed.digest)
    for root in (target, trusted):
        if not (root / ".git").exists():
            git(root, "init")
        git(root, "add", ".")
        git(
            root,
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-m",
            "configured",
        )
    base = git(target, "rev-parse", "HEAD")
    (target / "src/service.py").write_text("# good changed again\n")
    git(target, "add", ".")
    git(target, "commit", "-m", "change")
    revision = git(target, "rev-parse", "HEAD")
    report = run_bound(
        proposed.artifact.document["binding"],
        target,
        trusted,
        req,
        base,
        observed_at=AS_OF,
        provider_event=event(provider, revision, base),
        policy_revision=git(trusted, "rev-parse", "HEAD"),
        request_digest=content_digest(req.read_bytes()),
    )
    assert report.exit_code == (1 if omit_conformance else 0)
    observation = {
        "schema_version": 1,
        "kind": "provider-observation",
        "provider": provider,
        "repository": "team/project",
        "target_ref": "refs/heads/main",
        "revision": revision,
        "base": base,
        "observed_at": AS_OF,
        "artifact_digest": proposed.artifact.document["digest"],
        "report_digest": content_digest(report.to_json().encode()),
        "runtime_version": GOVKIT_VERSION,
        "run_id": "fixture-7",
        "run_url": "https://example.invalid/run/7",
        "enabled": True,
        "required_check": True,
        "all_changes": True,
        "trusted_policy": True,
        "approvals": True,
    }
    return target, config, report.document, observation


def collect(target, config, report=None, observation=None):
    return collect_evidence(
        target,
        config,
        bundled_catalog(),
        as_of=AS_OF,
        change_report=report,
        observation=observation,
    )


def states(report):
    return {r.spec.id: r.outcome.state.value for r in report.results}


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_provider_facts_feed_the_same_read_only_maintenance_assessment(tmp_path, provider):
    target, config, runtime, observation = configured(tmp_path, provider)
    report = collect(target, config, runtime, observation)
    before = snapshot(target)
    assessment = assess_repository(target, as_of=AS_OF, ci_report=report.to_document())
    assert dimensions(assessment)["ci"]["state"] == "unknown"
    assert snapshot(target) == before
    assert any(
        "authenticate" in limit
        for r in report.results
        for e in r.outcome.evidence
        for limit in e.limitations
    )


def test_configuration_presence_does_not_claim_runtime_or_enforcement(tmp_path):
    target, config, _, _ = configured(tmp_path)
    report = collect(target, config)
    assert states(report) == {
        "ci:configuration": "pass",
        "ci:runtime": "unknown",
        "ci:enforcement": "unknown",
        "ci:integration": "unknown",
    }


@pytest.mark.parametrize(
    "field,value,expected",
    [
        ("enabled", False, "fail"),
        ("required_check", False, "fail"),
        ("all_changes", False, "fail"),
        ("approvals", None, "unknown"),
        ("trusted_policy", False, "fail"),
        ("observed_at", "2026-09-20T00:00:00Z", "unknown"),
        ("revision", "b" * 40, "unknown"),
        ("artifact_digest", "b" * 64, "unknown"),
        ("report_digest", "b" * 64, "unknown"),
        ("runtime_version", "0.1.0", "fail"),
    ],
)
def test_inactive_stale_unbound_or_unconfigured_evidence_cannot_pass(
    tmp_path, field, value, expected
):
    target, config, runtime, observation = configured(tmp_path)
    observation[field] = value
    report = collect(target, config, runtime, observation)
    assert states(report)["ci:integration"] == expected


@pytest.mark.parametrize("change", ["missing", "edited", "malformed-lock"])
def test_pipeline_drift_is_an_actionable_configuration_failure(tmp_path, change):
    target, config, _, _ = configured(tmp_path)
    path = target / (
        ".govkit/pipeline-lock.json"
        if change == "malformed-lock"
        else ".github/actions/govkit-conformance/action.yml"
    )
    if change == "missing":
        path.unlink()
    else:
        path.write_text("# custom content\n")
    report = collect(target, config)
    assert states(report)["ci:configuration"] == "fail"
    assert states(report)["ci:integration"] == "fail"


def test_saved_evidence_is_invalidated_by_ignored_pipeline_edit(tmp_path):
    target, config, _, _ = configured(tmp_path)
    # Remove the generated files from the index and ignore them before collecting again.
    git(target, "rm", "--cached", ".github/actions/govkit-conformance/action.yml")
    (target / ".gitignore").write_text(".github/actions/govkit-conformance/action.yml\n")
    git(target, "add", ".")
    git(target, "commit", "-m", "ignore generated action")
    # A fresh configuration-only report still must bind the ignored file's content.
    evidence = collect(target, config).to_document()
    original = assess_repository(target, as_of=AS_OF, ci_report=evidence)
    (target / ".github/actions/govkit-conformance/action.yml").write_text("# drift\n")
    result = verify_assessment(target, original.document, as_of=AS_OF)
    ci = next(r for r in result["assessment"]["recommendations"] if r["dimension"] == "ci")
    assert any("inputs" in s for s in ci["uncertainty"])


def test_recollection_preserves_oldest_runtime_time_instead_of_renewing_evidence(tmp_path):
    target, config, runtime, observation = configured(tmp_path)
    oldest = "2026-09-23T13:00:00Z"
    runtime["checks"]["identity"]["observed_at"] = oldest
    from cli.schema_validation import canonical_json

    observation["report_digest"] = content_digest(canonical_json(runtime).encode())
    report = collect(target, config, runtime, observation)
    assert states(report)["ci:integration"] == "unknown"
    assert report.identity.observed_at == oldest


def test_passing_provider_export_with_wrong_runtime_profile_remains_unknown(tmp_path):
    target, config, runtime, observation = configured(tmp_path)
    # Change actual accepted policy after the run; a provider's success cannot approve it.
    path = target / ".govkit/profile.yaml"
    profile = json.loads(path.read_text())
    profile["policy"]["required_checks"].append({"id": "security:review"})
    path.write_text(json.dumps(profile))
    report = collect(target, config, runtime, observation)
    assert states(report)["ci:runtime"] == "unknown"
    assert states(report)["ci:integration"] != "pass"
