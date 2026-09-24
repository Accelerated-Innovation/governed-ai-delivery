"""The source profile exercises real GovKit paths without a consumer installation."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cli.change_conformance import load_change_report
from cli.pack_store import verified_lock_document
from cli.posture import reference
from cli.profiles import load_profile, load_resolution
from tests.test_change_conformance import git
from tests.test_pack_store import snapshot

ROOT = Path(__file__).resolve().parents[1]
CLOCK = "2026-09-24T21:00:00Z"


@pytest.fixture
def source_checkout(tmp_path):
    target, policy = tmp_path / "source", tmp_path / "accepted-policy"
    target.mkdir()
    shutil.copytree(ROOT / ".govkit", target / ".govkit")
    for relative in (
        ".github/workflows/test.yml",
        "tests/test_profiles.py",
        "tests/test_source_pipeline_contract.py",
    ):
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    shutil.copytree(target / ".govkit", policy / ".govkit")
    git(target, "init", "-q")
    git(target, "config", "user.email", "test@example.invalid")
    git(target, "config", "user.name", "Test")
    git(target, "add", ".")
    git(target, "commit", "-qm", "Accepted source baseline")
    base = git(target, "rev-parse", "HEAD")
    (target / "source-change.txt").write_text("An observed source maintenance change.\n")
    return target, policy, base


def command(*args):
    return subprocess.run(
        [sys.executable, "-I", "-B", "-m", "cli.govkit", *map(str, args)],
        capture_output=True,
        text=True,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        timeout=120,
    )


def conform(target, policy, base, *selected):
    return command(
        "conform",
        "--target",
        target,
        "--request",
        policy / ".govkit/requests/source-maintenance.json",
        "--base",
        base,
        "--policy-target",
        policy,
        "--observed-at",
        CLOCK,
        "--json",
        *(arg for check in selected for arg in ("--execute-check", check)),
    )


def results(completed):
    assert completed.stdout, completed.stderr
    report = json.loads(completed.stdout)
    return report, {r["id"]: r for r in report["checks"]["results"]}


def test_source_profile_resolves_and_pins_no_consumer_payload():
    profile = load_profile(ROOT / ".govkit/profile.yaml")
    resolution = load_resolution(ROOT / ".govkit/resolution.json")
    lock = verified_lock_document(ROOT)
    assert profile.repository.id == "Accelerated-Innovation/governed-ai-delivery"
    assert profile.document["capabilities"] == []
    assert resolution.ready and resolution.profile_digest == profile.digest
    assert lock["packs"] == [] and lock["files"] == {} and lock["checks"] == {}
    assert lock["agent"] is None
    assert not (ROOT / ".govkit/marker.json").exists()


@pytest.mark.parametrize("action", [("profile", "preview"), ("pipeline", "catalog")])
def test_source_model_and_catalog_are_read_only(source_checkout, action):
    target, _, _ = source_checkout
    before = snapshot(target)
    completed = command(*action, "--target", target, "--json")
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    if action[0] == "pipeline":
        assert report["ready"] and report["pins"]["packs"] == []
        assert report["execution"] == "not-run" and report["enforcement"] == "unknown"
        assert {g["id"] for g in report["gates"]} >= {
            "project:tests",
            "project:pipeline-contract",
            "provider:protected-caller",
        }
    assert snapshot(target) == before


def test_source_conformance_requires_execution_opt_in(source_checkout):
    target, policy, base = source_checkout
    completed = conform(target, policy, base)
    report, checks = results(completed)
    assert completed.returncode != 0 and report["state"] != "pass"
    for identifier in ("project:tests", "project:pipeline-contract"):
        assert checks[identifier]["state"] == "skipped"
        assert checks[identifier]["execution"] == "not-run"
    assert checks["provider:protected-caller"]["state"] == "unknown"


def test_real_source_checks_and_posture_preserve_external_unknown(source_checkout, tmp_path):
    target, policy, base = source_checkout
    before = snapshot(target), snapshot(policy)
    completed = conform(target, policy, base, "project:tests", "project:pipeline-contract")
    report, checks = results(completed)
    assert completed.returncode != 0 and report["state"] == "unknown", checks
    for identifier in ("project:tests", "project:pipeline-contract", "change:stable-inputs"):
        assert checks[identifier]["state"] == "pass", checks[identifier]
        assert checks[identifier]["execution"] == "executed"
    assert checks["provider:protected-caller"]["state"] == "unknown"
    assert checks["provider:protected-caller"]["execution"] == "not-run"
    assert report["plan"]["decisions"] == []
    path = tmp_path / "change.json"
    path.write_text(completed.stdout)
    assert load_change_report(path).document == report
    exported = command("posture", "change", "--results", path, "--json")
    assert exported.returncode == 0, exported.stderr
    posture = json.loads(exported.stdout)
    assert posture["coverage"]["provider_enforcement"] == "not-supplied"
    controls = {c["ref"]: c for c in posture["results"]["controls"]}
    assert controls[reference("control", "provider:protected-caller")]["state"] == "unknown"
    assert (snapshot(target), snapshot(policy)) == before


@pytest.mark.parametrize("broken", ["tests", "pipeline"])
def test_failed_source_checks_survive_into_canonical_results(source_checkout, broken):
    target, policy, base = source_checkout
    if broken == "tests":
        (target / "tests/test_profiles.py").write_text("def test_regression(): assert False\n")
        identifier = "project:tests"
    else:
        path = target / ".github/workflows/test.yml"
        path.write_text(path.read_text().replace("branches: [main]", "paths: ['cli/**']"))
        identifier = "project:pipeline-contract"
    completed = conform(target, policy, base, identifier)
    report, checks = results(completed)
    assert completed.returncode == 1 and report["state"] == "fail"
    assert checks[identifier]["state"] == "fail"
    assert checks[identifier]["execution"] == "executed"


def test_candidate_profile_cannot_remove_trusted_unknown(source_checkout):
    target, policy, base = source_checkout
    (target / ".govkit/profile.yaml").unlink()
    completed = conform(target, policy, base)
    _, checks = results(completed)
    assert checks["provider:protected-caller"]["required"] is True
    assert checks["provider:protected-caller"]["state"] == "unknown"


@pytest.mark.parametrize("impact", ["security", "llm", "new-feature"])
def test_source_profile_does_not_waive_substantive_request_requirements(source_checkout, impact):
    target, policy, base = source_checkout
    request_path = policy / ".govkit/requests/source-maintenance.json"
    request = json.loads(request_path.read_text())
    if impact == "new-feature":
        request["change"] = "feature"
        request["impacts"]["new-behavior"] = True
    else:
        request["impacts"][impact] = True
    request_path.write_text(json.dumps(request))
    completed = conform(target, policy, base)
    report, checks = results(completed)
    assert completed.returncode != 0
    assert checks["provider:protected-caller"]["required"] is True
    if impact == "security":
        assert checks["review:security"]["required"] is True
        assert checks["review:security"]["state"] == "unknown"
    else:
        capability = "llm-evaluation" if impact == "llm" else "gherkin-delivery"
        assert capability in report["plan"]["required_capabilities"]
        assert any(d["code"] == "missing-capability" for d in report["plan"]["decisions"])


def test_source_conformance_refuses_candidate_as_its_own_policy(source_checkout):
    target, _, base = source_checkout
    completed = conform(target, target, base)
    assert completed.returncode != 0
    assert "separate trusted checkout" in completed.stderr
