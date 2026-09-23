"""Reviewable install/remove operations and offline lock verification."""

import json
import shutil

import pytest
import yaml

from cli.agent_layout import AGENT_LAYOUTS
from cli.pack_loading import PackError, bundled_catalog, load_pack
from cli.pack_store import apply_install, execute_check, preview_install, verify_lock
from tests.test_capability_packs import make_pack, profile


def write_profile(target, project):
    (target / ".govkit").mkdir(parents=True, exist_ok=True)
    path = target / ".govkit/profile.yaml"
    path.write_text(yaml.safe_dump(project.document))
    return path


def snapshot(target):
    return {
        p.relative_to(target).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in target.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("agent", ["claude-code", "codex", "copilot"])
def test_preview_native_skills_pins_and_offline_portability(tmp_path, agent):
    source = make_pack(tmp_path / "source", skills=True)
    catalog = (load_pack(source),)
    target = tmp_path / "consumer"
    path = write_profile(target, profile(["sample"], agent=agent))
    (target / "USER.md").write_text("user instructions")
    before = snapshot(target)
    preview = preview_install(path, target, catalog, govkit_version="0.21.1")
    assert preview.resolution.ready
    assert snapshot(target) == before
    apply_install(preview)
    skill = target / AGENT_LAYOUTS[agent].skills_dir / "sample-help/SKILL.md"
    assert "{{pack_root}}" not in skill.read_text()
    assert (skill.parent / "references/guide.md").read_text() == "Useful reference\n"
    after = snapshot(target)
    assert after["USER.md"] == before["USER.md"]
    assert not (target / ".govkit/marker.json").exists()
    apply_install(preview_install(path, target, catalog, govkit_version="0.21.1"))
    assert snapshot(target) == after
    shutil.rmtree(source)
    moved = tmp_path / "other-machine"
    shutil.copytree(target, moved)
    result = verify_lock(moved)
    assert result.ready, result.decisions
    assert agent in (result.agent,)
    lock = json.loads((moved / ".govkit/pack-lock.json").read_text())
    assert str(tmp_path) not in json.dumps(lock)
    assert lock["packs"][0]["digest"] == catalog[0].digest
    assert lock["edges"][0] == {
        "parent": "profile:service",
        "capability": "sample",
        "provider": "sample",
        "reason": "Explicit desired capability",
    }


def test_missing_or_modified_pinned_resources_fail_offline_verification(tmp_path):
    catalog = (load_pack(make_pack(tmp_path / "source", skills=True)),)
    target = tmp_path / "consumer"
    path = write_profile(target, profile(["sample"]))
    apply_install(preview_install(path, target, catalog, govkit_version="0.21.1"))
    resource = next((target / ".govkit/packs").rglob("guide.md"))
    resource.write_text("tampered")
    assert not verify_lock(target).ready
    resource.unlink()
    assert not verify_lock(target).ready


def test_user_customized_skill_is_protected_on_refresh_and_removal(tmp_path):
    source = make_pack(tmp_path / "source", skills=True)
    catalog = (load_pack(source),)
    target = tmp_path / "consumer"
    path = write_profile(target, profile(["sample"]))
    apply_install(preview_install(path, target, catalog, govkit_version="0.21.1"))
    skill = target / ".agents/skills/sample-help/SKILL.md"
    skill.write_text("My customized skill")
    before = snapshot(target)
    preview = preview_install(path, target, catalog, govkit_version="0.21.1")
    assert any(op.action == "protected" for op in preview.operations)
    with pytest.raises(PackError, match="protected"):
        apply_install(preview)
    assert snapshot(target) == before
    path = write_profile(target, profile([]))
    preview = preview_install(path, target, catalog, govkit_version="0.21.1")
    assert any(
        op.path.endswith("SKILL.md") and op.action == "protected" for op in preview.operations
    )
    with pytest.raises(PackError):
        apply_install(preview)
    assert skill.read_text() == "My customized skill"


def test_unedited_removal_is_visible_and_required_control_removal_is_blocked(tmp_path):
    catalog = (
        load_pack(
            make_pack(
                tmp_path / "source",
                skills=True,
                checks=[{"id": "quality", "path": "checks/quality.py", "required": True}],
            )
        ),
    )
    target = tmp_path / "consumer"
    path = write_profile(target, profile(["sample"], checks=["quality"]))
    apply_install(preview_install(path, target, catalog, govkit_version="0.21.1"))
    path = write_profile(target, profile([], checks=["quality"]))
    preview = preview_install(path, target, catalog, govkit_version="0.21.1")
    assert not preview.resolution.ready
    assert any(op.action == "remove" for op in preview.operations)
    before = snapshot(target)
    with pytest.raises(PackError, match="unresolved"):
        apply_install(preview)
    assert snapshot(target) == before
    path = write_profile(target, profile([]))  # explicit accepted policy edit
    preview = preview_install(path, target, catalog, govkit_version="0.21.1")
    apply_install(preview)
    assert not (target / ".agents/skills/sample-help/SKILL.md").exists()
    assert verify_lock(target).ready


@pytest.mark.parametrize("change", ["source", "profile", "destination", "symlink"])
def test_apply_refuses_stale_or_unsafe_inputs_before_writing(tmp_path, change):
    source = make_pack(tmp_path / "source", skills=True)
    target = tmp_path / "consumer"
    path = write_profile(target, profile(["sample"]))
    preview = preview_install(path, target, (load_pack(source),), govkit_version="0.21.1")
    if change == "source":
        (source / "guide.md").write_text("changed")
    elif change == "profile":
        path.write_text(path.read_text() + "\n# changed\n")
    elif change == "destination":
        dest = target / ".agents/skills/sample-help/SKILL.md"
        dest.parent.mkdir(parents=True)
        dest.write_text("someone else's skill")
    else:
        outside = tmp_path / "outside"
        outside.mkdir()
        (target / ".agents").symlink_to(outside, target_is_directory=True)
    before = snapshot(target)
    with pytest.raises(PackError):
        apply_install(preview)
    assert snapshot(target) == before
    assert not (target / ".govkit/pack-lock.json").exists()


def test_executable_llm_evaluation_control_runs_without_an_agent_session(tmp_path):
    target = tmp_path / "consumer"
    path = write_profile(
        target, profile(["application-governance", "llm-evaluation"], checks=["llm-exact-match"])
    )
    preview = preview_install(path, target, bundled_catalog(), govkit_version="0.21.1")
    apply_install(preview)
    results = target / "evaluation-results.json"
    results.write_text(
        json.dumps({"cases": [{"id": "greeting", "expected": "hello", "actual": "hello"}]})
    )
    assert execute_check(target, "llm-exact-match", ("--results", str(results))).returncode == 0
    shutil.rmtree(target / ".agents/skills")
    assert execute_check(target, "llm-exact-match", ("--results", str(results))).returncode == 0
    results.write_text(
        json.dumps({"cases": [{"id": "greeting", "expected": "hello", "actual": "wrong"}]})
    )
    assert execute_check(target, "llm-exact-match", ("--results", str(results))).returncode != 0
    results.write_text('{"cases":[]}')
    assert execute_check(target, "llm-exact-match", ("--results", str(results))).returncode != 0
    script = next((target / ".govkit/packs").rglob("exact_match.py"))
    script.write_text("raise RuntimeError('must never execute modified code')")
    with pytest.raises(PackError, match="pinned|digest|verification"):
        execute_check(target, "llm-exact-match", ("--results", str(results)))


def test_external_preview_profile_requires_explicit_acceptance_before_apply(tmp_path):
    target = tmp_path / "consumer"
    target.mkdir()
    source = tmp_path / "profile.yaml"
    source.write_text(yaml.safe_dump(profile(["sample"]).document))
    preview = preview_install(
        source, target, (load_pack(make_pack(tmp_path / "source")),), govkit_version="0.21.1"
    )
    with pytest.raises(PackError, match="accepted"):
        apply_install(preview)
    assert snapshot(target) == {}


@pytest.mark.parametrize("change", ["escape", "control", "owner", "profile"])
def test_lock_cannot_forge_paths_ownership_or_drop_controls(tmp_path, change):
    target = tmp_path / "consumer"
    path = write_profile(target, profile(["sample"], checks=["quality"]))
    catalog = (
        load_pack(
            make_pack(
                tmp_path / "source",
                skills=True,
                checks=[{"id": "quality", "path": "check.py", "required": True}],
            )
        ),
    )
    apply_install(preview_install(path, target, catalog, govkit_version="0.21.1"))
    lock_path = target / ".govkit/pack-lock.json"
    lock = json.loads(lock_path.read_text())
    if change == "escape":
        lock["packs"][0]["id"] = "../../outside"
    elif change == "control":
        lock["required_checks"] = []
    elif change == "owner":
        lock["files"]["USER.md"] = "0" * 64
    else:
        lock["profile_digest"] = "0" * 64
    lock_path.write_text(json.dumps(lock))
    assert not verify_lock(target).ready
    before = snapshot(target)
    with pytest.raises(PackError):
        preview_install(path, target, catalog, govkit_version="0.21.1")
    assert snapshot(target) == before


def test_write_failure_rolls_back_partial_install(tmp_path, monkeypatch):
    from cli import pack_store

    target = tmp_path / "consumer"
    path = write_profile(target, profile(["sample"]))
    catalog = (load_pack(make_pack(tmp_path / "source", skills=True)),)
    preview = preview_install(path, target, catalog, govkit_version="0.21.1")
    before = snapshot(target)
    original = pack_store.os.replace
    replacements = 0

    def fail_once(source, destination):
        nonlocal replacements
        replacements += 1
        if replacements == 2:
            raise OSError("injected failure")
        original(source, destination)

    monkeypatch.setattr(pack_store.os, "replace", fail_once)
    with pytest.raises(PackError, match="injected failure"):
        apply_install(preview)
    assert snapshot(target) == before


def test_preexisting_native_skill_is_never_claimed_or_replaced(tmp_path):
    target = tmp_path / "consumer"
    path = write_profile(target, profile(["sample"]))
    source = make_pack(tmp_path / "source", skills=True)
    skill = target / ".agents/skills/sample-help/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("User-authored instructions")
    before = snapshot(target)
    preview = preview_install(path, target, (load_pack(source),), govkit_version="0.21.1")
    with pytest.raises(PackError, match="protected"):
        apply_install(preview)
    assert snapshot(target) == before


def test_agent_switch_moves_only_unedited_owned_skills(tmp_path):
    target = tmp_path / "consumer"
    path = write_profile(target, profile(["sample"], agent="codex"))
    catalog = (load_pack(make_pack(tmp_path / "source", skills=True)),)
    apply_install(preview_install(path, target, catalog, govkit_version="0.21.1"))
    frontmatter = (target / ".agents/skills/sample-help/SKILL.md").read_text().split("---")[1]
    write_profile(target, profile(["sample"], agent="copilot"))
    preview = preview_install(path, target, catalog, govkit_version="0.21.1")
    assert any(op.action == "remove" for op in preview.operations)
    apply_install(preview)
    assert not (target / ".agents/skills/sample-help/SKILL.md").exists()
    assert (target / ".github/skills/sample-help/SKILL.md").read_text().split("---")[
        1
    ] == frontmatter
    assert verify_lock(target).ready


def test_offline_use_checks_the_running_govkit_minimum(tmp_path, monkeypatch):
    from cli import version

    target = tmp_path / "consumer"
    path = write_profile(target, profile(["sample"]))
    catalog = (load_pack(make_pack(tmp_path / "source", minimum="0.21.1")),)
    apply_install(preview_install(path, target, catalog, govkit_version="0.21.1"))
    monkeypatch.setattr(version, "GOVKIT_VERSION", "0.1.0")
    assert not verify_lock(target).ready
