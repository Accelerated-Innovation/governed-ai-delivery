"""Version/resource observations remain useful when materialized content drifts."""

import json

import pytest

from cli.maintenance_inventory import inventory_repository, preview_candidate
from cli.pack_loading import load_pack
from cli.pack_store import apply_install, preview_install
from tests.test_capability_packs import make_pack
from tests.test_pack_store import snapshot, write_profile
from tests.test_release_metadata import AS_OF, metadata, project


def installed(tmp_path):
    target = tmp_path / "consumer"
    source = make_pack(tmp_path / "source", skills=True)
    pack = load_pack(source)
    path = write_profile(target, project())
    apply_install(preview_install(path, target, (pack,), govkit_version="0.21.1"))
    (target / ".govkit/marker.json").write_text(
        json.dumps({"version": "0.21.1", "level": "3", "options": {}})
    )
    return target, source


def test_inventory_separates_cli_marker_lock_and_actual_digests_without_writes(tmp_path):
    target, _ = installed(tmp_path)
    before = snapshot(target)
    report = inventory_repository(target, as_of=AS_OF, metadata=(metadata(),))
    doc = report.document
    assert doc["running_cli"] == "0.21.1"
    assert doc["recorded_install"] == "0.21.1"
    assert doc["locked_packs"][0]["version"] == "1.0.0"
    assert doc["resources"] and all(r["state"] == "matching" for r in doc["resources"])
    assert doc["lock_verification"] == "verified"
    assert doc["candidates"][0]["selected_target"] == "1.1.0"
    assert snapshot(target) == before
    assert inventory_repository(target, as_of=AS_OF, metadata=(metadata(),)).digest == report.digest


@pytest.mark.parametrize("change", ["missing", "modified"])
@pytest.mark.parametrize("kind", ["skill", "pinned"])
def test_same_version_never_hides_resource_drift(tmp_path, change, kind):
    target, _ = installed(tmp_path)
    path = (
        target / ".agents/skills/sample-help/SKILL.md"
        if kind == "skill"
        else next((target / ".govkit/packs").rglob("guide.md"))
    )
    if change == "missing":
        path.unlink()
    else:
        path.write_text("team customization")
    before = snapshot(target)
    doc = inventory_repository(target, as_of=AS_OF).document
    resource = next(r for r in doc["resources"] if r["path"] == path.relative_to(target).as_posix())
    assert resource["state"] == change
    assert resource["action"] == (
        "refresh-resources" if change == "missing" else "reconcile-customizations"
    )
    assert doc["lock_verification"] != "verified"
    assert doc["running_cli"] == doc["recorded_install"]
    assert snapshot(target) == before


def test_missing_profile_and_bad_lock_produce_partial_inventory(tmp_path):
    target, _ = installed(tmp_path)
    (target / ".govkit/pack-lock.json").write_text("broken")
    (target / ".govkit/profile.yaml").unlink()
    before = snapshot(target)
    doc = inventory_repository(target, as_of=AS_OF).document
    assert doc["problems"] and doc["lock_verification"] == "unknown"
    assert doc["recorded_install"] == "0.21.1"
    assert doc["candidates"] == []
    assert snapshot(target) == before


def test_symlink_resource_is_unavailable_and_not_read(tmp_path):
    target, _ = installed(tmp_path)
    path = target / ".agents/skills/sample-help/SKILL.md"
    path.unlink()
    outside = tmp_path / "private"
    outside.write_text("private bytes")
    path.symlink_to(outside)
    doc = inventory_repository(target, as_of=AS_OF).document
    resource = next(r for r in doc["resources"] if r["path"] == path.relative_to(target).as_posix())
    assert resource["state"] == "unavailable" and resource["actual_digest"] is None
    assert "private bytes" not in json.dumps(doc)


