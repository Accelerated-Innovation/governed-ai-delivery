"""Installed-wheel inventory and candidate previews with runtime dependencies only."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from cli import maintenance_inventory, paths
from cli.pack_loading import bundled_catalog

AS_OF = "2026-09-24T12:00:00Z"


def run_pilot(workspace, agent):
    target = workspace / "consumer"
    target.mkdir()
    fixture = paths.GOVERNANCE_DIR / "examples/maintenance"
    document = json.loads((fixture / "profile.json").read_text())
    document["integrations"]["agent"] = agent
    source = workspace / "profile.json"
    source.write_text(json.dumps(document))
    command = [sys.executable, "-I", "-m", "cli.govkit"]

    def cli(*args):
        result = subprocess.run(command + list(map(str, args)), capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        return result.stdout

    cli("profile", "apply", "--profile", source, "--target", target)
    cli("pack", "apply", "--profile", source, "--target", target)
    (target / "USER.md").write_text("Keep user instructions\n")

    def snapshot():
        return {
            p.relative_to(target).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in target.rglob("*")
            if p.is_file()
        }

    def inventory():
        return json.loads(
            cli(
                "maintain",
                "inventory",
                "--target",
                target,
                "--metadata",
                fixture / "releases.json",
                "--as-of",
                AS_OF,
                "--json",
            )
        )

    before = snapshot()
    doc = inventory()
    assert snapshot() == before and doc["lock_verification"] == "verified"
    assert doc["profile_resolution"]["capabilities"] == ["application-governance"]
    candidate = next(c for c in doc["candidates"] if c["component"] == "application-governance")
    assert candidate["newest_known"] == "9.0.0" and candidate["selected_target"] == "1.2.0"
    assert not candidate["latest_verified"]
    record = workspace / "inventory.json"
    record.write_text(json.dumps(doc))
    base = next(p for p in bundled_catalog() if p.id == "application-governance")
    staged = workspace / "candidate"
    shutil.copytree(base.root, staged)
    manifest = staged / "manifest.yaml"
    data = yaml.safe_load(manifest.read_text())
    data["version"] = "1.2.0"
    manifest.write_text(yaml.safe_dump(data))
    result = json.loads(
        cli(
            "maintain",
            "preview",
            "--target",
            target,
            "--inventory",
            record,
            "--component",
            "application-governance",
            "--pack-source",
            staged,
            "--json",
        )
    )
    assert result["ready"] and result["target_version"] == "1.2.0"
    assert snapshot() == before
    skill = next(
        target / r["path"]
        for r in doc["resources"]
        if not r["path"].startswith(".govkit/") and r["path"].endswith("SKILL.md")
    )
    skill.write_text("Team customization\n")
    drifted = inventory()
    assert any(r["action"] == "reconcile-customizations" for r in drifted["resources"])
    record.write_text(json.dumps(drifted))
    result = json.loads(
        cli(
            "maintain",
            "preview",
            "--target",
            target,
            "--inventory",
            record,
            "--component",
            "application-governance",
            "--pack-source",
            staged,
            "--json",
        )
    )
    assert not result["ready"] and result["protected_customizations"]
    assert skill.read_text() == "Team customization\n"
    skill.unlink()
    missing = inventory()
    assert any(r["action"] == "refresh-resources" for r in missing["resources"])
    stale = json.loads(
        cli(
            "maintain",
            "inventory",
            "--target",
            target,
            "--metadata",
            fixture / "releases.json",
            "--as-of",
            "2026-10-01T00:00:00Z",
            "--json",
        )
    )
    assert all(
        c["freshness"] == "stale" and c["selected_target"] is None for c in stale["candidates"]
    )


if __name__ == "__main__":
    assert Path(maintenance_inventory.__file__).is_relative_to(sys.prefix)
    for agent in ("codex", "claude-code", "copilot"):
        with tempfile.TemporaryDirectory(prefix="govkit-maintenance-pilot-") as directory:
            run_pilot(Path(directory), agent)
    print(
        "Three-agent inventory: release candidates, protected previews, resource drift and stale metadata verified."
    )
