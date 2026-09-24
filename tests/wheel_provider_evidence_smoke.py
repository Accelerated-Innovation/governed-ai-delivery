"""Installed-runtime pilot: admitted provider scripts and canonical maintenance parity."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

import cli
from cli import paths
from cli.maintenance import assess_repository
from cli.pack_loading import bundled_catalog
from cli.pack_store import apply_install, preview_install
from cli.pipeline_assessment import upgrade_integration_preview
from cli.pipeline_evidence import collect_evidence
from cli.pipeline_store import apply_pipeline, preview_pipeline
from cli.schema_validation import canonical_json, content_digest
from cli.version import GOVKIT_VERSION

AS_OF = "2026-09-24T12:00:00Z"


def run_pilot(workspace, agent, provider):
    workspace.mkdir(parents=True)
    target, trusted = workspace / "consumer", workspace / "policy"
    examples = paths.GOVERNANCE_DIR / "examples"
    fixture = json.loads((examples / "change-conformance/consumer.json").read_text())
    profile = fixture["profile"]
    profile["integrations"] = {"agent": agent, "ci": provider}
    profile["maintenance"] = {"assessment_max_age_hours": 24}

    def write(root, name, content):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def git(root, *args):
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    for root in (target, trusted):
        for name, content in {**fixture["files"], **fixture["fixed_files"]}.items():
            write(root, name, content)
        source = write(root, ".govkit/profile.yaml", json.dumps(profile))
        write(root, "conformance.json", json.dumps(fixture["conformance"]))
        apply_install(
            preview_install(source, root, bundled_catalog(), govkit_version=GOVKIT_VERSION)
        )
        git(root, "init", "-q")
        git(root, "config", "user.email", "fixture@example.invalid")
        git(root, "config", "user.name", "Fixture")
    settings = json.loads((examples / f"pipeline/{provider}-admission-settings.json").read_text())
    settings["govkit_version"] = GOVKIT_VERSION
    settings["execute_checks"] = ["project:tests", "llm-exact-match"]
    settings_path = write(workspace, "settings.json", json.dumps(settings))
    proposed = preview_pipeline(
        target / ".govkit/profile.yaml", target, settings_path, bundled_catalog()
    )
    apply_pipeline(proposed, proposed.digest)
    for root in (target, trusted):
        git(root, "add", ".")
        git(root, "commit", "-qm", "configured")
    base = git(target, "rev-parse", "HEAD")
    service = target / "src/service.py"
    service.write_text(service.read_text() + "\n# admitted pilot\n")
    git(target, "add", ".")
    git(target, "commit", "-qm", "change")
    head = git(target, "rev-parse", "HEAD")
    event = json.loads((examples / f"pipeline/{provider}-event.json").read_text())
    if provider == "github":
        event["payload"]["pull_request"]["head"]["sha"] = head
        event["payload"]["pull_request"]["base"]["sha"] = base
    else:
        event["payload"]["lastMergeSourceCommit"]["commitId"] = head
        event["payload"]["lastMergeTargetCommit"]["commitId"] = base
    event_path = write(workspace, "event.json", json.dumps(event))
    req = examples / "workflows/requests/enhancement.json"
    arguments = write(
        workspace, "arguments.json", json.dumps({"llm-exact-match": ["--results", "results.json"]})
    )
    data = yaml.safe_load(proposed.artifact.document["content"])
    step = data["runs"]["steps"][0] if provider == "github" else data["steps"][0]
    output = workspace / "change.json"
    env = {
        **os.environ,
        **step["env"],
        "GOVKIT_PYTHON": sys.executable,
        "GOVKIT_TARGET": str(target),
        "GOVKIT_POLICY_TARGET": str(trusted),
        "GOVKIT_BASE": base.upper(),
        "GOVKIT_REQUEST": str(req),
        "GOVKIT_PACK_ARGUMENTS": str(arguments),
        "GOVKIT_OBSERVED_AT": AS_OF,
        "GOVKIT_PROVIDER_EVENT": str(event_path),
        "GOVKIT_POLICY_REVISION": git(trusted, "rev-parse", "HEAD").upper(),
        "GOVKIT_REQUEST_DIGEST": content_digest(req.read_bytes()),
        "GOVKIT_CHANGE_OUTPUT": str(output),
    }
    run = subprocess.run(
        ["bash", "-c", step.get("run", step.get("bash"))],
        env=env,
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, (agent, provider, run.stderr, run.stdout)
    runtime = json.loads(output.read_text())
    assert runtime == json.loads(run.stdout)
    observation = json.loads((examples / f"pipeline/{provider}-observation.json").read_text())
    observation.update(
        revision=head,
        base=base,
        observed_at=AS_OF,
        artifact_digest=proposed.artifact.document["digest"],
        runtime_version=GOVKIT_VERSION,
        report_digest=content_digest(canonical_json(runtime).encode()),
        enabled=True,
        required_check=True,
        all_changes=True,
        trusted_policy=True,
        approvals=True,
    )
    observation_path = write(workspace, "observation.json", json.dumps(observation))
    evidence = collect_evidence(
        target,
        settings_path,
        bundled_catalog(),
        as_of=AS_OF,
        change_report=runtime,
        observation=observation,
    )
    assert evidence.exit_code == 1 and evidence.state.value == "unknown"
    assert all(
        result.outcome.state.value == "unknown"
        and {proof.origin for proof in result.outcome.evidence} == {"unverified-artifact"}
        for result in evidence.results
        if result.spec.id in {"ci:runtime", "ci:enforcement"}
    )
    expected = assess_repository(target, as_of=AS_OF, ci_report=evidence.to_document()).document
    assessment_path = workspace / "assessment.json"
    assessment = subprocess.run(
        [
            sys.executable,
            "-I",
            "-m",
            "cli.govkit",
            "pipeline",
            "assess",
            "--target",
            str(target),
            "--settings",
            str(settings_path),
            "--change-report",
            str(output),
            "--observation",
            str(observation_path),
            "--as-of",
            AS_OF,
            "--output",
            str(assessment_path),
            "--json",
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    assert assessment.returncode == 0, assessment.stderr
    assert json.loads(assessment.stdout) == json.loads(assessment_path.read_text()) == expected
    assert (
        next(r for r in expected["checks"]["results"] if r["id"] == "maintenance:ci")["state"]
        == "unknown"
    )
    missing = collect_evidence(target, settings_path, bundled_catalog(), as_of=AS_OF)
    assert missing.exit_code == 1 and missing.state.value == "unknown"
    failure = collect_evidence(
        target,
        settings_path,
        bundled_catalog(),
        as_of=AS_OF,
        change_report=runtime,
        observation={**observation, "required_check": False, "report_digest": "d" * 64},
    )
    assert failure.state.value == "fail"
    assert (
        next(r for r in failure.results if r.spec.id == "ci:enforcement").outcome.state.value
        == "fail"
    )
    assert (
        next(r for r in failure.results if r.spec.id == "ci:runtime").outcome.state.value
        == "unknown"
    )

    uninstalled = workspace / "uninstalled"
    desired = {
        **profile,
        "maintenance": {
            "sources": [
                {
                    "id": "team",
                    "url": "https://example.invalid/releases.json",
                    "channels": ["stable"],
                }
            ],
            "constraints": [
                {
                    "component": "govkit",
                    "source_id": "team",
                    "channel": "stable",
                    "compatibility": ">=0.21,<1",
                }
            ],
            "metadata_max_age_hours": 24,
        },
    }
    write(uninstalled, ".govkit/profile.yaml", json.dumps(desired))
    metadata = {
        "schema_version": 1,
        "kind": "release-metadata",
        "source_id": "team",
        "source_url": "https://example.invalid/releases.json",
        "as_of": AS_OF,
        "retrieved_at": AS_OF,
        "lookup_status": "cached",
        "releases": [
            {
                "component": "govkit",
                "version": "0.22.0",
                "channel": "stable",
                "requires_govkit": ">=0.21",
                "requires_python": ">=3.11",
                "dependencies": {},
            }
        ],
    }
    before_upgrade = assess_repository(uninstalled, as_of=AS_OF, metadata=(metadata,)).document
    selected = next(
        r["id"] for r in before_upgrade["recommendations"] if r["action"] == "upgrade-cli"
    )
    upgrade = upgrade_integration_preview(
        uninstalled, before_upgrade, selected, settings_path, catalog=bundled_catalog(), as_of=AS_OF
    )
    assert upgrade["integration"]["artifact"]["catalog"]["ready"]
    assert upgrade["integration"]["artifact"]["binding"]["govkit_version"] == "0.22.0"
    assert not upgrade["integration"]["writes_authorized"]
    assert sorted(
        p.relative_to(uninstalled).as_posix() for p in uninstalled.rglob("*") if p.is_file()
    ) == [".govkit/profile.yaml"]
    # Unsupported events reject before executing or publishing a second artifact.
    event["event_name"] = "push"
    event_path.write_text(json.dumps(event))
    env["GOVKIT_CHANGE_OUTPUT"] = str(workspace / "rejected.json")
    rejected = subprocess.run(
        ["bash", "-c", step.get("run", step.get("bash"))],
        env=env,
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    assert rejected.returncode == 1 and "admission rejected" in rejected.stderr
    assert not (workspace / "rejected.json").exists()
    assert git(target, "status", "--porcelain") == git(trusted, "status", "--porcelain") == ""


if __name__ == "__main__":
    assert Path(cli.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    with tempfile.TemporaryDirectory(prefix="govkit-provider-evidence-") as directory:
        for agent in ("codex", "claude-code", "copilot"):
            for provider in ("github", "azure"):
                run_pilot(Path(directory).resolve() / agent / provider, agent, provider)
    print(
        "Three agents, both providers: uppercase admission, explicit publication, canonical unknown evidence, preserved failures and no-lock upgrade previews verified; provider exports are synthetic."
    )
