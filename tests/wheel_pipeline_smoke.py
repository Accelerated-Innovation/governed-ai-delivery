"""Run both rendered entry points with real installed packs and change conformance."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

import cli
from cli import paths
from cli.change_conformance import inspect_change
from cli.pack_loading import bundled_catalog
from cli.pack_store import apply_install, preview_install
from cli.pipeline_store import apply_pipeline, check_pipeline, preview_pipeline
from cli.version import GOVKIT_VERSION
from cli.workflows import parse_request


def run_pilot(workspace, agent):
    workspace.mkdir(parents=True, exist_ok=True)
    root = paths.GOVERNANCE_DIR / "examples"
    fixture = json.loads((root / "change-conformance/consumer.json").read_text())
    target, trusted = workspace / "consumer", workspace / "policy"
    target.mkdir()
    trusted.mkdir()

    def write(folder, relative, text):
        destination = folder / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text)
        return destination

    for relative, text in fixture["files"].items():
        write(target, relative, text)
        write(trusted, relative, text)
    for relative, text in fixture["base_files"].items():
        write(target, relative, text)
    fixture["profile"]["policy"]["workflows"] = [
        {
            "id": "full-feature-quality",
            "source": {"reference": "policy.md", "authority": "accepted"},
            "when": ["full-feature"],
            "additional_checks": ["feature-quality"],
        }
    ]
    fixture["conformance"]["commands"].append(
        {
            "id": "feature-quality",
            "argv": [
                "{python}",
                "-c",
                "from pathlib import Path; assert '# review-fail' not in Path('src/service.py').read_text()",
            ],
            "timeout_seconds": 10,
        }
    )
    write(trusted, "conformance.json", json.dumps(fixture["conformance"]))

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(target), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.email", "pilot@example.invalid")
    git("config", "user.name", "Govkit pilot")
    git("add", ".")
    git("commit", "-qm", "baseline")
    base = git("rev-parse", "HEAD")
    for relative, text in fixture["fixed_files"].items():
        write(target, relative, text)
    checks = ["llm-exact-match", "project:tests", "feature-quality", "defect:eligibility"]
    arguments = {"llm-exact-match": ["--results", "results.json"]}
    args_path = write(workspace, "arguments.json", json.dumps(arguments))
    settings = write(
        workspace,
        "settings.json",
        json.dumps(
            {
                "schema_version": 1,
                "govkit_version": GOVKIT_VERSION,
                "execute_checks": checks,
            }
        ),
    )
    for provider in ("github", "azure"):
        profile = fixture["profile"]
        profile["integrations"] = {"agent": agent, "ci": provider}
        source = write(trusted, ".govkit/profile.yaml", json.dumps(profile))
        apply_install(
            preview_install(source, trusted, bundled_catalog(), govkit_version=GOVKIT_VERSION)
        )
        integration = workspace / provider
        integration.mkdir()
        preview = preview_pipeline(source, integration, settings, bundled_catalog())
        assert list(integration.iterdir()) == []
        apply_pipeline(preview, preview.digest)
        assert (
            check_pipeline(preview_pipeline(source, integration, settings, bundled_catalog()))[
                "configuration"
            ]
            == "current"
        )
        body = yaml.safe_load((integration / preview.artifact.document["path"]).read_text())
        step = body["runs"]["steps"][0] if provider == "github" else body["steps"][0]
        script = step.get("run", step.get("bash"))
        for name in ("enhancement", "feature", "llm"):
            req_path = root / "workflows/requests" / (name + ".json")
            request = parse_request(json.loads(req_path.read_text()))
            env = {
                **os.environ,
                **step["env"],
                "GOVKIT_PYTHON": sys.executable,
                "GOVKIT_TARGET": str(target),
                "GOVKIT_POLICY_TARGET": str(trusted),
                "GOVKIT_REQUEST": str(req_path),
                "GOVKIT_BASE": base,
                "GOVKIT_PACK_ARGUMENTS": str(args_path),
                "GOVKIT_OBSERVED_AT": "2026-09-23T12:00:00Z",
            }
            result = subprocess.run(
                ["bash", "-c", script], env=env, cwd=workspace, capture_output=True, text=True
            )
            assert result.returncode == 0, (agent, provider, name, result.stderr, result.stdout)
            if name == "feature":
                feature_env = dict(env)
            selected = ["llm-exact-match", "project:tests"] + (
                ["feature-quality"] if name == "feature" else []
            )
            local = inspect_change(
                target,
                request,
                base=base,
                policy_target=trusted,
                observed_at=env["GOVKIT_OBSERVED_AT"],
                execute_checks=selected,
                pack_arguments=arguments,
            )
            assert json.loads(result.stdout) == json.loads(local.to_json())
        results = target / "results.json"
        original = results.read_bytes()
        results.write_text('{"cases":[{"id":"hello","expected":"hi","actual":"wrong"}]}')
        failed = subprocess.run(
            ["bash", "-c", script], env=env, cwd=workspace, capture_output=True, text=True
        )
        assert failed.returncode == 1, failed.stderr
        check = next(
            r
            for r in json.loads(failed.stdout)["checks"]["results"]
            if r["id"] == "llm-exact-match"
        )
        assert check["state"] == "fail"
        results.write_bytes(original)
        service = target / "src/service.py"
        original = service.read_bytes()
        service.write_bytes(original + b"\n# review-fail\n")
        failed = subprocess.run(
            ["bash", "-c", script], env=feature_env, cwd=workspace, capture_output=True, text=True
        )
        assert failed.returncode == 1, failed.stderr
        check = next(
            r
            for r in json.loads(failed.stdout)["checks"]["results"]
            if r["id"] == "feature-quality"
        )
        assert check["state"] == "fail" and check["execution"] == "executed"
        service.write_bytes(original)
        apply_install(preview_install(source, trusted, bundled_catalog(), govkit_version="0.21.2"))
        stale = subprocess.run(
            ["bash", "-c", script], env=env, cwd=workspace, capture_output=True, text=True
        )
        assert stale.returncode == 1 and "lock differs" in stale.stderr
        apply_install(
            preview_install(source, trusted, bundled_catalog(), govkit_version=GOVKIT_VERSION)
        )


if __name__ == "__main__":
    assert Path(cli.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    with tempfile.TemporaryDirectory(prefix="govkit-provider-pilot-") as directory:
        for agent in ("codex", "claude-code", "copilot"):
            # macOS's default temporary path can include the /var symlink.
            run_pilot(Path(directory).resolve() / agent, agent)
    print(
        "Three agents, both provider scripts: protected generation, conditional workflow opt-ins, small/full/LLM local parity, real failures and resolver-version pins verified."
    )
