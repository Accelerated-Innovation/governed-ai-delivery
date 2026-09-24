"""Real legacy installs and migration/rollback using only shipped runtime dependencies."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from cli import migration, paths
from cli.pack_store import verify_lock
from cli.workflow_store import plan_request
from cli.workflows import parse_request


def run_pilot(workspace, agent, level):
    target = workspace / "consumer"
    target.mkdir()
    command = [sys.executable, "-I", "-m", "cli.govkit"]
    installed = subprocess.run(
        command
        + [
            "apply",
            "--agent",
            agent,
            "--level",
            level,
            "--type",
            "api",
            "--ci",
            "github",
            "--stack",
            "python-fastapi",
            "--target",
            str(target),
        ],
        capture_output=True,
        text=True,
    )
    assert installed.returncode == 0, installed.stderr
    marker_path = target / ".govkit/marker.json"
    marker = json.loads(marker_path.read_text())
    marker["authority"] = {"mode": "enforced", "endpoint": "https://authority.invalid"}
    marker_path.write_text(json.dumps(marker))
    custom = next((target / "docs/backend/architecture").glob("*.md"))
    custom.write_text(custom.read_text() + "\nTeam customization, preserve exactly.\n")
    user = target / "USER.md"
    user.write_text("User-owned instructions\n")

    def snapshot():
        return {
            p.relative_to(target).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in target.rglob("*")
            if p.is_file()
        }

    before = snapshot()
    draft = migration.preview_migration(target)
    assert not draft.document["ready"] and snapshot() == before
    source = workspace / "accepted.json"
    source.write_text(json.dumps(draft.document["proposed_profile"]))
    approved = migration.preview_migration(target, profile_path=source)
    assert approved.document["ready"], approved.document["decisions"]
    args = [
        "migrate",
        "apply",
        "--target",
        str(target),
        "--profile",
        str(source),
        "--expected-digest",
        approved.digest,
        "--json",
    ]
    applied = subprocess.run(command + args, capture_output=True, text=True)
    assert applied.returncode == 0, applied.stderr
    report = json.loads(applied.stdout)
    assert report["applied"] and not report["enforcement_parity"]
    assert "migration:ci-enforcement" in report["remaining"]
    assert verify_lock(target).ready
    assert all(snapshot()[name] == value for name, value in before.items())
    current = snapshot()
    again = subprocess.run(command + args, capture_output=True, text=True)
    assert again.returncode == 0, again.stderr
    assert snapshot() == current
    request = json.loads(
        (paths.GOVERNANCE_DIR / "examples/workflows/requests/enhancement.json").read_text()
    )
    request["references"] = []
    plan = plan_request(target, parse_request(request))
    assert plan.ready, plan.document["decisions"]
    assert any(g["id"] == "govkit-request-planning" for g in plan.document["guidance"])
    assert any(c["id"] == "migration:authority" for c in plan.document["checks"])
    # Real drift must block rollback, then restoring original owned bytes permits it.
    profile_path = target / ".govkit/profile.yaml"
    original = profile_path.read_bytes()
    profile_path.write_text("corrupted")
    try:
        migration.rollback_migration(target, expected_digest=approved.digest)
    except ValueError:
        pass
    else:
        raise AssertionError("Edited migration content was not protected")
    profile_path.write_bytes(original)
    migration.rollback_migration(target, expected_digest=approved.digest)
    assert snapshot() == before


if __name__ == "__main__":
    assert Path(migration.__file__).is_relative_to(sys.prefix)
    for agent, level in (("codex", "3"), ("claude-code", "4"), ("copilot", "5")):
        with tempfile.TemporaryDirectory(prefix="govkit-migration-pilot-") as directory:
            run_pilot(Path(directory), agent, level)
    print(
        "Three real legacy installs: migration, preservation, request planning, drift rejection and rollback verified."
    )
