"""Safe legacy migration: explicit acceptance, preservation, freshness and rollback."""

import json
from pathlib import Path

import pytest

from cli.migration import apply_migration, preview_migration, rollback_migration
from cli.pack_store import verify_lock
from cli.workflow_store import plan_request
from cli.workflows import parse_request
from tests.test_discovery import write
from tests.test_pack_store import snapshot
from tests.test_workflows import request


def legacy(tmp_path, level="4", agent="codex", flat=False):
    target = tmp_path / "consumer"
    target.mkdir()
    marker = {
        "version": "0.21.1",
        "agent": agent,
        "level": level,
        "options": {"type": "api", "ci": "github"},
        "stack": {"id": "python-fastapi"},
        "authority": {"mode": "enforced", "url": "https://authority.invalid"},
        "calibration": {"completed_at": None, "decisions": ["custom decision"]},
    }
    write(target, ".govkit" if flat else ".govkit/marker.json", json.dumps(marker))
    write(target, "docs/backend/architecture/ARCHITECTURE.md", "# Our edited architecture\n")
    write(target, "AGENTS.md", "Our user-authored guidance\n")
    write(target, ".github/workflows/check.yml", "on: [pull_request]\njobs: {}\n")
    write(target, "extensions/local/manifest.yaml", "id: local\nversion: 1.0.0\n")
    write(target, "features/existing/spec.md", "An existing requirement\n")
    write(target, "src/service.py", "# existing application\n")
    return target


def accepted(tmp_path, target):
    draft = preview_migration(target)
    return write(tmp_path, "accepted.json", json.dumps(draft.document["proposed_profile"]))


@pytest.mark.parametrize("level,count", [("3", 1), ("4", 2), ("5", 3)])
@pytest.mark.parametrize("agent", ["claude-code", "codex", "copilot"])
def test_preview_derives_legacy_capabilities_without_writes(tmp_path, level, count, agent):
    target = legacy(tmp_path, level, agent)
    before = snapshot(target)
    preview = preview_migration(target)
    doc = preview.document
    assert not doc["ready"] and doc["acceptance"] == "proposed"
    assert len(doc["proposed_profile"]["capabilities"]) == count
    assert doc["proposed_profile"]["integrations"]["agent"] == agent
    assert doc["proposed_profile"]["repository"]["stack"] == "python-fastapi"
    assert not doc["enforcement_parity"]
    assert doc["controls"] and all(c["active"] == "unknown" for c in doc["controls"])
    assert snapshot(target) == before
    assert preview_migration(target).digest == preview.digest


@pytest.mark.parametrize("flat", [False, True])
def test_apply_preserves_legacy_and_provides_replayable_request_planning(tmp_path, flat):
    target = legacy(tmp_path, flat=flat)
    before = snapshot(target)
    source = accepted(tmp_path, target)
    preview = preview_migration(target, profile_path=source)
    assert preview.document["ready"]
    result = apply_migration(preview)
    assert result["applied"] and not result["enforcement_parity"]
    assert verify_lock(target).ready
    for path, value in before.items():
        actual = ".govkit/marker.json" if path == ".govkit" else path
        assert snapshot(target)[actual] == value
    assert (
        json.loads((target / ".govkit/marker.json").read_text())["authority"]["mode"] == "enforced"
    )
    after = snapshot(target)
    assert apply_migration(preview)["applied"]
    assert snapshot(target) == after
    plan = plan_request(target, parse_request(request()))
    checks = {c["id"] for c in plan.document["checks"]}
    assert {"legacy:doctor", "migration:ci-enforcement", "migration:authority"} <= checks
    assert plan.document["guidance"]
    rollback_migration(target, expected_digest=preview.digest)
    assert snapshot(target) == before


@pytest.mark.parametrize(
    "mutation", ["marker", "contract", "pipeline", "extension", "profile", "new-file"]
)
def test_stale_preview_is_rejected_before_writes(tmp_path, mutation):
    target = legacy(tmp_path)
    source = accepted(tmp_path, target)
    preview = preview_migration(target, profile_path=source)
    paths = {
        "marker": ".govkit/marker.json",
        "contract": "docs/backend/architecture/ARCHITECTURE.md",
        "pipeline": ".github/workflows/check.yml",
        "extension": "extensions/local/manifest.yaml",
        "new-file": "new-policy.md",
    }
    if mutation == "profile":
        source.write_text(source.read_text() + "\n")
    else:
        write(target, paths[mutation], "changed")
    before = snapshot(target)
    with pytest.raises(ValueError, match="[Ss]tale"):
        apply_migration(preview)
    assert snapshot(target) == before


