"""PR 194 review regressions exercise production boundaries with explicit local inputs."""

import json
import sys

import pytest

from cli.govkit import main
from cli.maintenance import assess_repository
from cli.pack_loading import load_pack
from cli.pipeline_assessment import upgrade_integration_preview
from cli.pipeline_runtime import run_bound
from cli.provider_admission import parse_event
from cli.schema_validation import content_digest
from tests.test_capability_packs import make_pack
from tests.test_change_conformance import git
from tests.test_maintenance import dimensions
from tests.test_pack_store import snapshot
from tests.test_pipeline_assessment import candidate
from tests.test_pipeline_evidence import AS_OF, collect, configured, states
from tests.test_pipeline_render import settings
from tests.test_provider_admission import event, policy, prepared
from tests.test_release_metadata import metadata, project, release


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_matching_but_unauthenticated_exports_cannot_pass_required_evidence(tmp_path, provider):
    target, config, runtime, observation = configured(tmp_path, provider)
    before = snapshot(target)

    report = collect(target, config, runtime, observation)

    assert states(report) == {
        "ci:configuration": "pass",
        "ci:runtime": "unknown",
        "ci:enforcement": "unknown",
        "ci:integration": "unknown",
    }
    assert report.exit_code == 1
    assert snapshot(target) == before
    for result in report.results:
        if result.spec.id in {"ci:runtime", "ci:enforcement"}:
            assert {e.origin for e in result.outcome.evidence} == {"unverified-artifact"}


def test_maintenance_preserves_unknown_provider_authenticity(tmp_path):
    target, config, runtime, observation = configured(tmp_path)
    evidence = collect(target, config, runtime, observation).to_document()

    assessment = assess_repository(target, as_of=AS_OF, ci_report=evidence)

    assert dimensions(assessment)["ci"]["state"] == "unknown"
    assert dimensions(assessment)["ci"]["required"]
    assert any(r["action"] == "repair-ci" for r in assessment.document["recommendations"])


@pytest.mark.parametrize("provider", ["github", "azure"])
@pytest.mark.parametrize("failed", ["required_check", "approvals"])
@pytest.mark.parametrize("mismatch", ["report_digest", "base"])
def test_runtime_mismatch_does_not_erase_explicit_enforcement_failure(
    tmp_path, provider, failed, mismatch
):
    target, config, runtime, observation = configured(tmp_path, provider)
    observation[failed] = False
    observation[mismatch] = "b" * (64 if mismatch == "report_digest" else 40)

    report = collect(target, config, runtime, observation)

    assert states(report)["ci:runtime"] == "unknown"
    assert states(report)["ci:enforcement"] == "fail"
    assert states(report)["ci:integration"] == "fail"
    result = next(r for r in report.results if r.spec.id == "ci:enforcement")
    assert failed + "=False" in result.outcome.summary


@pytest.mark.parametrize(
    "action,option",
    [
        ("evidence", "--assessment"),
        ("evidence", "--recommendation"),
        ("evidence", "--metadata"),
        ("evidence", "--release-source"),
        ("assess", "--assessment"),
        ("assess", "--recommendation"),
        ("upgrade-preview", "--change-report"),
        ("upgrade-preview", "--observation"),
        ("upgrade-preview", "--metadata"),
        ("upgrade-preview", "--release-source"),
    ],
)
@pytest.mark.parametrize("value", ["unused-input", ""])
def test_cli_rejects_unused_inputs_before_publishing(
    tmp_path, monkeypatch, capsys, action, option, value
):
    target, pack, report, identifier, config = candidate(tmp_path)
    assessment = tmp_path / "assessment.json"
    assessment.write_text(json.dumps(report))
    output = tmp_path / "output.json"
    before = snapshot(target)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "govkit",
            "pipeline",
            action,
            "--target",
            str(target),
            "--settings",
            str(config),
            "--pack-source",
            str(pack.root),
            "--as-of",
            AS_OF,
            "--output",
            str(output),
            "--json",
            *(
                ["--assessment", str(assessment), "--recommendation", identifier]
                if action == "upgrade-preview"
                else []
            ),
            option,
            value,
        ],
    )

    with pytest.raises(SystemExit) as error:
        main()

    captured = capsys.readouterr()
    assert error.value.code == 1
    assert option in captured.err and "not valid" in captured.err
    assert captured.out == "" and not output.exists()
    assert snapshot(target) == before


