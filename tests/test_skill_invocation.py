"""Explicit invocation survives both native installers without changing pins."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from cli import paths
from cli.agent_layout import AGENT_LAYOUTS
from cli.cmd_extension import cmd_extension_add
from cli.native_skills import render_native_skill
from cli.pack_loading import PackError, load_pack
from cli.pack_store import apply_install, preview_install, verify_lock
from tests.test_capability_packs import make_pack
from tests.test_cmd_extension import _add_args
from tests.test_native_skill_installation import install
from tests.test_pack_store import snapshot


@pytest.mark.parametrize("config", [b"policy: [", b"\xff", b"null", b"[]", b"policy: false"])
def test_unrecognized_metadata_remains_unchanged_without_inventing_policy(config):
    skill = b"---\nname: sample-help\ndescription: Help\n---\nHelp\n"
    files = {"SKILL.md": skill, "agents/openai.yaml": config, "references/guide.md": b"Guide"}

    rendered = render_native_skill(files, "sample-help", {}, "claude-code")

    assert rendered == files


def test_default_prompt_aliases_preserve_unrelated_metadata_and_self_identity():
    skill = b"---\nname: help\ndescription: Help\n---\n"
    config = b'interface:\n  default_prompt: "Use $help or $sibling-skill."\n  icon_small: "./assets/help.png"\npolicy:\n  allow_implicit_invocation: false\ndependencies:\n  tools: [{type: mcp, value: example}]\n'
    original = yaml.safe_load(config)

    rendered = render_native_skill(
        {"SKILL.md": skill, "agents/openai.yaml": config},
        "sample-help",
        {"sibling-skill": "sample-sibling-skill"},
        "codex",
    )

    updated = yaml.safe_load(rendered["agents/openai.yaml"])
    expected = {
        **original,
        "interface": {
            **original["interface"],
            "default_prompt": "Use $sample-help or $sample-sibling-skill.",
        },
    }
    assert updated == expected
    assert "disable-model-invocation" not in yaml.safe_load(
        rendered["SKILL.md"].decode().split("---", 2)[1]
    )


@pytest.mark.parametrize("method", ["extension", "pack"])
@pytest.mark.parametrize("agent", AGENT_LAYOUTS)
def test_otter_explicit_policy_reaches_native_agent(tmp_path, monkeypatch, method, agent):
    source = paths.EXTENSION_PACKS_DIR / "otter-skills"
    before = snapshot(source)
    target = tmp_path / "consumer"

    pinned = install(source, target, method, agent, monkeypatch)

    native = target / AGENT_LAYOUTS[agent].skills_dir
    skill = native / "otter-user-pov-sliced-stories"
    metadata = yaml.safe_load((skill / "SKILL.md").read_text().split("---", 2)[1])
    config = yaml.safe_load((skill / "agents/openai.yaml").read_text())
    assert config["policy"]["allow_implicit_invocation"] is False
    assert "$otter-user-pov-sliced-stories" in config["interface"]["default_prompt"]
    assert metadata.get("disable-model-invocation", False) is (agent != "codex")
    assert metadata["name"] == skill.name
    ordinary = native / "otter-story-splitting-for-delivery/SKILL.md"
    assert "disable-model-invocation" not in yaml.safe_load(ordinary.read_text().split("---", 2)[1])
    for item in load_pack(source).files:
        assert (pinned / item.path).read_bytes() == item.content
    assert snapshot(source) == before


@pytest.mark.parametrize("method", ["extension", "pack"])
@pytest.mark.parametrize("agent", AGENT_LAYOUTS)
@pytest.mark.parametrize("policy", ["false", "true", '"false"', "null", "0", "missing"])
def test_only_explicit_boolean_false_disables_automatic_invocation(
    tmp_path, monkeypatch, method, agent, policy
):
    source = make_pack(tmp_path / "sample", skills=True)
    config = source / "skills/help/agents/openai.yaml"
    config.parent.mkdir()
    config.write_text(
        'interface:\n  default_prompt: "Use $help to start."\n  display_name: "Help"\n'
        + ("" if policy == "missing" else f"policy:\n  allow_implicit_invocation: {policy}\n")
    )
    target = tmp_path / "consumer"

    install(source, target, method, agent, monkeypatch)

    native = target / AGENT_LAYOUTS[agent].skills_dir / "sample-help"
    metadata = yaml.safe_load((native / "SKILL.md").read_text().split("---", 2)[1])
    assert metadata.get("disable-model-invocation", False) is (
        policy == "false" and agent != "codex"
    )
    installed_config = yaml.safe_load((native / "agents/openai.yaml").read_text())
    assert installed_config["interface"] == {
        "default_prompt": "Use $sample-help to start.",
        "display_name": "Help",
    }
    assert installed_config.get("policy") == yaml.safe_load(config.read_text()).get("policy")


def previous_install(tmp_path):
    target = tmp_path / "consumer"
    shutil.copytree(Path(__file__).parent / "fixtures/native-skill-rendering-v2", target)
    pinned = next((target / ".govkit/packs/sample").iterdir())
    return target, (load_pack(pinned),)


def test_v2_lock_replays_original_policy_bytes_without_writes(tmp_path):
    target, _ = previous_install(tmp_path)
    before = snapshot(target)

    result = verify_lock(target)

    assert result.ready, result.decisions
    assert snapshot(target) == before
    assert (
        "disable-model-invocation"
        not in (target / ".claude/skills/sample-help/SKILL.md").read_text()
    )


def test_explicit_refresh_maps_policy_and_preserves_pinned_sources(tmp_path):
    target, catalog = previous_install(tmp_path)
    before = snapshot(target)
    proposal = preview_install(
        target / ".govkit/profile.yaml", target, catalog, govkit_version="0.21.1"
    )

    apply_install(proposal)

    native = target / ".claude/skills/sample-help/SKILL.md"
    assert yaml.safe_load(native.read_text().split("---", 2)[1])["disable-model-invocation"] is True
    lock = json.loads((target / ".govkit/pack-lock.json").read_text())
    assert lock["skill_rendering"] == "install-as-v3"
    assert verify_lock(target).ready
    after = snapshot(target)
    for relative in before:
        if relative.startswith(".govkit/packs/"):
            assert after[relative] == before[relative]


@pytest.mark.parametrize("filename", ["SKILL.md", "agents/openai.yaml"])
def test_user_edits_block_policy_refresh_without_writes(tmp_path, filename):
    target, catalog = previous_install(tmp_path)
    edited = target / ".claude/skills/sample-help" / filename
    edited.write_text(edited.read_text() + "\n# Team customization\n")
    before = snapshot(target)
    proposal = preview_install(
        target / ".govkit/profile.yaml", target, catalog, govkit_version="0.21.1"
    )

    with pytest.raises(PackError, match="protected"):
        apply_install(proposal)

    assert snapshot(target) == before


@pytest.mark.parametrize("agent", AGENT_LAYOUTS)
def test_reapplying_policy_install_preserves_bytes_and_mtimes(tmp_path, monkeypatch, agent):
    source = paths.EXTENSION_PACKS_DIR / "otter-skills"
    target = tmp_path / "consumer"
    install(source, target, "pack", agent, monkeypatch)
    before = snapshot(target)
    proposal = preview_install(
        target / ".govkit/profile.yaml", target, (load_pack(source),), govkit_version="0.21.1"
    )

    apply_install(proposal)

    assert snapshot(target) == before


@pytest.mark.parametrize("force", [False, True])
def test_legacy_policy_refresh_requires_explicit_force(tmp_path, monkeypatch, force):
    source = paths.EXTENSION_PACKS_DIR / "otter-skills"
    target = tmp_path / "consumer"
    install(source, target, "extension", "claude-code", monkeypatch)
    native = target / ".claude/skills/otter-user-pov-sliced-stories/SKILL.md"
    native.write_text("Team-owned instructions\n")
    before = snapshot(target)

    if force:
        cmd_extension_add(_add_args("otter-skills", target, force=True))
        assert (
            yaml.safe_load(native.read_text().split("---", 2)[1])["disable-model-invocation"]
            is True
        )
    else:
        with pytest.raises(SystemExit):
            cmd_extension_add(_add_args("otter-skills", target))
        assert snapshot(target) == before