@pytest.mark.parametrize("drop", ["capability", "control", "contract", "agent"])
def test_accepted_profile_cannot_silently_drop_legacy_obligations(tmp_path, drop):
    target = legacy(tmp_path, "5")
    source = accepted(tmp_path, target)
    document = json.loads(source.read_text())
    if drop == "capability":
        document["capabilities"].pop()
    if drop == "control":
        document["policy"]["workflows"] = []
    if drop == "contract":
        document["policy"]["contracts"] = []
    if drop == "agent":
        document["integrations"]["agent"] = "copilot"
    source.write_text(json.dumps(document))
    before = snapshot(target)
    preview = preview_migration(target, profile_path=source)
    assert not preview.document["ready"]
    with pytest.raises(ValueError):
        apply_migration(preview)
    assert snapshot(target) == before


def test_native_skill_collision_protects_existing_user_content(tmp_path):
    target = legacy(tmp_path)
    write(target, ".agents/skills/application-governance/SKILL.md", "user-owned skill")
    source = accepted(tmp_path, target)
    before = snapshot(target)
    preview = preview_migration(target, profile_path=source)
    assert not preview.document["ready"]
    assert any(o["action"] == "protected" for o in preview.document["operations"])
    with pytest.raises(ValueError):
        apply_migration(preview)
    assert snapshot(target) == before


@pytest.mark.parametrize("flat", [False, True])
def test_rollback_refuses_modified_owned_content(tmp_path, flat):
    target = legacy(tmp_path, flat=flat)
    preview = preview_migration(target, profile_path=accepted(tmp_path, target))
    apply_migration(preview)
    write(target, ".agents/skills/application-governance/SKILL.md", "user edited after migration")
    before = snapshot(target)
    with pytest.raises(ValueError):
        rollback_migration(target, expected_digest=preview.digest)
    assert snapshot(target) == before


def test_unsafe_symlink_and_ambiguous_old_level_fail_closed(tmp_path):
    target = legacy(tmp_path)
    outside = write(tmp_path, "outside", "not target")
    (target / "linked").symlink_to(outside)
    with pytest.raises(ValueError):
        preview_migration(target)
    (target / "linked").unlink()
    path = target / ".govkit/marker.json"
    marker = json.loads(path.read_text())
    marker["version"] = "0.6.0"
    path.write_text(json.dumps(marker))
    preview = preview_migration(target)
    assert not preview.document["ready"]
    assert any("migrate-levels" in d for d in preview.document["decisions"])


def test_caught_write_failure_restores_original_layout_and_bytes(tmp_path, monkeypatch):
    import cli.migration_store as store

    target = legacy(tmp_path, flat=True)
    preview = preview_migration(target, profile_path=accepted(tmp_path, target))
    before = snapshot(target)
    real = store.os.replace
    calls = 0

    def failing(source, destination):
        nonlocal calls
        if Path(destination).is_relative_to(target):
            calls += 1
        if Path(destination).is_relative_to(target) and calls == 3:
            raise OSError("injected replacement failure")
        return real(source, destination)

    monkeypatch.setattr(store.os, "replace", failing)
    with pytest.raises(ValueError):
        apply_migration(preview)
    assert calls >= 3
    assert snapshot(target) == before


def test_cli_defaults_to_preview_and_requires_exact_approval_digest(tmp_path, monkeypatch, capsys):
    import sys

    from cli.govkit import main

    target = legacy(tmp_path)
    before = snapshot(target)
    monkeypatch.setattr(sys, "argv", ["govkit", "migrate", "--target", str(target), "--json"])
    main()
    assert json.loads(capsys.readouterr().out)["acceptance"] == "proposed"
    assert snapshot(target) == before
    source = accepted(tmp_path, target)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "govkit",
            "migrate",
            "apply",
            "--target",
            str(target),
            "--profile",
            str(source),
            "--expected-digest",
            "0" * 64,
        ],
    )
    with pytest.raises(SystemExit):
        main()
    assert snapshot(target) == before


