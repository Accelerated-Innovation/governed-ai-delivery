"""Runtime-only posture export: three agents, both CI profiles, no test dependencies."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cli
from cli import paths
from cli.maintenance import assess_repository
from cli.posture import export_posture, parse_posture

AS_OF = "2026-09-24T12:00:00Z"


def run_pilot(workspace, agent, provider):
    workspace.mkdir(parents=True)
    target = workspace / "consumer"
    target.mkdir()
    examples = paths.GOVERNANCE_DIR / "examples/maintenance"
    profile = json.loads((examples / "profile.json").read_text())
    profile["integrations"] = {"agent": agent, "ci": provider}
    profile["repository"]["id"] = "private-repository-person"
    source = workspace / "profile.json"
    source.write_text(json.dumps(profile))
    (target / "policy.md").write_text("Private accepted policy text\n")

    def command(*args):
        return subprocess.run(
            [sys.executable, "-I", "-m", "cli.govkit", *map(str, args)],
            capture_output=True,
            text=True,
        )

    for args in [("profile", "apply"), ("pack", "apply")]:
        result = command(*args, "--profile", source, "--target", target)
        assert result.returncode == 0, result.stderr
    # Assessment deliberately contains a compatible update and protected resource drift.
    skill = next(
        p for p in target.rglob("SKILL.md") if ".govkit" not in p.relative_to(target).parts
    )
    skill.write_text("Private team customization\n")
    metadata = json.loads((examples / "releases.json").read_text())
    assessment = assess_repository(target, as_of=AS_OF, metadata=(metadata,)).document
    saved = workspace / "assessment.json"
    saved.write_text(json.dumps(assessment))
    before = {
        p.relative_to(target).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in target.rglob("*")
        if p.is_file()
    }
    expected = export_posture(assessment).document
    output = workspace / "posture.json"
    result = command("posture", "export", "--assessment", saved, "--output", output, "--json")
    assert result.returncode == 0, result.stderr
    actual = json.loads(result.stdout)
    assert actual == expected == json.loads(output.read_text())
    assert parse_posture(actual).document == actual
    assert {r["action"] for r in actual["maintenance"]["recommendations"]} >= {
        "upgrade-pack",
        "reconcile-customizations",
        "repair-ci",
    }
    assert (
        next(d for d in actual["maintenance"]["dimensions"] if d["id"] == "maintenance:ci")["state"]
        == "unknown"
    )
    assert actual["coverage"]["change_results"] == "not-supplied"
    assert "private-repository-person" not in result.stdout and str(target) not in result.stdout
    assert "releases.example.invalid" not in result.stdout and "Private team" not in result.stdout
    assert output.stat().st_mode & 0o777 == 0o600
    human = command("posture", "export", "--assessment", saved)
    assert human.returncode == 0, human.stderr
    for item in actual["maintenance"]["recommendations"]:
        assert item["id"] in human.stdout and item["action"] in human.stdout
    duplicate = command("posture", "export", "--assessment", saved, "--output", output)
    assert duplicate.returncode == 1 and not duplicate.stdout
    assert json.loads(output.read_text()) == actual
    after = {
        p.relative_to(target).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in target.rglob("*")
        if p.is_file()
    }
    assert before == after

    # Partial lock damage is a reportable unknown, including modified resources.
    lock_path = target / ".govkit/pack-lock.json"
    lock = json.loads(lock_path.read_text())
    del lock["owners"][skill.relative_to(target).as_posix()]
    lock_path.write_text(json.dumps(lock))
    assessment = assess_repository(target, as_of=AS_OF, metadata=(metadata,)).document
    saved.write_text(json.dumps(assessment))
    assert assessment["inventory"]["lock_verification"] == "unverified"
    before = {
        p.relative_to(target).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in target.rglob("*")
        if p.is_file()
    }
    result = command("posture", "export", "--assessment", saved, "--json")
    assert result.returncode == 0, result.stderr
    actual = parse_posture(json.loads(result.stdout)).document
    assert actual["capabilities"]["lock_verification"] == "unverified"
    assert sum(r["component_ref"] is None for r in actual["resources"]) == 1
    for projected, original in zip(
        actual["resources"], assessment["inventory"]["resources"], strict=True
    ):
        assert (projected["component_ref"] is None) == (original["owner"] is None)
        assert (projected["state"], projected["action"]) == (original["state"], original["action"])
    human = command("posture", "export", "--assessment", saved)
    assert human.returncode == 0, human.stderr
    for item in assessment["recommendations"]:
        assert item["id"] in human.stdout and item["action"] in human.stdout
    assert before == {
        p.relative_to(target).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in target.rglob("*")
        if p.is_file()
    }


if __name__ == "__main__":
    assert "site-packages" in str(Path(cli.__file__).resolve()), cli.__file__
    example = json.loads((paths.GOVERNANCE_DIR / "examples/posture/maintenance.json").read_text())
    assert parse_posture(example).document == example
    with tempfile.TemporaryDirectory() as directory:
        for agent in ("claude-code", "codex", "copilot"):
            for provider in ("github", "azure"):
                run_pilot(Path(directory).resolve() / agent / provider, agent, provider)
    print(
        "Three agents, both CI profiles: private deterministic posture, canonical action parity, explicit protected publication, unknown CI and missing lock owners verified."
    )
