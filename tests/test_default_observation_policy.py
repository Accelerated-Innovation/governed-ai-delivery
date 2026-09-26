"""An omitted optional source retains bounded capture, not conformance approval."""

import json

import pytest

from cli.change_conformance import parse_change_report
from cli.observation_policy import ObservationBudget
from cli.pack_loading import bundled_catalog
from cli.pack_store import apply_install, preview_install
from cli.schema_validation import canonical_json, content_digest
from cli.version import GOVKIT_VERSION
from tests.test_change_conformance import inspect, result, setup
from tests.test_pack_store import snapshot
from tests.test_pipeline_evidence import collect, configured


def omit_conformance(trusted):
    source = trusted / ".govkit/profile.yaml"
    profile = json.loads(source.read_text())
    del profile["policy"]["conformance"]
    source.write_text(json.dumps(profile))
    apply_install(
        preview_install(source, trusted, bundled_catalog(), govkit_version=GOVKIT_VERSION)
    )


@pytest.mark.parametrize("changed", [False, True])
def test_omitted_source_keeps_complete_stable_default_capture_without_approval(tmp_path, changed):
    target, trusted, base = setup(tmp_path)
    omit_conformance(trusted)
    if changed:
        (target / "src/service.py").write_text("# good changed\n")
    before = snapshot(target), snapshot(trusted)

    report = inspect(target, trusted, base)

    assert report.change["observation"] == ObservationBudget().document
    assert report.change["complete"]
    assert result(report, "change:stable-inputs").outcome.state.value == "pass"
    assert result(report, "change:scope").outcome.state.value == ("fail" if changed else "pass")
    assert result(report, "change:policy").outcome.state.value == "unknown"
    assert result(report, "project:tests").outcome.execution.value == "not-run"
    assert report.exit_code == 1
    assert parse_change_report(report.document).to_json() == report.to_json()
    assert (snapshot(target), snapshot(trusted)) == before


def test_omitted_source_still_enforces_default_file_limit(tmp_path):
    target, trusted, base = setup(tmp_path)
    omit_conformance(trusted)
    (target / "src/asset.bin").write_bytes(b"\0" * (1024 * 1024 + 1))

    report = inspect(target, trusted, base)

    assert report.change["observation"] == ObservationBudget().document
    assert not report.change["complete"]
    assert result(report, "change:scope").outcome.state.value == "unknown"
    assert report.exit_code == 1
    assert parse_change_report(report.document).document == report.document


@pytest.mark.parametrize("bad", ["missing", "invalid"])
def test_declared_broken_source_cannot_be_treated_as_default(tmp_path, bad):
    target, trusted, base = setup(tmp_path)
    source = trusted / "conformance.json"
    if bad == "missing":
        source.unlink()
    else:
        source.write_text("{}")

    report = inspect(target, trusted, base)

    assert report.change["observation"]["source_state"] == "unavailable"
    assert not report.change["complete"]
    assert result(report, "change:policy").outcome.state.value == "unknown"
    assert result(report, "project:tests").outcome.execution.value == "not-run"
    assert parse_change_report(report.document).document == report.document


def test_default_replay_cannot_discard_a_declared_source(tmp_path):
    target, trusted, base = setup(tmp_path)
    document = inspect(target, trusted, base).document
    document["change"]["observation"] = ObservationBudget().document
    document["checks"]["identity"]["change_digest"] = content_digest(
        canonical_json(document["change"]).encode()
    )

    with pytest.raises(ValueError, match="declared conformance"):
        parse_change_report(document)


def test_unavailable_source_replay_cannot_claim_complete_scope(tmp_path):
    target, trusted, base = setup(tmp_path)
    (trusted / "conformance.json").unlink()
    document = inspect(target, trusted, base).document
    document["change"]["complete"] = True
    document["checks"]["identity"]["change_digest"] = content_digest(
        canonical_json(document["change"]).encode()
    )

    with pytest.raises(ValueError, match="cannot establish complete scope"):
        parse_change_report(document)


def test_default_source_change_during_inspection_invalidates_result(tmp_path, monkeypatch):
    from cli import change_conformance

    target, trusted, base = setup(tmp_path)
    omit_conformance(trusted)
    original = change_conformance.run_checks

    def change_profile_after_checks(*args, **kwargs):
        checks = original(*args, **kwargs)
        path = trusted / ".govkit/profile.yaml"
        profile = json.loads(path.read_text())
        profile["policy"]["conformance"] = {
            "reference": "conformance.json",
            "authority": "accepted",
        }
        path.write_text(json.dumps(profile))
        return checks

    monkeypatch.setattr(change_conformance, "run_checks", change_profile_after_checks)

    report = inspect(target, trusted, base)

    assert report.change["observation"] == ObservationBudget().document
    assert result(report, "change:stable-inputs").outcome.state.value == "fail"
    assert report.exit_code == 1


@pytest.mark.parametrize("provider", ["github", "azure"])
@pytest.mark.parametrize("version", [1, 2])
def test_evidence_matches_default_capture_without_authenticating_it(tmp_path, provider, version):
    target, config, runtime, observation = configured(tmp_path, provider, omit_conformance=True)
    assert runtime["change"]["observation"] == ObservationBudget().document
    assert runtime["change"]["complete"]
    if version == 1:
        # Reconstruct the historical representation: fixed defaults, no provenance.
        runtime["schema_version"] = 1
        del runtime["change"]["observation"]
        runtime["checks"]["identity"]["change_digest"] = content_digest(
            canonical_json(runtime["change"]).encode()
        )
        observation["report_digest"] = content_digest(canonical_json(runtime).encode())
    before = snapshot(target)

    report = collect(target, config, runtime, observation)

    outcomes = {r.spec.id: r.outcome for r in report.results}
    assert "Reported change results: fail" in outcomes["ci:runtime"].summary
    assert outcomes["ci:runtime"].state.value == "fail"
    assert "unauthenticated" in outcomes["ci:runtime"].summary
    assert outcomes["ci:enforcement"].state.value == "unknown"
    assert snapshot(target) == before


@pytest.mark.parametrize("agent", ["codex", "claude-code", "copilot"])
@pytest.mark.parametrize("provider", ["github", "azure"])
def test_installed_provider_default_source_pilot(tmp_path, agent, provider):
    from tests.wheel_observation_smoke import run_pilot

    run_pilot(tmp_path, agent, provider, default_source=True)
