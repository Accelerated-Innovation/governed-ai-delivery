"""Verify request planning, pinned guidance and replay using runtime-only wheels."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from cli import paths, workflows
from cli.agent_layout import AGENT_LAYOUTS
from cli.workflow_store import load_workflow_plan

assert Path(workflows.__file__).is_relative_to(sys.prefix)
root = paths.GOVERNANCE_DIR / "examples/workflows"
fixture = json.loads((root / "consumer.json").read_text())
command = [sys.executable, "-I", "-m", "cli.govkit"]


def invoke(*args):
    result = subprocess.run(command + list(args), check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def snapshot(target):
    return {
        p.relative_to(target).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in target.rglob("*")
        if p.is_file()
    }


expected = {
    "defect": "defect",
    "enhancement": "bounded",
    "refactor": "bounded",
    "mcp": "full-feature",
    "llm": "bounded",
    "feature": "full-feature",
    "architecture": "architecture",
}
assert {p.stem for p in (root / "requests").glob("*.json")} == set(expected)
with tempfile.TemporaryDirectory() as directory:
    workspace = Path(directory)
    for agent in ("codex", "claude-code", "copilot"):
        target = workspace / agent
        target.mkdir()
        for relative, content in fixture["files"].items():
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        user_skill = target / AGENT_LAYOUTS[agent].skills_dir / "request-planning/SKILL.md"
        user_skill.parent.mkdir(parents=True, exist_ok=True)
        user_skill.write_text("# User-owned planning skill\n")
        original_user_skill = (user_skill.read_bytes(), user_skill.stat().st_mtime_ns)
        profile = workspace / f"{agent}-profile.json"
        fixture["profile"]["integrations"]["agent"] = agent
        profile.write_text(json.dumps(fixture["profile"]))
        invoke("profile", "apply", "--target", str(target), "--profile", str(profile), "--json")
        invoke("pack", "apply", "--target", str(target), "--json")
        assert (user_skill.read_bytes(), user_skill.stat().st_mtime_ns) == original_user_skill
        before = snapshot(target)
        for name, workflow in expected.items():
            request = root / "requests" / f"{name}.json"
            result = invoke("request", "plan", str(request), "--target", str(target), "--json")
            assert result["workflow"] == workflow
            assert not any(d["blocking"] for d in result["decisions"])
            assert all(c["execution"] == "not-run" for c in result["checks"])
            assert any(g["id"] == "govkit-request-planning" for g in result["guidance"])
            assert all((target / g["path"]).is_file() for g in result["guidance"])
            record = workspace / f"{agent}-{name}-plan.json"
            record.write_text(json.dumps(result))
            assert load_workflow_plan(record).ready
            again = invoke(
                "request",
                "plan",
                str(request),
                "--target",
                str(target),
                "--previous",
                str(record),
                "--json",
            )
            assert not again["reassessment"]["required"]
            assert snapshot(target) == before
        record = workspace / f"{agent}-enhancement-plan.json"
        scope = workspace / "scope.json"
        scope.write_text(
            json.dumps({"schema_version": 1, "paths": ["auth/login.py"], "impacts": {"auth": True}})
        )
        changed = invoke(
            "request",
            "plan",
            str(root / "requests/enhancement.json"),
            "--target",
            str(target),
            "--previous",
            str(record),
            "--scope",
            str(scope),
            "--json",
        )
        assert changed["reassessment"]["required"]
        assert "review:auth" in {c["id"] for c in changed["checks"]}
        assert snapshot(target) == before
        maximum_request = json.loads((root / "requests/feature.json").read_text())
        maximum_request["scope"] = [f"src/declared-{i}" for i in range(64)]
        maximum_path = workspace / "maximum-request.json"
        maximum_path.write_text(json.dumps(maximum_request))
        observed_paths = [f"src/observed-{i}" for i in range(256)]
        scope.write_text(
            json.dumps({"schema_version": 1, "paths": observed_paths, "impacts": {"auth": True}})
        )
        maximum = invoke(
            "request",
            "plan",
            str(maximum_path),
            "--target",
            str(target),
            "--scope",
            str(scope),
            "--json",
        )
        expected_paths = sorted(maximum_request["scope"] + observed_paths)
        assert maximum["scope"] == expected_paths
        assert all(c["scope"] == expected_paths for c in maximum["checks"])
        record.write_text(json.dumps(maximum))
        assert load_workflow_plan(record).ready
        assert snapshot(target) == before
        native = target / next(
            g["path"] for g in maximum["guidance"] if g["id"] == "govkit-request-planning"
        )
        native.write_text("modified guidance")
        drifted_before = snapshot(target)
        drifted = invoke("request", "plan", str(maximum_path), "--target", str(target), "--json")
        assert not drifted["guidance"]
        assert any(d["blocking"] and d["code"] == "unavailable-lock" for d in drifted["decisions"])
        assert snapshot(target) == drifted_before
print(
    "Workflow wheel smoke passed: seven requests, three agents, verified native guidance, replay, maximum scope, user-skill preservation, resource drift and no writes"
)
