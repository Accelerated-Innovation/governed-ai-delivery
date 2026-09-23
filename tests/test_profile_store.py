"""Preview/apply operates only on the two explicit profile metadata paths."""

import json
import os

import pytest
import yaml

from cli.profile_store import apply_profile, preview_materialization
from cli.profiles import ProfileError, load_resolution
from tests.test_profiles import profile_document


def snapshot(root):
    return {
        p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in root.rglob("*")
        if p.is_file()
    }


def setup(tmp_path):
    source = tmp_path / "input.yaml"
    source.write_text(yaml.safe_dump(profile_document()))
    target = tmp_path / "consumer"
    target.mkdir()
    (target / "user.txt").write_text("user owned")
    return source, target


def test_preview_no_writes_apply_is_idempotent_and_preserves_legacy_marker(tmp_path):
    source, target = setup(tmp_path)
    (target / ".govkit").mkdir()
    (target / ".govkit/marker.json").write_text('{"agent":"codex","options":{"level":"4"}}')
    before = snapshot(target)
    preview = preview_materialization(source, target)
    assert snapshot(target) == before
    assert {op.path: op.action for op in preview.operations} == {
        ".govkit/profile.yaml": "create",
        ".govkit/resolution.json": "create",
    }
    apply_profile(preview)
    after = snapshot(target)
    assert all(after[key] == value for key, value in before.items())
    assert set(after) - set(before) == {".govkit/profile.yaml", ".govkit/resolution.json"}
    assert (
        load_resolution(target / ".govkit/resolution.json").profile_digest
        == preview.resolution.profile_digest
    )
    apply_profile(preview_materialization(target / ".govkit/profile.yaml", target))
    assert snapshot(target) == after


@pytest.mark.parametrize(
    "field,value",
    [("agent", "copilot"), ("ci", "azure"), ("level", "4"), ("stack", "python-fastapi")],
)
def test_explicit_flags_conflict_instead_of_overriding_profile(tmp_path, field, value):
    source, target = setup(tmp_path)
    before = snapshot(target)
    with pytest.raises(ProfileError, match=field):
        preview_materialization(source, target, overrides={field: value})
    assert snapshot(target) == before


@pytest.mark.parametrize("path", [".govkit/profile.yaml", ".govkit/resolution.json"])
def test_preexisting_user_file_is_protected_before_any_write(tmp_path, path):
    source, target = setup(tmp_path)
    (target / ".govkit").mkdir()
    (target / path).write_text("user-owned content")
    before = snapshot(target)
    preview = preview_materialization(source, target)
    assert any(op.path == path and op.action == "protected" for op in preview.operations)
    with pytest.raises(ProfileError, match="protected"):
        apply_profile(preview)
    assert snapshot(target) == before


@pytest.mark.parametrize("change", ["source", "destination", "symlink"])
def test_apply_rejects_stale_preview_without_writing(tmp_path, change):
    source, target = setup(tmp_path)
    preview = preview_materialization(source, target)
    if change == "source":
        source.write_text(source.read_text() + "\n# changed since preview\n")
    elif change == "destination":
        (target / ".govkit").mkdir()
        (target / ".govkit/profile.yaml").write_text("new user file")
    else:
        outside = tmp_path / "outside"
        outside.mkdir()
        (target / ".govkit").symlink_to(outside, target_is_directory=True)
    before = snapshot(target)
    with pytest.raises(ProfileError, match="(?i)stale|symlink"):
        apply_profile(preview)
    assert snapshot(target) == before
    if change == "symlink":
        assert list(outside.iterdir()) == []


def test_unresolved_profile_refuses_materialization(tmp_path):
    source, target = setup(tmp_path)
    document = profile_document()
    document["capabilities"][0]["requires"] = ["missing"]
    source.write_text(yaml.safe_dump(document))
    preview = preview_materialization(source, target)
    assert not preview.resolution.ready
    with pytest.raises(ProfileError, match="unresolved"):
        apply_profile(preview)
    assert not (target / ".govkit").exists()


def test_editing_accepted_profile_in_place_updates_only_generated_resolution(tmp_path):
    source, target = setup(tmp_path)
    apply_profile(preview_materialization(source, target))
    profile_path = target / ".govkit/profile.yaml"
    document = yaml.safe_load(profile_path.read_text())
    document["policy"]["required_checks"].append({"id": "audit"})
    profile_path.write_text("# keep my comment\n" + yaml.safe_dump(document))
    before = snapshot(target)
    preview = preview_materialization(profile_path, target)
    assert [op.action for op in preview.operations] == ["preserve", "update"]
    apply_profile(preview)
    after = snapshot(target)
    assert after[".govkit/profile.yaml"] == before[".govkit/profile.yaml"]
    assert {
        c["id"]
        for c in json.loads(after[".govkit/resolution.json"][0])["plan"]["selections"]["checks"]
    } == {"security", "audit"}


def test_second_write_failure_rolls_back_and_cleans_staging_files(tmp_path, monkeypatch):
    source, target = setup(tmp_path)
    preview = preview_materialization(source, target)
    real_replace = os.replace

    def fail_resolution(source_path, destination):
        if destination.name == "resolution.json":
            raise OSError("injected disk failure")
        return real_replace(source_path, destination)

    monkeypatch.setattr(os, "replace", fail_resolution)
    before = snapshot(target)
    with pytest.raises(ProfileError, match="injected disk failure"):
        apply_profile(preview)
    assert snapshot(target) == before
    assert not (target / ".govkit").exists()


def test_hand_edited_generated_record_is_protected(tmp_path):
    source, target = setup(tmp_path)
    apply_profile(preview_materialization(source, target))
    record_path = target / ".govkit/resolution.json"
    data = json.loads(record_path.read_text())
    data["plan"]["selections"]["checks"] = []
    record_path.write_text(json.dumps(data))
    before = snapshot(target)
    preview = preview_materialization(source, target)
    assert preview.operations[1].action == "protected"
    with pytest.raises(ProfileError, match="protected"):
        apply_profile(preview)
    assert snapshot(target) == before


@pytest.mark.parametrize(
    "metadata",
    [
        {"status": "available", "latest": "99.0.0"},
        {"status": "stale", "as_of": "2000-01-01"},
        {"status": "unavailable"},
    ],
)
def test_release_cache_and_lock_are_not_read_as_current_policy_or_modified(
    tmp_path, monkeypatch, metadata
):
    source, target = setup(tmp_path)
    managed = target / ".govkit"
    managed.mkdir()
    cache, lock = managed / "releases.json", managed / "lock.json"
    cache.write_text(json.dumps(metadata))
    lock.write_text('{"intentional_pin":"0.21.1"}')
    before = snapshot(target)
    path_type = type(cache)
    real_open = path_type.open

    def guarded_open(path, *args, **kwargs):
        if path in (cache, lock):
            raise AssertionError("Profile command inspected unrelated release/lock state")
        return real_open(path, *args, **kwargs)

    with monkeypatch.context() as guard:
        guard.setattr(path_type, "open", guarded_open)
        preview = preview_materialization(source, target)
        assert preview.resolution.ready
        assert preview.resolution.release_metadata_status == "not-queried"
        apply_profile(preview)
    after = snapshot(target)
    assert after[".govkit/releases.json"] == before[".govkit/releases.json"]
    assert after[".govkit/lock.json"] == before[".govkit/lock.json"]
