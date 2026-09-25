"""Native skill aliases, preserved upstream copies and old-lock upgrades."""

import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

from cli import paths
from cli.agent_layout import AGENT_LAYOUTS
from cli.cmd_extension import cmd_extension_add
from cli.pack_loading import PackError, load_pack
from cli.pack_store import apply_install, preview_install, verify_lock
from cli.schema_validation import canonical_json
from tests.test_capability_packs import make_pack, profile
from tests.test_cmd_extension import TestExtensionAddSkills as SkillsFixture
from tests.test_cmd_extension import _add_args
from tests.test_pack_store import snapshot, write_profile


def install(source, target, method, agent, monkeypatch):
    if method == "extension":
        monkeypatch.setattr(paths, "EXTENSION_PACKS_DIR", source.parent)
        from cli.marker import write_govkit_marker

        target.mkdir()
        write_govkit_marker(target, agent, "4", {"type": "api", "ci": "github"})
        cmd_extension_add(_add_args(source.name, target))
        return target / "extensions" / source.name
    pack = load_pack(source)
    path = write_profile(target, profile([pack.id], agent=agent))
    apply_install(preview_install(path, target, (pack,), govkit_version="0.21.1"))
    assert verify_lock(target).ready
    return target / ".govkit/packs" / pack.id / pack.digest


@pytest.mark.parametrize("agent", AGENT_LAYOUTS)
@pytest.mark.parametrize("method", ["extension", "pack"])
def test_otter_native_names_and_sibling_references_match_install_as(
    tmp_path, monkeypatch, agent, method
):
    source = paths.EXTENSION_PACKS_DIR / "otter-skills"
    original = snapshot(source)
    target = tmp_path / "consumer"
    pinned = install(source, target, method, agent, monkeypatch)
    manifest = yaml.safe_load((source / "manifest.yaml").read_text())
    native = target / AGENT_LAYOUTS[agent].skills_dir
    names = [Path(entry["path"]).name for entry in manifest["skills"]]
    for entry in manifest["skills"]:
        skill = native / entry["install_as"] / "SKILL.md"
        text = skill.read_text()
        metadata = yaml.safe_load(text.split("---", 2)[1])
        assert metadata["name"] == skill.parent.name
        for name in names:
            assert not re.search(rf"(?<![\w/-]){re.escape(name)}(?![\w/-])", text), skill
        for original_file in (source / entry["path"]).rglob("*"):
            if not original_file.is_file():
                continue
            relative = original_file.relative_to(source)
            assert (pinned / relative).read_bytes() == original_file.read_bytes()
            if original_file.name != "SKILL.md":
                suffix = original_file.relative_to(source / entry["path"])
                assert (skill.parent / suffix).read_bytes() == original_file.read_bytes()
    assert snapshot(source) == original


@pytest.mark.parametrize("method", ["extension", "pack"])
def test_native_references_preserve_urls_paths_and_longer_names(tmp_path, monkeypatch, method):
    source = SkillsFixture._bundle_skills_pack(tmp_path / "packs")
    skill = source / "skills/unit-testing/SKILL.md"
    skill.write_text(
        "---\nname: 'unit-testing'\ndescription: Use unit-testing.\n---\n"
        "Use `unit-testing`, /unit-testing and $unit-testing.\n"
        "Keep https://example.test/unit-testing?skill=unit-testing unchanged.\n"
        "Keep skills/unit-testing/SKILL.md and unit-testing.md unchanged.\n"
        "Keep C:\\skills\\unit-testing and [upstream](unit-testing) unchanged.\n"
        "Keep other-unit-testing and unit-testing-extra unchanged.\n"
    )
    target = tmp_path / "consumer"
    install(source, target, method, "codex", monkeypatch)
    text = (target / ".agents/skills/craft-unit-testing/SKILL.md").read_text()
    assert yaml.safe_load(text.split("---", 2)[1])["name"] == "craft-unit-testing"
    assert "Use craft-unit-testing." in text
    assert "Use `craft-unit-testing`, /craft-unit-testing and $craft-unit-testing." in text
    assert "https://example.test/unit-testing?skill=unit-testing" in text
    assert "skills/unit-testing/SKILL.md and unit-testing.md" in text
    assert "C:\\skills\\unit-testing and [upstream](unit-testing)" in text
    assert "other-unit-testing and unit-testing-extra" in text