def test_rollback_write_failure_leaves_complete_migrated_install(tmp_path, monkeypatch):
    import cli.migration_store as store

    target = legacy(tmp_path, flat=True)
    preview = preview_migration(target, profile_path=accepted(tmp_path, target))
    apply_migration(preview)
    before = snapshot(target)
    real = store.os.replace
    failed = False

    def failing(source, destination):
        nonlocal failed
        if Path(destination) == target / ".govkit" and not failed:
            failed = True
            raise OSError("injected flat marker restoration failure")
        return real(source, destination)

    monkeypatch.setattr(store.os, "replace", failing)
    with pytest.raises(ValueError):
        rollback_migration(target, expected_digest=preview.digest)
    assert failed
    assert snapshot(target) == before


def test_rollback_preserves_unrelated_new_content_and_directories(tmp_path):
    target = legacy(tmp_path)
    preview = preview_migration(target, profile_path=accepted(tmp_path, target))
    apply_migration(preview)
    new = target / "new-user-directory"
    new.mkdir()
    write(target, "new-user-file", "preserve me")
    rollback_migration(target, expected_digest=preview.digest)
    assert new.is_dir()
    assert (target / "new-user-file").read_text() == "preserve me"


def test_unknown_legacy_options_need_reconciliation(tmp_path):
    target = legacy(tmp_path)
    path = target / ".govkit/marker.json"
    marker = json.loads(path.read_text())
    marker["options"]["additional_policy"] = "security"
    path.write_text(json.dumps(marker))
    preview = preview_migration(target, profile_path=accepted(tmp_path, target))
    assert not preview.document["ready"]
    assert any("additional_policy" in d for d in preview.document["decisions"])


def test_bounded_writer_never_overwrites_an_excluded_existing_destination(tmp_path):
    from cli.migration_store import FileState, capture, write_changes

    target = legacy(tmp_path)
    path = write(target, "vendor/owned.txt", "user content outside the inventory")
    before = snapshot(target)
    with pytest.raises(ValueError):
        write_changes(
            target, capture(target), {"vendor/owned.txt": FileState(b"replacement", 0o600, 0)}
        )
    assert snapshot(target) == before
    assert path.read_text() == "user content outside the inventory"


@pytest.mark.parametrize("agent,level", [("codex", "3"), ("claude-code", "4"), ("copilot", "5")])
def test_real_legacy_install_pilot(tmp_path, agent, level):
    from tests.wheel_migration_smoke import run_pilot

    run_pilot(tmp_path, agent, level)
    assert not (tmp_path / "consumer/.govkit/profile.yaml").exists()


def test_preview_exposes_broken_controls_and_discovery_limits(tmp_path):
    target = legacy(tmp_path)
    preview = preview_migration(target)
    document = preview.document
    assert document["discovery_coverage"]["complete"]
    extensions = next(c for c in document["controls"] if c["id"] == "legacy:extensions")
    assert extensions["active"] == "unknown"
    assert extensions["local_state"] == "fail"
    assert any(
        r["findings"]
        for r in document["local_verification"]["results"]
        if r["id"] == "legacy:extensions"
    )
    assert preview_migration(target).digest == preview.digest


def test_malformed_receipt_is_rejected_before_any_rollback(tmp_path):
    target = legacy(tmp_path)
    preview = preview_migration(target, profile_path=accepted(tmp_path, target))
    apply_migration(preview)
    path = target / ".govkit/migration.json"
    record = json.loads(path.read_text())
    record["created"] = {"USER.md": {"digest": "0" * 64, "mode": 0o644}}
    path.write_text(json.dumps(record))
    before = snapshot(target)
    with pytest.raises(ValueError):
        rollback_migration(target, expected_digest=preview.digest)
    assert snapshot(target) == before


def test_repeat_preview_keeps_control_gaps_visible(tmp_path):
    target = legacy(tmp_path)
    preview = preview_migration(target, profile_path=accepted(tmp_path, target))
    apply_migration(preview)
    repeated = preview_migration(target)
    assert repeated.document["operations"] == []
    assert any(
        c["id"] == "migration:ci-enforcement" and c["active"] == "unknown"
        for c in repeated.document["controls"]
    )


def test_snapshot_limits_block_without_writes(tmp_path):
    target = legacy(tmp_path)
    write(target, "oversized.txt", "x" * (2 * 1024 * 1024 + 1))
    before = snapshot(target)
    with pytest.raises(ValueError, match="limit"):
        preview_migration(target)
    assert snapshot(target) == before
