"""Both provider scripts run the same pinned engine over explicit prepared inputs."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from cli.gate_catalog import compose_catalog
from cli.pack_loading import bundled_catalog
from cli.pack_store import apply_install, preview_install
from cli.pipeline_render import parse_settings, render_pipeline
from cli.pipeline_runtime import run_bound
from cli.profiles import load_profile
from cli.version import GOVKIT_VERSION
from tests.test_change_conformance import inspect, setup
from tests.test_discovery import write
from tests.test_pipeline_render import settings
from tests.test_workflows import request


def fixture(tmp_path, provider="github"):
    target, trusted, base = setup(tmp_path)
    source = trusted / ".govkit/profile.yaml"
    document = json.loads(source.read_text())
    document["integrations"]["ci"] = provider
    source.write_text(json.dumps(document))
    apply_install(
        preview_install(source, trusted, bundled_catalog(), govkit_version=GOVKIT_VERSION)
    )
    write(target, "src/service.py", "# good changed\n")
    req = write(tmp_path, "request.json", json.dumps(request()))
    catalog = compose_catalog(
        load_profile(trusted / ".govkit/profile.yaml"),
        bundled_catalog(),
        govkit_version=GOVKIT_VERSION,
    )
    artifact = render_pipeline(catalog, parse_settings(settings(execute_checks=["project:tests"])))
    return target, trusted, base, req, artifact


@pytest.mark.parametrize("provider", ["github", "azure"])
@pytest.mark.parametrize("kind", ["enhancement", "feature"])
def test_runtime_matches_local_engine_for_identical_inputs(tmp_path, provider, kind):
    target, trusted, base, req, artifact = fixture(tmp_path, provider)
    req.write_text(json.dumps(request(kind)))
    report = run_bound(
        artifact.document["binding"], target, trusted, req, base, observed_at="2026-09-23T12:00:00Z"
    )
    assert (
        report.to_json()
        == inspect(
            target, trusted, base, request(kind), execute_checks=("project:tests",)
        ).to_json()
    )


@pytest.mark.parametrize("change", ["version", "profile", "packs", "base", "nested-policy"])
def test_runtime_rejects_mismatched_pins_and_unsafe_bindings(tmp_path, change):
    target, trusted, base, req, artifact = fixture(tmp_path)
    binding = artifact.document["binding"]
    if change == "version":
        binding["govkit_version"] = "99.0.0"
    elif change == "profile":
        binding["profile_digest"] = "a" * 64
    elif change == "packs":
        binding["packs_digest"] = "a" * 64
    elif change == "base":
        base = "HEAD; echo bypass"
    else:
        trusted = target
    with pytest.raises(ValueError):
        run_bound(binding, target, trusted, req, base)


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_generated_script_keeps_shell_characters_in_inputs_literal(tmp_path, provider):
    target, trusted, base, req, artifact = fixture(tmp_path, provider)
    odd = tmp_path / "request ; touch INJECTED.json"
    req.rename(odd)
    document = yaml.safe_load(artifact.document["content"])
    step = document["runs"]["steps"][0] if provider == "github" else document["steps"][0]
    env = {
        **os.environ,
        **step["env"],
        "GOVKIT_PYTHON": sys.executable,
        "GOVKIT_TARGET": str(target),
        "GOVKIT_POLICY_TARGET": str(trusted),
        "GOVKIT_REQUEST": str(odd),
        "GOVKIT_BASE": base,
        "GOVKIT_PACK_ARGUMENTS": "",
        "GOVKIT_OBSERVED_AT": "2026-09-23T12:00:00Z",
    }
    result = subprocess.run(
        ["bash", "-c", step.get("run", step.get("bash"))],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["exit_code"] == 0
    assert not (tmp_path / "INJECTED.json").exists()


@pytest.mark.parametrize("arguments", [[], ["unexpected"], "wrong", 7])
def test_runtime_rejects_non_mapping_pack_arguments(tmp_path, arguments):
    target, trusted, base, req, artifact = fixture(tmp_path)
    with pytest.raises(ValueError, match="arguments"):
        run_bound(
            artifact.document["binding"], target, trusted, req, base, pack_arguments=arguments
        )


@pytest.mark.parametrize("python", ["--help", "python3"])
def test_provider_cannot_pass_with_an_interpreter_option_or_relative_command(tmp_path, python):
    target, trusted, base, req, artifact = fixture(tmp_path)
    step = yaml.safe_load(artifact.document["content"])["runs"]["steps"][0]
    env = {
        **os.environ,
        **step["env"],
        "GOVKIT_PYTHON": python,
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"],
        "GOVKIT_TARGET": str(target),
        "GOVKIT_POLICY_TARGET": str(trusted),
        "GOVKIT_REQUEST": str(req),
        "GOVKIT_BASE": base,
        "GOVKIT_PACK_ARGUMENTS": "",
        "GOVKIT_OBSERVED_AT": "",
    }
    result = subprocess.run(
        ["bash", "-c", step["run"]], env=env, cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "absolute" in result.stderr


@pytest.mark.parametrize("agent", ["codex", "claude-code", "copilot"])
def test_runtime_only_provider_pilot(tmp_path, agent):
    from tests.wheel_pipeline_smoke import run_pilot

    run_pilot(tmp_path, agent)


@pytest.mark.parametrize("llm", [False, True])
def test_small_change_capabilities_do_not_require_gherkin(tmp_path, llm):
    target, trusted, base = setup(tmp_path, llm=llm)
    source = trusted / ".govkit/profile.yaml"
    document = json.loads(source.read_text())
    document["integrations"]["ci"] = "github"
    document["capabilities"] = [
        c for c in document["capabilities"] if c["id"] != "gherkin-delivery"
    ]
    source.write_text(json.dumps(document))
    apply_install(
        preview_install(source, trusted, bundled_catalog(), govkit_version=GOVKIT_VERSION)
    )
    write(target, "src/service.py", "# good changed\n")
    req = write(tmp_path, "request.json", json.dumps(request(llm=llm)))
    checks = ["project:tests"] + (["llm-exact-match"] if llm else [])
    catalog = compose_catalog(
        load_profile(source), bundled_catalog(), govkit_version=GOVKIT_VERSION
    )
    artifact = render_pipeline(catalog, parse_settings(settings(execute_checks=checks)))
    arguments = {"llm-exact-match": ["--results", "results.json"]} if llm else None
    report = run_bound(
        artifact.document["binding"], target, trusted, req, base, pack_arguments=arguments
    )
    assert report.exit_code == 0
    assert report.plan.document["workflow"] == "bounded"
    assert "gherkin-delivery" not in catalog.document["capabilities"]