def test_candidate_preview_uses_real_protected_pack_operations_and_rejects_stale_inventory(
    tmp_path,
):
    target, source = installed(tmp_path)
    manifest = source / "manifest.yaml"
    manifest.write_text(manifest.read_text().replace("1.0.0", "1.1.0"))
    candidate = load_pack(source)
    skill = target / ".agents/skills/sample-help/SKILL.md"
    skill.write_text("user customization")
    report = inventory_repository(target, as_of=AS_OF, metadata=(metadata(),))
    before = snapshot(target)
    preview = preview_candidate(target, report.document, "sample", catalog=(candidate,))
    assert preview["target_version"] == "1.1.0"
    assert not preview["ready"]
    assert any(o["action"] == "protected" for o in preview["operations"])
    assert snapshot(target) == before
    skill.write_text("changed since assessment")
    with pytest.raises(ValueError, match="[Ss]tale"):
        preview_candidate(target, report.document, "sample", catalog=(candidate,))


def test_metadata_candidate_does_not_download_missing_pack(tmp_path):
    target, _ = installed(tmp_path)
    report = inventory_repository(target, as_of=AS_OF, metadata=(metadata(),))
    preview = preview_candidate(target, report.document, "sample", catalog=())
    assert not preview["ready"] and not preview["operations"]
    assert "explicit" in " ".join(preview["decisions"]).lower()


def test_inventory_replays_existing_profile_resolution(tmp_path):
    from cli.profiles import resolve_profile

    target, _ = installed(tmp_path)
    record = resolve_profile(project())
    (target / ".govkit/resolution.json").write_text(record.to_json() + "\n")
    doc = inventory_repository(target, as_of=AS_OF).document
    assert "resolution:invalid" not in doc["problems"]
    assert doc["identity"]["resolution_digest"] is not None
    assert doc["profile_resolution"]["govkit_version"] == "0.21.1"
    assert doc["profile_resolution"]["capabilities"] == ["sample"]


def test_preview_cannot_trust_forged_inventory_actions(tmp_path):
    target, source = installed(tmp_path)
    report = inventory_repository(target, as_of=AS_OF, metadata=(metadata(),)).document
    report["candidates"][0]["selected_target"] = "9.0"
    with pytest.raises(ValueError, match="inventory"):
        preview_candidate(target, report, "sample", catalog=(load_pack(source),))


def test_candidate_preview_names_both_old_and_new_controls(tmp_path):
    from cli.profile_store import apply_profile, preview_materialization
    from tests.test_release_metadata import release

    target, source = installed(tmp_path)
    candidate = load_pack(
        make_pack(
            tmp_path / "candidate",
            version="1.1.0",
            skills=True,
            checks=[{"id": "quality", "path": "checks/quality.py", "required": True}],
        )
    )
    profile_path = target / ".govkit/profile.yaml"
    apply_profile(preview_materialization(profile_path, target))
    report = inventory_repository(target, as_of=AS_OF, metadata=(metadata(release()),))
    before = snapshot(target)
    preview = preview_candidate(target, report.document, "sample", catalog=(candidate,))
    assert preview["ready"]
    assert "quality" in preview["affected_controls"]
    assert {o["action"] for o in preview["operations"]} >= {"create", "remove", "update"}
    assert snapshot(target) == before


@pytest.mark.parametrize("agent", ["codex", "claude-code", "copilot"])
def test_runtime_maintenance_pilot(tmp_path, agent):
    from tests.wheel_maintenance_smoke import run_pilot

    run_pilot(tmp_path, agent)
    assert (tmp_path / "consumer/USER.md").read_text() == "Keep user instructions\n"


def test_git_identity_invalidates_candidate_preview_when_application_changes(tmp_path):
    import subprocess

    target, _ = installed(tmp_path)
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
    before = inventory_repository(target, as_of=AS_OF, metadata=(metadata(),))
    assert before.document["identity"]["git_complete"]
    assert before.document["identity"]["revision"]
    (target / "new-application.py").write_text("# changed application\n")
    after = inventory_repository(target, as_of=AS_OF, metadata=(metadata(),))
    assert after.document["identity"]["dirty_digest"] != before.document["identity"]["dirty_digest"]
    with pytest.raises(ValueError, match="Stale"):
        preview_candidate(target, before.document, "sample")
