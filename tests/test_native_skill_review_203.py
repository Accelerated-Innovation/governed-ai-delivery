"""PR 203: resource link destinations survive native alias rendering."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from cli.pack_loading import PackError, load_pack
from cli.pack_store import apply_install, preview_install, verify_lock
from cli.schema_validation import canonical_json
from tests.test_cmd_extension import TestExtensionAddSkills as SkillsFixture
from tests.test_native_skill_installation import install
from tests.test_pack_store import snapshot


@pytest.mark.parametrize("method", ["extension", "pack"])
@pytest.mark.parametrize(
    "definition",
    [
        '[guide]: unit-testing "Guide"',
        '[guide]: <unit-testing> "Guide"',
        "   [guide]:\tunit-testing",
        "[guide]:\n  unit-testing",
        "> [guide]: unit-testing",
        "- [guide]: unit-testing",
        "[guide]: https://example.test/unit-testing",
    ],
    ids=["bare", "angle", "indent", "next-line", "quote", "list", "url-control"],
)
def test_reference_destinations_stay_literal_while_visible_names_render(
    tmp_path, monkeypatch, method, definition
):
    source = SkillsFixture._bundle_skills_pack(tmp_path / "packs")
    skill = source / "skills/unit-testing/SKILL.md"
    skill.write_text(
        "---\nname: unit-testing\ndescription: Use unit-testing.\n---\n"
        "Use [unit-testing][guide] and `unit-testing`.\n\n" + definition + "\n"
    )
    resource = skill.parent / "unit-testing"
    resource.write_text("Unrenamed local resource\n")
    before = snapshot(source)
    target = tmp_path / "consumer"

    install(source, target, method, "codex", monkeypatch)

    native = target / ".agents/skills/craft-unit-testing/SKILL.md"
    text = native.read_text()
    assert definition in text
    assert "Use [craft-unit-testing][guide] and `craft-unit-testing`." in text
    metadata = yaml.safe_load(text.split("---", 2)[1])
    assert metadata == {"name": "craft-unit-testing", "description": "Use craft-unit-testing."}
    assert (native.parent / "unit-testing").read_bytes() == resource.read_bytes()
    assert snapshot(source) == before


def previous_rendering(tmp_path):
    target = tmp_path / "consumer"
    shutil.copytree(Path(__file__).parent / "fixtures/native-skill-rendering-v1", target)
    pinned = next((target / ".govkit/packs/craft-pack").iterdir())
    source = tmp_path / "source"
    shutil.copytree(pinned, source)
    return target, (load_pack(source),)


def test_pre_fix_rendering_lock_still_replays_without_writes(tmp_path):
    target, _ = previous_rendering(tmp_path)
    before = snapshot(target)

    result = verify_lock(target)

    assert result.ready, result.decisions
    assert snapshot(target) == before
    text = (target / ".agents/skills/craft-unit-testing/SKILL.md").read_text()
    assert "[guide]: craft-unit-testing" in text


def test_explicit_refresh_repairs_reference_destination_and_preserves_pins(tmp_path):
    target, catalog = previous_rendering(tmp_path)
    before = snapshot(target)
    source = target / ".govkit/profile.yaml"
    proposal = preview_install(source, target, catalog, govkit_version="0.21.1")
    assert snapshot(target) == before

    apply_install(proposal)

    native = target / ".agents/skills/craft-unit-testing/SKILL.md"
    assert "[guide]: unit-testing\n" in native.read_text()
    assert "Use [craft-unit-testing][guide]." in native.read_text()
    assert (native.parent / "unit-testing").is_file()
    lock = json.loads((target / ".govkit/pack-lock.json").read_text())
    assert lock["skill_rendering"] == "install-as-v3"
    assert verify_lock(target).ready
    after = snapshot(target)
    for relative, value in before.items():
        if relative.startswith(".govkit/packs/"):
            assert after[relative] == value
    apply_install(preview_install(source, target, catalog, govkit_version="0.21.1"))
    assert snapshot(target) == after


def test_user_edits_block_reference_renderer_refresh_without_writes(tmp_path):
    target, catalog = previous_rendering(tmp_path)
    native = target / ".agents/skills/craft-unit-testing/SKILL.md"
    native.write_text(native.read_text() + "\nUser instructions\n")
    before = snapshot(target)
    proposal = preview_install(
        target / ".govkit/profile.yaml", target, catalog, govkit_version="0.21.1"
    )

    with pytest.raises(PackError, match="protected"):
        apply_install(proposal)

    assert snapshot(target) == before


def test_original_mode_cannot_replay_corrected_resource_hashes(tmp_path):
    target, catalog = previous_rendering(tmp_path)
    apply_install(
        preview_install(target / ".govkit/profile.yaml", target, catalog, govkit_version="0.21.1")
    )
    lock_path = target / ".govkit/pack-lock.json"
    document = json.loads(lock_path.read_text())
    assert document["skill_rendering"] == "install-as-v3"
    document["skill_rendering"] = "install-as-v1"
    lock_path.write_text(canonical_json(document) + "\n")

    result = verify_lock(target)

    assert not result.ready
