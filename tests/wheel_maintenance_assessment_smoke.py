"""Runtime-only pilots for consolidated maintenance and protected operation routing."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from cli import maintenance, paths
from cli.check_models import (
    CheckContext,
    CheckOutcome,
    CheckSpec,
    Evidence,
    Execution,
    Identity,
    State,
)
from cli.check_runner import CheckRegistry, run_checks
from cli.discovery import discover
from cli.maintenance_inventory import inventory_repository
from cli.pack_loading import bundled_catalog

AS_OF = "2026-09-24T12:00:00Z"


def run_pilot(workspace, agent):
    target = workspace / "consumer"
    target.mkdir()
    fixture = paths.GOVERNANCE_DIR / "examples/maintenance"
    document = json.loads((fixture / "profile.json").read_text())
    document["integrations"].update(agent=agent, ci="github")
    document["maintenance"]["assessment_max_age_hours"] = 24
    source = workspace / "accepted-profile.json"
    source.write_text(json.dumps(document))
    (target / "policy.md").write_text("Accepted team policy\n")
    (target / "USER.md").write_text("Preserve user instructions\n")

    def cli(*args):
        result = subprocess.run(
            [sys.executable, "-I", "-m", "cli.govkit", *map(str, args)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout

    cli("profile", "apply", "--profile", source, "--target", target)
    cli("pack", "apply", "--profile", source, "--target", target)
    for args in (
        ("init",),
        ("add", "."),
        (
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-m",
            "fixture",
        ),
    ):
        subprocess.run(["git", "-C", str(target), *args], check=True, capture_output=True)
    baseline = discover(target).document
    baseline_path = workspace / "baseline.json"
    baseline_path.write_text(json.dumps(baseline))
    (target / "model.py").write_text("import openai\n")
    inventory = inventory_repository(target, as_of=AS_OF).document
    skill = next(
        target / r["path"]
        for r in inventory["resources"]
        if not r["path"].startswith(".govkit/") and r["path"].endswith("SKILL.md")
    )
    original = skill.read_bytes()
    skill.write_text("Protected team customization\n")

    def snapshot():
        return {
            p.relative_to(target).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in target.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(target).parts
        }

    before = snapshot()
    args = (
        "maintain",
        "assess",
        "--target",
        target,
        "--metadata",
        fixture / "releases.json",
        "--baseline",
        baseline_path,
        "--as-of",
        AS_OF,
        "--json",
    )
    report = json.loads(cli(*args))
    assert {"upgrade-pack", "reconcile-customizations", "review-capability", "repair-ci"} <= {
        r["action"] for r in report["recommendations"]
    }
    assert (
        next(r for r in report["checks"]["results"] if r["id"] == "maintenance:ci")["state"]
        == "unknown"
    )
    assert snapshot() == before
    local = maintenance.assess_repository(
        target,
        as_of=AS_OF,
        metadata=(json.loads((fixture / "releases.json").read_text()),),
        baseline=baseline,
    )
    assert local.document == report

    fields = report["inventory"]["identity"]
    identity = Identity(
        report["repository"],
        revision=fields["revision"],
        dirty_digest=fields["dirty_digest"],
        profile_digest=fields["profile_digest"],
        resolution_digest=fields["resolution_digest"],
        pack_lock_digest=fields["pack_lock_digest"],
        observed_at=AS_OF,
    )
    for state in (State.PASS, State.FAIL):
        registry = CheckRegistry()
        proof = Evidence(
            "ci-run:synthetic",
            (".",),
            "synthetic-provider",
            "tool-execution",
            "a" * 64,
            ("Not live provider enforcement",),
        )
        registry.register(
            "ci:integration",
            lambda _, state=state, proof=proof: CheckOutcome(
                state, Execution.EXECUTED, "Synthetic integration result", evidence=(proof,)
            ),
        )
        canonical = run_checks(
            CheckContext(target, identity),
            (CheckSpec("ci:integration", True, "Accepted integration", "policy.md", (".",)),),
            registry,
        )
        ci_path = workspace / "ci-results.json"
        ci_path.write_text(canonical.to_json())
        assessed = json.loads(cli(*args, "--ci-report", ci_path))
        assert (
            next(r for r in assessed["checks"]["results"] if r["id"] == "maintenance:ci")["state"]
            == state.value
        )
    assert snapshot() == before

    record = workspace / "assessment.json"
    record.write_text(json.dumps(report))
    selected = next(r for r in report["recommendations"] if r["action"] == "upgrade-pack")
    pack = next(p for p in bundled_catalog() if p.id == selected["component"])
    candidate = workspace / "candidate"
    shutil.copytree(pack.root, candidate)
    manifest = candidate / "manifest.yaml"
    data = yaml.safe_load(manifest.read_text())
    data["version"] = selected["target_version"]
    manifest.write_text(yaml.safe_dump(data))
    preview = json.loads(
        cli(
            "maintain",
            "preview",
            "--target",
            target,
            "--assessment",
            record,
            "--recommendation",
            selected["id"],
            "--pack-source",
            candidate,
            "--as-of",
            AS_OF,
            "--json",
        )
    )
    assert not preview["ready"] and preview["protected_customizations"]
    assert preview["target_version"] == "1.2.0"
    assert snapshot() == before
    skill.write_bytes(original)
    repaired = snapshot()
    verified = json.loads(
        cli(
            "maintain",
            "verify",
            "--target",
            target,
            "--assessment",
            record,
            "--as-of",
            AS_OF,
            "--json",
        )
    )
    customization = next(
        r for r in report["recommendations"] if r["action"] == "reconcile-customizations"
    )
    assert customization["id"] in verified["resolved"]
    assert any(
        r["action"] == "review-capability" for r in verified["assessment"]["recommendations"]
    )
    assert snapshot() == repaired


if __name__ == "__main__":
    assert Path(maintenance.__file__).is_relative_to(sys.prefix)
    for agent in ("codex", "claude-code", "copilot"):
        with tempfile.TemporaryDirectory(prefix="govkit-maintenance-assessment-") as directory:
            run_pilot(Path(directory), agent)
    print(
        "Three-agent consolidated assessment: independent dimensions, synthetic CI pass/fail, protected previews and post-repair verification passed."
    )