def old_install(tmp_path):
    target = tmp_path / "consumer"
    shutil.copytree(Path(__file__).parent / "fixtures/native-skill-lock-v1", target)
    pinned = next((target / ".govkit/packs/sample").iterdir())
    source = tmp_path / "source"
    shutil.copytree(pinned, source)
    catalog = (load_pack(source),)
    return target, catalog


def test_original_lock_replays_offline_without_changing_bytes(tmp_path):
    target, _ = old_install(tmp_path)
    before = snapshot(target)
    result = verify_lock(target)
    assert result.ready, result.decisions
    assert snapshot(target) == before
    assert "name: help\n" in (target / ".agents/skills/sample-help/SKILL.md").read_text()


def test_explicit_old_lock_refresh_updates_native_identity_and_is_idempotent(tmp_path):
    target, catalog = old_install(tmp_path)
    path = target / ".govkit/profile.yaml"
    before = snapshot(target)
    preview = preview_install(path, target, catalog, govkit_version="0.21.1")
    assert snapshot(target) == before
    skill = next(
        op for op in preview.operations if op.path == ".agents/skills/sample-help/SKILL.md"
    )
    assert skill.action == "update"
    apply_install(preview)
    native = target / skill.path
    assert "name: sample-help\n" in native.read_text()
    lock = json.loads((target / ".govkit/pack-lock.json").read_text())
    assert lock["skill_rendering"] == "install-as-v1"
    assert verify_lock(target).ready
    after = snapshot(target)
    apply_install(preview_install(path, target, catalog, govkit_version="0.21.1"))
    assert snapshot(target) == after
    for relative, value in before.items():
        if relative.startswith(".govkit/packs/"):
            assert after[relative] == value


def test_old_native_user_edits_block_renderer_upgrade_without_writes(tmp_path):
    target, catalog = old_install(tmp_path)
    skill = target / ".agents/skills/sample-help/SKILL.md"
    skill.write_text(skill.read_text() + "\nUser instructions\n")
    before = snapshot(target)
    preview = preview_install(
        target / ".govkit/profile.yaml", target, catalog, govkit_version="0.21.1"
    )
    assert any(
        op.path.endswith("SKILL.md") and op.action == "protected" for op in preview.operations
    )
    with pytest.raises(PackError, match="protected"):
        apply_install(preview)
    assert snapshot(target) == before


@pytest.mark.parametrize("mode", [None, "future-unknown"])
def test_rendering_mode_cannot_be_changed_without_matching_resource_hashes(tmp_path, mode):
    target = tmp_path / "consumer"
    catalog = (load_pack(make_pack(tmp_path / "source", skills=True)),)
    path = write_profile(target, profile(["sample"]))
    apply_install(preview_install(path, target, catalog, govkit_version="0.21.1"))
    lock_path = target / ".govkit/pack-lock.json"
    lock = json.loads(lock_path.read_text())
    assert lock.pop("skill_rendering") == "install-as-v1"
    if mode is not None:
        lock["skill_rendering"] = mode
    lock_path.write_text(canonical_json(lock) + "\n")
    assert not verify_lock(target).ready


@pytest.mark.parametrize("method", ["extension", "pack"])
def test_one_word_name_changes_only_explicit_references(tmp_path, monkeypatch, method):
    source = make_pack(tmp_path / "sample", skills=True)
    skill = source / "skills/help/SKILL.md"
    skill.write_text(
        '---\nname: help\ndescription: "Need help? Invoke `help`."\n---\n'
        "Get help with `help`, /help or $help.\n"
    )
    target = tmp_path / "consumer"
    install(source, target, method, "codex", monkeypatch)
    text = (target / ".agents/skills/sample-help/SKILL.md").read_text()
    metadata = yaml.safe_load(text.split("---", 2)[1])
    assert metadata["name"] == "sample-help"
    assert metadata["description"] == "Need help? Invoke `sample-help`."
    assert "Get help with `sample-help`, /sample-help or $sample-help." in text


@pytest.mark.parametrize("method", ["extension", "pack"])
def test_duplicate_upstream_names_keep_each_native_identity(tmp_path, monkeypatch, method):
    source = SkillsFixture._bundle_skills_pack(
        tmp_path / "packs",
        "  - path: skills/unit-testing\n    install_as: craft-extra\n",
    )
    target = tmp_path / "consumer"
    install(source, target, method, "codex", monkeypatch)
    for name in ("craft-unit-testing", "craft-extra"):
        text = (target / ".agents/skills" / name / "SKILL.md").read_text()
        assert yaml.safe_load(text.split("---", 2)[1])["name"] == name
