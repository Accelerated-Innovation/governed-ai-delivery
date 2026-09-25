"""Execute the shipped onboarding recipe, including its failing control."""

import json
import os
import re
import shlex
import subprocess
import sys

import pytest

from cli import paths
from cli.agent_layout import AGENT_LAYOUTS


def snapshot(target):
    return {
        p.relative_to(target).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in target.rglob("*")
        if p.is_file()
    }


def recipe(name):
    guide = (paths.REPO_ROOT / "docs/CAPABILITY_ONBOARDING.md").read_text()
    matches = re.findall(
        r"<!-- example: " + re.escape(name) + r" -->\n```bash\n(.*?)\n```", guide, re.S
    )
    assert len(matches) == 1, f"Expected one executable onboarding example: {name}"
    return matches[0]


def run_example(name, target, *, agent="codex", provider="github"):
    env = {
        "PATH": os.defpath,
        "LANG": "C.UTF-8",
        "GOVKIT_DEMO": str(target),
        "GOVKIT_PROFILE": str(target.parent / "proposed-profile.yaml"),
        "GOVKIT_AGENT": agent,
        "GOVKIT_CI": provider,
    }
    shell = f'govkit() {{ {shlex.quote(sys.executable)} -I -B -m cli.govkit "$@"; }}\n'
    return subprocess.run(
        ["bash", "-c", "set -euo pipefail\n" + shell + recipe(name)],
        cwd=target.parent,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )


def prepare(target, *stages, agent="codex", provider="github"):
    target.mkdir()
    (target / "policy.md").write_text(
        "Reviewed fixture policy: evaluate the supplied greeting case.\n"
    )
    (target / "app.py").write_text("# Existing application, keep its bytes.\n")
    (target / "AGENTS.md").write_text("Project-owned instructions.\n")
    for stage in ("profile", *stages):
        result = run_example(stage, target, agent=agent, provider=provider)
        assert result.returncode == 0, (stage, result.stdout, result.stderr)
    return target


@pytest.mark.parametrize("stage", ["discover", "profile-preview", "pack-preview"])
def test_documented_previews_leave_existing_project_unchanged(tmp_path, stage):
    target = prepare(tmp_path / "existing project")
    before = snapshot(target)
    result = run_example(stage, target)
    assert result.returncode == 0, result.stderr
    assert snapshot(target) == before
    assert not (target / ".govkit").exists()


def test_documented_profile_apply_only_materializes_metadata(tmp_path):
    target = prepare(tmp_path / "existing project")
    before = snapshot(target)
    result = run_example("profile-apply", target)
    assert result.returncode == 0, result.stderr
    after = snapshot(target)
    assert set(after) - set(before) == {".govkit/profile.yaml", ".govkit/resolution.json"}
    assert {p: after[p] for p in before} == before


@pytest.mark.parametrize("stage", ["profile-apply", "pack-apply"])
def test_documented_reapplication_preserves_bytes_and_mtimes(tmp_path, stage):
    target = prepare(tmp_path / "existing project", "profile-apply", "pack-apply")
    before = snapshot(target)
    result = run_example(stage, target)
    assert result.returncode == 0, result.stderr
    assert snapshot(target) == before


@pytest.mark.parametrize("agent", ["claude-code", "codex", "copilot"])
@pytest.mark.parametrize("provider", ["github", "azure"])
def test_documented_pack_apply_installs_only_selected_skills(tmp_path, agent, provider):
    target = prepare(tmp_path / "existing project", "profile-apply", agent=agent, provider=provider)
    before = snapshot(target)
    result = run_example("pack-apply", target, agent=agent, provider=provider)
    assert result.returncode == 0, result.stderr
    after = snapshot(target)
    assert {p: after[p] for p in before} == before
    skills = target / AGENT_LAYOUTS[agent].skills_dir
    guide = (paths.REPO_ROOT / "docs/CAPABILITY_ONBOARDING.md").read_text()
    documented_skills = set(re.findall(r"^\| `([^`]+)` \|", guide, re.M))
    assert documented_skills, "The guide must name the installed skills"
    assert {p.parent.name for p in skills.glob("*/SKILL.md")} == documented_skills
    for skill in skills.glob("*/SKILL.md"):
        assert "{{pack_root}}" not in skill.read_text()
        for relative in re.findall(r"\]\((references/[^)]+)\)", skill.read_text()):
            assert (skill.parent / relative).is_file(), (skill, relative)
    lock = json.loads((target / ".govkit/pack-lock.json").read_text())
    assert lock["agent"] == agent
    assert lock["profile"]["integrations"] == {"agent": agent, "ci": provider}
    assert {pack["id"] for pack in lock["packs"]} == {"application-governance", "llm-evaluation"}
    assert not (target / ".govkit/marker.json").exists()
    assert not (target / "features").exists()
    assert not (target / "docs").exists()
    assert not (target / ".github/workflows").exists()


@pytest.mark.parametrize("modified", [False, True])
def test_documented_verify_measures_installed_resources(tmp_path, modified):
    target = prepare(tmp_path / "existing project", "profile-apply", "pack-apply")
    if modified:
        next((target / ".govkit/packs/llm-evaluation").glob("*/checks/exact_match.py")).write_text(
            "pass\n"
        )
    before = snapshot(target)
    result = run_example("pack-verify", target)
    assert result.returncode == (1 if modified else 0), (result.stdout, result.stderr)
    assert snapshot(target) == before


@pytest.mark.parametrize("mismatch", [False, True])
def test_documented_evaluation_measures_supplied_outputs(tmp_path, mismatch):
    target = prepare(
        tmp_path / "existing project", "profile-apply", "pack-apply", "evaluation-input"
    )
    if mismatch:
        result_file = target / "evaluation-results.json"
        doc = json.loads(result_file.read_text())
        doc["cases"][0]["actual"] = "wrong"
        result_file.write_text(json.dumps(doc))
    before = snapshot(target)
    result = run_example("evaluate", target)
    assert result.returncode == (1 if mismatch else 0), (result.stdout, result.stderr)
    report = json.loads(result.stdout)
    assert report["failed"] == (["greeting"] if mismatch else [])
    assert snapshot(target) == before