def cli_candidate(tmp_path):
    target = tmp_path / "consumer"
    (target / ".govkit").mkdir(parents=True)
    profile = project().document
    profile["maintenance"]["constraints"].append(
        {
            "component": "govkit",
            "source_id": "team",
            "channel": "stable",
            "compatibility": ">=0.21,<1",
        }
    )
    (target / ".govkit/profile.yaml").write_text(json.dumps(profile))
    pack = load_pack(make_pack(tmp_path / "sample"))
    report = assess_repository(
        target, as_of=AS_OF, metadata=(metadata(release("0.22.0", component="govkit")),)
    ).document
    identifier = next(r["id"] for r in report["recommendations"] if r["action"] == "upgrade-cli")
    config = tmp_path / "settings.json"
    config.write_text(json.dumps(settings()))
    return target, pack, report, identifier, config


def test_cli_upgrade_without_lock_uses_explicit_available_catalog_read_only(tmp_path):
    target, pack, report, identifier, config = cli_candidate(tmp_path)
    before = snapshot(target)

    preview = upgrade_integration_preview(
        target, report, identifier, config, catalog=(pack,), as_of=AS_OF
    )

    assert preview["target_version"] == "0.22.0"
    assert preview["integration"]["artifact"]["binding"]["govkit_version"] == "0.22.0"
    assert preview["integration"]["artifact"]["catalog"]["capabilities"] == ["sample"]
    assert preview["integration"]["writes_authorized"] is False
    assert snapshot(target) == before and not (target / ".govkit/pack-lock.json").exists()


@pytest.mark.parametrize("provider", ["github", "azure"])
@pytest.mark.parametrize("uppercase", ["base", "policy", "event-head", "event-base"])
def test_admitted_runtime_normalizes_full_uppercase_commit_ids(tmp_path, provider, uppercase):
    target, trusted, base, req, rendered, context, revision = prepared(tmp_path, provider)
    if uppercase == "base":
        base = base.upper()
    elif uppercase == "policy":
        revision = revision.upper()
    else:
        field = "head" if uppercase == "event-head" else "base"
        pr = context["payload"]
        if provider == "github":
            entry = pr["pull_request"][field]
            entry["sha"] = entry["sha"].upper()
        else:
            entry = pr["lastMergeSourceCommit" if field == "head" else "lastMergeTargetCommit"]
            entry["commitId"] = entry["commitId"].upper()

    report = run_bound(
        {**rendered.document["binding"], "admission": policy(provider)},
        target,
        trusted,
        req,
        base,
        provider_event=context,
        policy_revision=revision,
        request_digest=content_digest(req.read_bytes()),
    )

    assert report.exit_code == 0
    assert report.change["base"] == base.lower()
    assert report.change["revision"] == git(target, "rev-parse", "HEAD")


@pytest.mark.parametrize("provider", ["github", "azure"])
@pytest.mark.parametrize("length", [40, 64])
def test_native_sha_normalization_supports_both_git_object_formats(provider, length):
    result = parse_event(policy(provider), event(provider, "A" * length, "B" * length))
    assert result.head == "a" * length and result.base == "b" * length


@pytest.mark.parametrize("head", ["0" * 40, "F" * 39, "F" * 41, "G" * 40, "", None, False])
def test_normalization_does_not_admit_zero_partial_or_invalid_commit_ids(head):
    with pytest.raises(ValueError, match="full nonzero commit SHAs"):
        parse_event(policy(), event("github", head, "B" * 40))


def test_cli_upgrade_without_lock_still_requires_a_resolvable_catalog(tmp_path):
    target, _, report, identifier, config = cli_candidate(tmp_path)
    before = snapshot(target)
    with pytest.raises(ValueError, match="resolved catalog"):
        upgrade_integration_preview(target, report, identifier, config, catalog=(), as_of=AS_OF)
    assert snapshot(target) == before


def test_cli_upgrade_keeps_an_existing_lock_instead_of_selecting_a_new_available_pack(tmp_path):
    from cli.pack_store import apply_install, preview_install
    from cli.version import GOVKIT_VERSION

    target, pack, _, _, config = cli_candidate(tmp_path)
    apply_install(
        preview_install(
            target / ".govkit/profile.yaml", target, (pack,), govkit_version=GOVKIT_VERSION
        )
    )
    report = assess_repository(
        target, as_of=AS_OF, metadata=(metadata(release("0.22.0", component="govkit")),)
    ).document
    identifier = next(r["id"] for r in report["recommendations"] if r["action"] == "upgrade-cli")
    available = load_pack(make_pack(tmp_path / "newer", version="2.0.0"))
    before = snapshot(target)

    preview = upgrade_integration_preview(
        target, report, identifier, config, catalog=(available,), as_of=AS_OF
    )

    assert preview["integration"]["artifact"]["catalog"]["pins"]["packs"][0]["version"] == "1.0.0"
    assert snapshot(target) == before
