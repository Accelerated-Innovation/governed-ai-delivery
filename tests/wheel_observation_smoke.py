"""Accepted budgets through installed provider scripts, for each supported agent."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

import cli
from cli import paths
from cli.change_conformance import inspect_change, parse_change_report
from cli.maintenance import assess_repository, parse_assessment
from cli.pack_loading import bundled_catalog
from cli.pack_store import apply_install, preview_install
from cli.pipeline_store import preview_pipeline
from cli.posture_change import export_change_posture, parse_change_posture
from cli.schema_validation import content_digest
from cli.version import GOVKIT_VERSION
from cli.workflows import parse_request

MIB = 1024 * 1024


def run_pilot(workspace, agent, provider, *, default_source=False):
    workspace.mkdir(parents=True, exist_ok=True)
    fixture = json.loads(
        (paths.GOVERNANCE_DIR / "examples/change-conformance/consumer.json").read_text()
    )
    target, trusted = workspace / "consumer", workspace / "policy"
    target.mkdir()
    trusted.mkdir()

    def write(root, name, data):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
        return path

    def git(root, *args):
        # Fixture commits must not leave background writers racing later snapshots.
        return subprocess.run(
            ["git", "-c", "maintenance.auto=false", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit(root):
        git(root, "add", ".")
        git(
            root,
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=pilot@example.invalid",
            "commit",
            "-qm",
            "fixture",
        )
        return git(root, "rev-parse", "HEAD")

    def snapshot():
        return {
            (str(root), str(p.relative_to(root))): (
                p.read_bytes(),
                p.stat().st_mode,
                p.stat().st_mtime_ns,
            )
            for root in (target, trusted)
            for p in root.rglob("*")
            if p.is_file()
        }

    for root in (target, trusted):
        for name, data in fixture["files"].items():
            write(root, name, data)
        if not default_source:
            (root / "src/asset.bin").write_bytes(b"\0" * (MIB + 1))
        git(root, "init", "-q")
    for name, data in fixture["base_files"].items():
        write(target, name, data)
    base = commit(target)
    for name, data in fixture["fixed_files"].items():
        write(target, name, data)
    head = commit(target)
    fixture["profile"]["integrations"] = {"agent": agent, "ci": provider}
    if default_source:
        del fixture["profile"]["policy"]["conformance"]
    else:
        fixture["conformance"]["observation_limits"] = {"max_file_bytes": 2 * MIB}
    profile_path = write(trusted, ".govkit/profile.yaml", json.dumps(fixture["profile"]))
    config_path = write(trusted, "conformance.json", json.dumps(fixture["conformance"]))
    apply_install(
        preview_install(profile_path, trusted, bundled_catalog(), govkit_version=GOVKIT_VERSION)
    )
    revision = commit(trusted)
    checks = [] if default_source else ["project:tests", "llm-exact-match"]
    settings = write(
        workspace,
        "settings.json",
        json.dumps(
            {
                "schema_version": 1,
                "govkit_version": GOVKIT_VERSION,
                "execute_checks": checks,
                "admission": {
                    "provider": provider,
                    "repository": "team/project",
                    "target_ref": "refs/heads/main",
                    "allow_forks": False,
                },
            }
        ),
    )
    integration = workspace / "integration"
    integration.mkdir()
    artifact = preview_pipeline(
        profile_path, integration, settings, bundled_catalog()
    ).artifact.document
    body = yaml.safe_load(artifact["content"])
    step = body["runs"]["steps"][0] if provider == "github" else body["steps"][0]
    script = step.get("run", step.get("bash"))
    if provider == "github":
        event = {
            "event_name": "pull_request",
            "payload": {
                "action": "synchronize",
                "repository": {"full_name": "team/project"},
                "pull_request": {
                    "number": 7,
                    "state": "open",
                    "draft": False,
                    "base": {"ref": "main", "sha": base, "repo": {"full_name": "team/project"}},
                    "head": {"sha": head, "repo": {"full_name": "team/project"}},
                },
            },
        }
    else:
        event = {
            "event_name": "PullRequest",
            "payload": {
                "repository": {"id": "team/project"},
                "pullRequestId": 7,
                "status": "active",
                "isDraft": False,
                "targetRefName": "refs/heads/main",
                "lastMergeSourceCommit": {"commitId": head},
                "lastMergeTargetCommit": {"commitId": base},
            },
        }
    event_path = write(workspace, "event.json", json.dumps(event))
    request_path = paths.GOVERNANCE_DIR / "examples/workflows/requests/enhancement.json"
    arguments = {} if default_source else {"llm-exact-match": ["--results", "results.json"]}
    arguments_path = write(workspace, "arguments.json", json.dumps(arguments))
    env = {
        **os.environ,
        **step["env"],
        "GOVKIT_CHANGE_OUTPUT": "",
        "GOVKIT_PYTHON": sys.executable,
        "GOVKIT_TARGET": str(target),
        "GOVKIT_POLICY_TARGET": str(trusted),
        "GOVKIT_REQUEST": str(request_path),
        "GOVKIT_BASE": base,
        "GOVKIT_POLICY_REVISION": revision,
        "GOVKIT_PROVIDER_EVENT": str(event_path),
        "GOVKIT_REQUEST_DIGEST": content_digest(request_path.read_bytes()),
        "GOVKIT_PACK_ARGUMENTS": str(arguments_path),
        "GOVKIT_OBSERVED_AT": "2026-09-26T17:00:00Z",
    }
    before = snapshot()
    result = subprocess.run(
        ["bash", "-c", script], env=env, cwd=workspace, capture_output=True, text=True
    )
    assert result.returncode == (1 if default_source else 0), (
        agent,
        provider,
        result.stderr,
        result.stdout,
    )
    assert result.stdout, result.stderr
    doc = json.loads(result.stdout)
    local = inspect_change(
        target,
        parse_request(json.loads(request_path.read_text())),
        base=base,
        policy_target=trusted,
        observed_at=env["GOVKIT_OBSERVED_AT"],
        execute_checks=checks,
        pack_arguments=arguments,
    )
    assert doc == local.document == parse_change_report(doc).document
    assert doc["schema_version"] == 2 and doc["change"]["complete"]
    assert doc["change"]["observation"]["limits"]["max_file_bytes"] == (
        MIB if default_source else 2 * MIB
    )
    assert doc["change"]["observation"]["source_state"] == (
        "default" if default_source else "accepted"
    )
    projected = export_change_posture(doc)
    assert parse_change_posture(projected.document).document == projected.document
    assert "asset.bin" not in projected.to_json() and str(workspace) not in projected.to_json()
    maintenance = assess_repository(trusted, as_of=env["GOVKIT_OBSERVED_AT"])
    assert maintenance.document["identity"]["git_complete"]
    assert parse_assessment(maintenance.document).document == maintenance.document
    assert snapshot() == before
    if default_source:
        outcomes = {r.spec.id: r.outcome for r in local.checks.results}
        assert outcomes["change:policy"].state.value == "unknown"
        assert outcomes["change:stable-inputs"].state.value == "pass"
        assert outcomes["project:tests"].execution.value == "not-run"
        return
    original = config_path.read_bytes()
    config_path.write_bytes(original + b"\n")
    dirty_before = snapshot()
    refused = subprocess.run(
        ["bash", "-c", script], env=env, cwd=workspace, capture_output=True, text=True
    )
    assert refused.returncode == 1 and "bootstrap bytes" in refused.stderr and not refused.stdout
    assert snapshot() == dirty_before
    config_path.write_bytes(original)
    # Default conformance cannot be enlarged by a target environment claim.
    del fixture["conformance"]["observation_limits"]
    config_path.write_text(json.dumps(fixture["conformance"]))
    default = inspect_change(
        target,
        parse_request(json.loads(request_path.read_text())),
        base=base,
        policy_target=trusted,
    )
    assert not default.change["complete"] and default.exit_code == 1
    assert default.change["observation"]["limits"]["max_file_bytes"] == MIB


if __name__ == "__main__":
    assert Path(cli.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    with tempfile.TemporaryDirectory(prefix="govkit-observation-pilot-") as directory:
        for agent in ("codex", "claude-code", "copilot"):
            for provider in ("github", "azure"):
                run_pilot(Path(directory).resolve() / agent / provider, agent, provider)
                run_pilot(
                    Path(directory).resolve() / agent / provider / "default-source",
                    agent,
                    provider,
                    default_source=True,
                )
    print(
        "Twelve admitted provider/agent budget pilots: expanded and omitted-source defaults, local parity, provenance, maintenance, privacy, dirty-source rejection and default-limit refusal verified."
    )
