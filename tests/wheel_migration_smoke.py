"""Real legacy installs and migration/rollback using only shipped runtime dependencies."""

import json
import os
import stat
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
    authority_required = level != "4"
    marker["authority"] = {"source": "pdg" if authority_required else "none"}
    marker_path.write_text(json.dumps(marker))
    marker_path.chmod(0o600)
    if level == "3":
        # Stage the older flat-marker fixture from the installed bundle; keep
        # modern-only metadata such as skill_context.yaml outside this target.
        (target / ".govkit").rename(workspace / "modern-metadata")
        (workspace / "modern-metadata/marker.json").rename(target / ".govkit")
    custom = next((target / "docs/backend/architecture").glob("*.md"))
    custom.write_text(custom.read_text() + "\nTeam customization, preserve exactly.\n")
    user = target / "USER.md"
    user.write_text("User-owned instructions\n")

    legacy_marker = target / ".govkit" if level == "3" else marker_path
    original_bytes = legacy_marker.read_bytes()
    for field, value in (("version", None), ("agent", [])):
        malformed = {**marker, field: value}
        legacy_marker.write_text(json.dumps(malformed))
        checked = subprocess.run(
            command + ["migrate", "--target", str(target), "--json"],
            capture_output=True,
            text=True,
        )
        if field == "version":
            assert checked.returncode == 0, checked.stderr
            document = json.loads(checked.stdout)
            assert not document["ready"]
            assert any("unknown legacy version" in d for d in document["decisions"])
        else:
            assert checked.returncode == 1
            assert "unsupported legacy agent" in checked.stderr
            assert "Traceback" not in checked.stderr
        assert legacy_marker.read_bytes() == json.dumps(malformed).encode()
    legacy_marker.write_bytes(original_bytes)

    def snapshot():
        return {
            p.relative_to(target).as_posix(): (
                p.read_bytes(),
                stat.S_IMODE(p.stat().st_mode),
                p.stat().st_mtime_ns,
            )
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
    assert ("migration:authority" in report["remaining"]) == authority_required
    assert verify_lock(target).ready
    assert all(
        snapshot()[".govkit/marker.json" if name == ".govkit" else name] == value
        for name, value in before.items()
    )
    for name in ("marker.json", "migration-source.json", "migration.json"):
        assert stat.S_IMODE((target / ".govkit" / name).stat().st_mode) == 0o600
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
    assert (
        any(c["id"] == "migration:authority" for c in plan.document["checks"]) == authority_required
    )
    if level == "3":
        original_marker = marker_path.stat()
        for mutation in ("mode", "mtime"):
            if mutation == "mode":
                marker_path.chmod(0o640)
            else:
                changed = original_marker.st_mtime_ns + 1_000_000_000
                os.utime(marker_path, ns=(changed, changed))
            edited = snapshot()
            try:
                migration.rollback_migration(target, expected_digest=approved.digest)
            except ValueError as exc:
                assert "Legacy marker was changed" in str(exc)
            else:
                raise AssertionError("Edited marker metadata was not protected")
            assert snapshot() == edited
            marker_path.chmod(stat.S_IMODE(original_marker.st_mode))
            os.utime(marker_path, ns=(original_marker.st_atime_ns, original_marker.st_mtime_ns))
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
