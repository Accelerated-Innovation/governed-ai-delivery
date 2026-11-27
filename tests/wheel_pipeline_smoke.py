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
from cli.change_conformance import inspect_change, parse_feature_verdicts
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
        # Fixture commits must not leave background writers racing later snapshots.
        return subprocess.run(
            ["git", "-c", "maintenance.auto=false", "-C", str(target), *args],
            check=True,
            capture_output=True,
            text=True,
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


ACCEPTANCE = """Feature: {title}

  @scenario:{slug}
  Scenario: {title} works
    When it is requested
    Then it answers
"""
ARTIFACTS = {
    "nfrs.md": "## Repository Scope\n\n**Scope:** `single-repo`\n\n## Out of scope\n- none declared yet\n",
    "eval_criteria.yaml": (
        "version: 1\nmode: deterministic\n"
        "unit_tests:\n  enforce_FIRST: true\n  minimum_FIRST_average: 4\n"
        "code_quality:\n  enforce_virtues: true\n  minimum_virtue_average: 4\n"
    ),
    "architecture_preflight.md": "# Architecture Preflight\nAll checks passed.\n",
    "plan.md": "# Plan\n\nReturn the agreed result.\n",
}
FEATURES = {"01_result": "result-works", "02_refund": "refund-works", "03_untouched": "other-works"}


def _junit(outcomes):
    cases = "".join(
        f'<testcase classname="tests.features" name="test_{name}" time="0.01">'
        f'<properties><property name="govkit.scenario" value="{name}#scenario:{slug}"/>'
        f"</properties>{outcomes.get(name, '')}</testcase>"
        for name, slug in FEATURES.items()
    )
    return (
        f'<?xml version="1.0"?><testsuites><testsuite name="pytest" tests="{len(FEATURES)}">'
        f"{cases}</testsuite></testsuites>"
    )


def feature_pilot(workspace, provider):
    """A pipeline generated to judge features: one run, one answer for each touched feature."""
    workspace.mkdir(parents=True)
    root = paths.GOVERNANCE_DIR / "examples"
    fixture = json.loads((root / "change-conformance/consumer.json").read_text())
    target, trusted = workspace / "consumer", workspace / "policy"

    def write(folder, relative, text):
        destination = folder / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text)
        return destination

    for relative, text in {**fixture["files"], **fixture["fixed_files"]}.items():
        write(target, relative, text)
    for relative, text in fixture["files"].items():
        write(trusted, relative, text)
    for name, slug in FEATURES.items():
        write(
            target, f"features/{name}/acceptance.feature", ACCEPTANCE.format(title=name, slug=slug)
        )
        for artifact, text in ARTIFACTS.items():
            write(target, f"features/{name}/{artifact}", text)
    write(target, ".gitignore", "junit.xml\ngovkit-evidence-record.json\n")
    fixture["conformance"]["impact_rules"].append({"paths": ["features"], "impacts": {}})
    write(trusted, "conformance.json", json.dumps(fixture["conformance"]))
    profile = fixture["profile"]
    profile["integrations"] = {"agent": "codex", "ci": provider}
    profile["repository"]["project_type"] = "api"
    source = write(trusted, ".govkit/profile.yaml", json.dumps(profile))
    apply_install(
        preview_install(source, trusted, bundled_catalog(), govkit_version=GOVKIT_VERSION)
    )

    def git(*args):
        return subprocess.run(
            ["git", "-c", "maintenance.auto=false", "-C", str(target), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.email", "pilot@example.invalid")
    git("config", "user.name", "Govkit pilot")
    git("add", ".")
    git("commit", "-qm", "baseline")
    base = git("rev-parse", "HEAD")
    request = json.loads((root / "workflows/requests/feature.json").read_text())
    request["scope"] = [*request["scope"], "features"]
    request_path = write(workspace, "request.json", json.dumps(request))
    arguments = write(
        workspace, "arguments.json", json.dumps({"llm-exact-match": ["--results", "results.json"]})
    )

    def generate(name, **extra):
        settings = write(
            workspace,
            name + "-settings.json",
            json.dumps(
                {
                    "schema_version": 1,
                    "govkit_version": GOVKIT_VERSION,
                    "execute_checks": ["llm-exact-match", "project:tests"],
                    **extra,
                }
            ),
        )
        integration = workspace / name
        integration.mkdir()
        preview = preview_pipeline(source, integration, settings, bundled_catalog())
        apply_pipeline(preview, preview.digest)
        body = yaml.safe_load((integration / preview.artifact.document["path"]).read_text())
        return body["runs"]["steps"][0] if provider == "github" else body["steps"][0]

    def run(step, **variables):
        env = {
            **os.environ,
            **step["env"],
            "GOVKIT_PYTHON": sys.executable,
            "GOVKIT_TARGET": str(target),
            "GOVKIT_POLICY_TARGET": str(trusted),
            "GOVKIT_REQUEST": str(request_path),
            "GOVKIT_BASE": base,
            "GOVKIT_PACK_ARGUMENTS": str(arguments),
            "GOVKIT_OBSERVED_AT": "2026-09-23T12:00:00Z",
            **variables,
        }
        return subprocess.run(
            ["bash", "-c", step.get("run", step.get("bash"))],
            env=env,
            cwd=workspace,
            capture_output=True,
            text=True,
        )

    def record(outcomes):
        write(target, "junit.xml", _junit(outcomes))
        subprocess.run(
            [sys.executable, "-I", "-m", "cli.govkit", "evidence", "--record", "--target", target],
            check=True,
            capture_output=True,
        )

    plain, judged = generate("plain"), generate("judged", features="changed")
    assert "GOVKIT_FEATURE_OUTPUT" in judged["env"] and "GOVKIT_FEATURE_OUTPUT" not in plain["env"]
    for name in ("01_result", "02_refund"):
        write(
            target,
            f"features/{name}/architecture_preflight.md",
            "# Architecture Preflight\nRevised.\n",
        )

    record({})
    before = run(plain)
    assert before.returncode == 0, (provider, before.stderr, before.stdout)
    assert "[" not in "".join(r["id"] for r in json.loads(before.stdout)["checks"]["results"])

    done = tmp = workspace / "done.json"
    result = run(judged, GOVKIT_FEATURE_OUTPUT=str(done))
    assert result.returncode == 0, (provider, result.stderr, result.stdout)
    answers = json.loads(tmp.read_text())
    assert parse_feature_verdicts(answers) == answers
    assert [(a["feature"], a["state"]) for a in answers["features"]] == [
        ("01_result", "done"),
        ("02_refund", "done"),
    ], answers["features"]
    assert answers["change"] == json.loads(result.stdout)
    scoped = [r["id"] for r in answers["change"]["checks"]["results"] if "[" in r["id"]]
    assert len(scoped) == 26 and not any("03_untouched" in name for name in scoped), scoped

    record(
        {
            "01_result": '<failure message="boom">trace</failure>',
            "02_refund": '<skipped message="no service"/>',
        }
    )
    mixed = workspace / "mixed.json"
    result = run(judged, GOVKIT_FEATURE_OUTPUT=str(mixed))
    assert result.returncode == 1, (provider, result.stderr, result.stdout)
    assert "Feature 01_result: CONTINUE" in result.stderr, result.stderr
    assert "Feature 02_refund: ESCALATE" in result.stderr, result.stderr
    answers = json.loads(mixed.read_text())
    assert parse_feature_verdicts(answers) == answers
    assert [a["state"] for a in answers["features"]] == ["continue", "escalate"]
    kept = mixed.read_bytes()
    again = run(judged, GOVKIT_FEATURE_OUTPUT=str(mixed))
    assert again.returncode == 1 and again.stdout == "", (again.stdout, again.stderr)
    assert "Error:" in again.stderr and "Feature 01_result" not in again.stderr, again.stderr
    assert mixed.read_bytes() == kept, "an answers file was overwritten"
    # A pipeline generated without the setting refuses an answers path and writes nothing.
    assert run(plain, GOVKIT_FEATURE_OUTPUT=str(workspace / "none.json")).returncode == 1
    assert not (workspace / "none.json").exists()


if __name__ == "__main__":
    assert Path(cli.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    with tempfile.TemporaryDirectory(prefix="govkit-provider-pilot-") as directory:
        for agent in ("codex", "claude-code", "copilot"):
            # macOS's default temporary path can include the /var symlink.
            run_pilot(Path(directory).resolve() / agent, agent)
        for provider in ("github", "azure"):
            feature_pilot(Path(directory).resolve() / ("features-" + provider), provider)
    example = json.loads(
        (paths.GOVERNANCE_DIR / "examples/feature-verdict/feature-verdicts.json").read_text()
    )
    assert parse_feature_verdicts(example) == example
    print(
        "Three agents, both provider scripts, and a pipeline that judges touched features: protected generation, conditional workflow opt-ins, small/full/LLM local parity, real failures and resolver-version pins verified."
    )
