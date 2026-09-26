"""Accepted budgets bind capture, provider admission and replay without granting trust."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from cli.change_conformance import parse_change_report
from cli.change_policy import load_change_policy
from cli.gate_catalog import parse_catalog
from cli.maintenance import assess_repository, parse_assessment
from cli.maintenance_inventory import inventory_repository
from cli.pipeline_render import parse_render
from cli.pipeline_runtime import run_bound
from cli.posture import export_posture, parse_posture
from cli.posture_aggregate import aggregate_posture, parse_aggregate
from cli.posture_change import export_change_posture, parse_change_posture
from cli.profiles import load_profile
from cli.schema_validation import canonical_json, content_digest
from tests.test_change_conformance import git, inspect, result, setup
from tests.test_pack_store import snapshot
from tests.test_pipeline_evidence import collect, configured
from tests.test_provider_admission import event, policy, prepared

MIB = 1024 * 1024
AS_OF = "2026-09-26T17:00:00Z"


def configure(root, setting):
    path = root / "conformance.json"
    data = json.loads(path.read_text())
    data["observation_limits"] = setting
    path.write_text(json.dumps(data))
    return content_digest(path.read_bytes())


def commit(root):
    if not (root / ".git").exists():
        git(root, "init", "-q")
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        "budget",
    )
    return git(root, "rev-parse", "HEAD")


@pytest.mark.parametrize(
    "setting", [{}, {"max_file_bytes": 1}, {"max_file_bytes": MIB}, {"max_file_bytes": 8 * MIB}]
)
def test_accepted_policy_allows_only_the_bounded_per_file_setting(tmp_path, setting):
    _, trusted, _ = setup(tmp_path)
    expected = configure(trusted, setting)

    document, digest = load_change_policy(trusted, load_profile(trusted / ".govkit/profile.yaml"))

    assert document["observation_limits"] == setting
    assert digest == expected


@pytest.mark.parametrize(
    "setting",
    [
        None,
        True,
        [],
        {"max_files": 1},
        {"max_file_bytes": None},
        {"max_file_bytes": True},
        {"max_file_bytes": 1.0},
        {"max_file_bytes": 0},
        {"max_file_bytes": -1},
        {"max_file_bytes": 8 * MIB + 1},
    ],
)
def test_invalid_accepted_budget_is_rejected(tmp_path, setting):
    _, trusted, _ = setup(tmp_path)
    configure(trusted, setting)

    with pytest.raises(ValueError):
        load_change_policy(trusted, load_profile(trusted / ".govkit/profile.yaml"))


@pytest.mark.parametrize("phase", ["baseline", "working-tree"])
def test_trusted_budget_captures_binary_scope_and_survives_replay(tmp_path, phase):
    target, trusted, base = setup(tmp_path)
    digest = configure(trusted, {"max_file_bytes": 2 * MIB})
    (target / "src/asset.bin").write_bytes(b"\0" * (MIB + 1))
    if phase == "baseline":
        base = commit(target)
    before = snapshot(target), snapshot(trusted)

    report = inspect(target, trusted, base, execute_checks=("project:tests",))

    assert report.exit_code == 0
    assert result(report, "change:scope").outcome.state.value == "pass"
    assert result(report, "change:stable-inputs").outcome.state.value == "pass"
    assert report.document["schema_version"] == 2
    observation = report.change["observation"]
    assert observation["source_digest"] == digest
    assert observation["source_state"] == "accepted"
    assert observation["limits"] == {
        "max_file_bytes": 2 * MIB,
        "max_files": 2048,
        "max_total_bytes": 16 * MIB,
        "max_changed_paths": 256,
    }
    assert parse_change_report(report.document).document == report.document
    posture = export_change_posture(report.document)
    assert posture.document["schema_version"] == 2
    assert posture.document["identity"]["observation_ref"].startswith("ref:")
    assert "conformance.json" not in posture.to_json()
    assert "asset.bin" not in posture.to_json()
    assert (snapshot(target), snapshot(trusted)) == before


def test_target_configuration_and_environment_cannot_raise_trusted_default(tmp_path, monkeypatch):
    target, trusted, base = setup(tmp_path)
    (target / "conformance.json").write_text('{"observation_limits":{"max_file_bytes":8388608}}')
    (target / "src/asset.bin").write_bytes(b"\0" * (MIB + 1))
    monkeypatch.setenv("GOVKIT_MAX_FILE_BYTES", "8388608")

    report = inspect(target, trusted, base)

    assert not report.change["complete"]
    assert report.change["observation"]["limits"]["max_file_bytes"] == MIB
    assert report.exit_code == 1


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_pinned_provider_bootstrap_handles_large_policy_and_target_checkouts(tmp_path, provider):
    target, trusted, base, req, artifact, _, _ = prepared(tmp_path, provider)
    digest = configure(trusted, {"max_file_bytes": 2 * MIB})
    for root in (target, trusted):
        (root / "src").mkdir(exist_ok=True)
        (root / "src/asset.bin").write_bytes(b"\0" * (MIB + 1))
        commit(root)
    before = snapshot(target), snapshot(trusted)

    report = run_bound(
        {**artifact.document["binding"], "admission": policy(provider)},
        target,
        trusted,
        req,
        base,
        provider_event=event(provider, git(target, "rev-parse", "HEAD"), base),
        policy_revision=git(trusted, "rev-parse", "HEAD"),
        request_digest=content_digest(req.read_bytes()),
        observed_at=AS_OF,
    )

    assert report.exit_code == 0
    assert report.change["observation"]["source_digest"] == digest
    assert (snapshot(target), snapshot(trusted)) == before


@pytest.mark.parametrize("bad", ["dirty-config", "dirty-profile", "missing", "pin"])
def test_unbound_budget_source_never_reaches_execution(tmp_path, bad, monkeypatch):
    from cli import pipeline_runtime

    target, trusted, base, req, artifact, context, revision = prepared(tmp_path)
    configure(trusted, {"max_file_bytes": 2 * MIB})
    revision = commit(trusted)
    if bad == "dirty-config":
        configure(trusted, {"max_file_bytes": 8 * MIB})
    elif bad == "dirty-profile":
        with (trusted / ".govkit/profile.yaml").open("a") as stream:
            stream.write(" ")
    elif bad == "missing":
        (trusted / "conformance.json").unlink()
    else:
        revision = "a" * 40

    def unexpected_execution(*args, **kwargs):
        pytest.fail("Unbound accepted budget reached command execution")

    monkeypatch.setattr(pipeline_runtime, "inspect_change", unexpected_execution)

    with pytest.raises(ValueError):
        run_bound(
            {**artifact.document["binding"], "admission": policy()},
            target,
            trusted,
            req,
            base,
            provider_event=context,
            policy_revision=revision,
            request_digest=content_digest(req.read_bytes()),
        )


@pytest.mark.parametrize("valid", [True, False])
def test_maintenance_uses_accepted_budget_and_marks_invalid_policy_unknown(tmp_path, valid):
    _, trusted, _ = setup(tmp_path)
    configure(trusted, {"max_file_bytes": 2 * MIB if valid else True})
    (trusted / "asset.bin").write_bytes(b"\0" * (MIB + 1))
    commit(trusted)
    before = snapshot(trusted)

    report = assess_repository(trusted, as_of=AS_OF)

    doc = report.document
    assert doc["schema_version"] == doc["inventory"]["schema_version"] == 2
    assert doc["identity"]["git_complete"] is valid
    assert doc["inventory"]["observation"]["source_state"] == (
        "accepted" if valid else "unavailable"
    )
    assert parse_assessment(doc).document == doc
    projected = export_posture(doc)
    assert projected.document["schema_version"] == 2
    assert projected.document["identity"]["observation_digest_ref"].startswith("ref:")
    assert "asset.bin" not in projected.to_json()
    assert snapshot(trusted) == before


@pytest.mark.parametrize("field", ["source_digest", "limits", "missing"])
def test_changed_or_missing_budget_provenance_cannot_replay(tmp_path, field):
    target, trusted, base = setup(tmp_path)
    configure(trusted, {"max_file_bytes": 2 * MIB})
    doc = inspect(target, trusted, base).document
    if field == "missing":
        del doc["change"]["observation"]
    elif field == "limits":
        doc["change"]["observation"]["limits"]["max_file_bytes"] = 8 * MIB
    else:
        doc["change"]["observation"]["source_digest"] = "a" * 64

    with pytest.raises(ValueError):
        parse_change_report(doc)


@pytest.mark.parametrize(
    "kind,parser",
    [
        ("change", parse_change_report),
        ("assessment", parse_assessment),
        ("change_posture", parse_change_posture),
        ("posture", parse_posture),
        ("catalog", parse_catalog),
        ("pipeline", parse_render),
    ],
)
def test_historical_version_one_records_replay_without_changed_bytes(kind, parser):
    saved = json.loads((Path(__file__).parent / "fixtures/observation-v1.json").read_text())[kind]

    replay = parser(deepcopy(saved))

    assert canonical_json(replay.document) == canonical_json(saved)
    assert replay.document["schema_version"] == 1


@pytest.mark.parametrize("boundary", ["file", "total", "count", "changes"])
def test_accepted_expansion_preserves_every_fixed_bound(tmp_path, boundary):
    target, trusted, base = setup(tmp_path)
    configure(trusted, {"max_file_bytes": 8 * MIB})
    if boundary == "file":
        (target / "src/asset.bin").write_bytes(b"\0" * (8 * MIB + 1))
    elif boundary == "total":
        for i in range(3):
            (target / f"src/asset{i}.bin").write_bytes(b"\0" * (6 * MIB))
    else:
        for i in range(2049 if boundary == "count" else 257):
            (target / f"src/item{i}").touch()

    report = inspect(target, trusted, base)

    assert not report.change["complete"]
    assert report.exit_code == 1
    assert any("limit" in p for p in report.change["problems"])


def test_policy_mutating_command_withholds_later_execution_and_invalidates_result(tmp_path):
    target, trusted, base = setup(tmp_path, extra_checks=("project:zzz",))
    configure(trusted, {"max_file_bytes": 2 * MIB})
    source = trusted / "conformance.json"
    marker = tmp_path / "must-not-run"
    config = json.loads(source.read_text())
    config["commands"][0]["argv"] = [
        "{python}",
        "-c",
        f"from pathlib import Path; Path({str(source)!r}).write_text('{{}}')",
    ]
    config["commands"].append(
        {
            "id": "project:zzz",
            "argv": ["{python}", "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"],
            "timeout_seconds": 10,
        }
    )
    source.write_text(json.dumps(config))

    report = inspect(target, trusted, base, execute_checks=("project:tests", "project:zzz"))

    assert result(report, "artifact:test-evidence").outcome.execution.value == "executed"
    assert result(report, "project:zzz").outcome.execution.value == "not-run"
    assert not marker.exists()
    assert result(report, "change:stable-inputs").outcome.state.value == "fail"
    assert report.exit_code == 1


@pytest.mark.parametrize(
    "bad", ["oversized-profile", "oversized-config", "symlink", "mode", "profile-pin"]
)
def test_provider_bootstrap_sources_remain_small_regular_and_profile_bound(tmp_path, bad):
    target, trusted, base, req, artifact, context, _ = prepared(tmp_path)
    configure(trusted, {"max_file_bytes": 2 * MIB})
    binding = {**artifact.document["binding"], "admission": policy()}
    path = trusted / (".govkit/profile.yaml" if bad == "oversized-profile" else "conformance.json")
    if bad.startswith("oversized"):
        with path.open("a") as stream:
            stream.write(" " * 65536)
    revision = commit(trusted)
    if bad == "symlink":
        outside = tmp_path / "substitute.json"
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
    elif bad == "mode":
        path.chmod(0o755)
    elif bad == "profile-pin":
        binding["profile_digest"] = "a" * 64

    with pytest.raises(ValueError):
        run_bound(
            binding,
            target,
            trusted,
            req,
            base,
            provider_event=context,
            policy_revision=revision,
            request_digest=content_digest(req.read_bytes()),
        )


def test_provider_rechecks_bootstrap_after_admission_before_common_engine(tmp_path, monkeypatch):
    from cli import pipeline_runtime

    target, trusted, base, req, artifact, context, _ = prepared(tmp_path)
    configure(trusted, {"max_file_bytes": 2 * MIB})
    revision = commit(trusted)
    original = pipeline_runtime.verified_lock_document

    def changed_after_admission(root):
        lock = original(root)
        configure(trusted, {"max_file_bytes": 8 * MIB})
        return lock

    monkeypatch.setattr(pipeline_runtime, "verified_lock_document", changed_after_admission)

    with pytest.raises(ValueError, match="bootstrap bytes"):
        run_bound(
            {**artifact.document["binding"], "admission": policy()},
            target,
            trusted,
            req,
            base,
            provider_event=context,
            policy_revision=revision,
            request_digest=content_digest(req.read_bytes()),
        )


def test_provider_budget_cannot_change_at_common_engine_entry(tmp_path, monkeypatch):
    from cli import change_conformance, pipeline_runtime

    target, trusted, base, req, artifact, context, _ = prepared(tmp_path)
    configure(trusted, {"max_file_bytes": 2 * MIB})
    revision = commit(trusted)
    original = pipeline_runtime.inspect_change

    def changed_at_entry(*args, **kwargs):
        configure(trusted, {"max_file_bytes": 8 * MIB})
        return original(*args, **kwargs)

    def unexpected_capture(*args, **kwargs):
        pytest.fail("Changed provider budget reached initial capture")

    monkeypatch.setattr(pipeline_runtime, "inspect_change", changed_at_entry)
    monkeypatch.setattr(change_conformance, "capture_observation", unexpected_capture)

    with pytest.raises(ValueError, match="bootstrap bytes"):
        run_bound(
            {**artifact.document["binding"], "admission": policy()},
            target,
            trusted,
            req,
            base,
            provider_event=context,
            policy_revision=revision,
            request_digest=content_digest(req.read_bytes()),
        )


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_evidence_recapture_uses_current_accepted_budget_with_matching_provenance(
    tmp_path, provider
):
    target, config, runtime, observation = configured(tmp_path, provider, observation_limit=2 * MIB)

    report = collect(target, config, runtime, observation)

    outcome = next(r.outcome for r in report.results if r.spec.id == "ci:runtime")
    assert outcome.state.value == "unknown"  # Caller claims never authenticate execution.
    assert "Reported change results: pass" in outcome.summary


@pytest.mark.parametrize("change", ["same-budget-new-bytes", "smaller", "missing", "invalid"])
def test_imported_expansion_cannot_override_current_policy(tmp_path, change):
    target, config, runtime, observation = configured(tmp_path, observation_limit=2 * MIB)
    source = target / "conformance.json"
    if change == "same-budget-new-bytes":
        source.write_text(source.read_text() + "\n")
    elif change == "missing":
        source.unlink()
    else:
        configure(target, {"max_file_bytes": MIB if change == "smaller" else True})

    report = collect(target, config, runtime, observation)

    outcome = next(r.outcome for r in report.results if r.spec.id == "ci:runtime")
    assert outcome.state.value == "unknown"
    assert "Reported change results" not in outcome.summary


def test_maintenance_rejects_oversized_declared_profile_for_budget_resolution(tmp_path):
    _, trusted, _ = setup(tmp_path)
    configure(trusted, {"max_file_bytes": 2 * MIB})
    with (trusted / ".govkit/profile.yaml").open("a") as stream:
        stream.write(" " * 65536)
    commit(trusted)

    doc = inventory_repository(trusted, as_of=AS_OF).document

    assert doc["observation"]["source_state"] == "unavailable"
    assert not doc["identity"]["git_complete"]


def test_mixed_version_aggregate_preserves_original_snapshots(tmp_path):
    target, trusted, base = setup(tmp_path)
    new = export_change_posture(inspect(target, trusted, base).document).document
    old = json.loads((Path(__file__).parent / "fixtures/observation-v1.json").read_text())[
        "posture"
    ]

    doc = aggregate_posture(
        [new, old],
        repository_refs=sorted({new["repository_ref"], old["repository_ref"]}),
        as_of=AS_OF,
    ).document

    assert doc["schema_version"] == 2
    assert old in doc["snapshots"] and new in doc["snapshots"]
    assert parse_aggregate(doc).document == doc


@pytest.mark.parametrize("agent", ["codex", "claude-code", "copilot"])
@pytest.mark.parametrize("provider", ["github", "azure"])
def test_runtime_only_observation_budget_pilot(tmp_path, agent, provider):
    from tests.wheel_observation_smoke import run_pilot

    run_pilot(tmp_path, agent, provider)


@pytest.mark.parametrize("edit", ["staged", "unstaged", "deleted", "symlink", "index-drift"])
def test_accepted_budget_keeps_git_change_and_unsafe_kind_semantics(tmp_path, edit):
    target, trusted, _ = setup(tmp_path)
    configure(trusted, {"max_file_bytes": 2 * MIB})
    asset = target / "src/asset.bin"
    asset.write_bytes(b"\0" * (MIB + 1))
    base = commit(target)
    if edit in ("deleted", "symlink"):
        asset.unlink()
        if edit == "symlink":
            asset.symlink_to(target / "src/service.py")
    else:
        asset.write_bytes(b"\0" * (MIB + 2))
        if edit in ("staged", "index-drift"):
            git(target, "add", "src/asset.bin")
        if edit == "index-drift":
            asset.write_bytes(b"\0" * (MIB + 3))
    before = snapshot(target), snapshot(trusted)

    report = inspect(target, trusted, base)

    assert report.change["complete"] is (edit not in ("symlink", "index-drift"))
    if edit != "symlink":
        assert "src/asset.bin" in {c["path"] for c in report.change["changes"]}
    assert (snapshot(target), snapshot(trusted)) == before


def test_rehashed_source_substitution_still_disagrees_with_accepted_plan(tmp_path):
    target, trusted, base = setup(tmp_path)
    doc = inspect(target, trusted, base).document
    doc["change"]["observation"]["source_digest"] = "b" * 64
    doc["checks"]["identity"]["change_digest"] = content_digest(
        canonical_json(doc["change"]).encode()
    )

    with pytest.raises(ValueError, match="accepted plan evidence"):
        parse_change_report(doc)


def test_consistent_imported_budget_claim_cannot_select_recapture_limits(tmp_path):
    target, config, runtime, observation = configured(tmp_path)
    runtime["change"]["observation"]["limits"]["max_file_bytes"] = 8 * MIB
    runtime["checks"]["identity"]["change_digest"] = content_digest(
        canonical_json(runtime["change"]).encode()
    )
    observation["report_digest"] = content_digest(canonical_json(runtime).encode())
    # Offline replay checks internal consistency, not authority or source bytes.
    assert parse_change_report(runtime).document == runtime
    before = snapshot(target)

    report = collect(target, config, runtime, observation)

    outcome = next(r.outcome for r in report.results if r.spec.id == "ci:runtime")
    assert outcome.state.value == "unknown"
    assert "identities disagree" in outcome.summary
    assert snapshot(target) == before


@pytest.mark.parametrize(
    "name,parser",
    [("observation-change", parse_change_posture), ("observation-maintenance", parse_posture)],
)
def test_version_two_bundled_examples_replay(name, parser):
    from cli import paths

    doc = json.loads((paths.GOVERNANCE_DIR / f"examples/posture/{name}.json").read_text())

    assert parser(doc).document == doc
    assert doc["schema_version"] == 2
