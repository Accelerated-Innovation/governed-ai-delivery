"""The dev-time sync retains supported native metadata at the exact pin."""

import shutil
from pathlib import Path

import pytest

from scripts import sync_otter_skills as syncer
from tests.test_pack_store import snapshot


def arrange_sync(tmp_path, monkeypatch):
    upstream = tmp_path / "upstream"
    plugin = upstream / syncer.UPSTREAM_PLUGIN
    skill = plugin / "skills/sample"
    (skill / "agents").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: sample\ndescription: Sample\n---\n")
    metadata = b'interface:\r\n  default_prompt: "Use $sample."\r\npolicy:\r\n  allow_implicit_invocation: false\r\n'
    (skill / "agents/openai.yaml").write_bytes(metadata)
    (skill / "agents/other.yaml").write_text("Unrelated configuration\n")
    for name in ("LICENSE", "NOTICE"):
        (plugin / name).write_text(name)
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "README.md").write_text("<!-- sync:provenance -->\nold\n<!-- /sync:provenance -->\n")
    (pack / "skills/existing").mkdir(parents=True)
    (pack / "skills/existing/SKILL.md").write_text("Existing vendored content\n")
    (pack / "manifest.yaml").write_text("Existing manifest\n")
    sha = "a" * 40

    def git(args, cwd=None):
        if args[1] == "clone":
            # Git preserves symlinks; dereferencing here would hide the defect.
            shutil.copytree(upstream, args[-1], symlinks=True)
        return sha if args[1] == "rev-parse" else ""

    monkeypatch.setattr(syncer, "_run", git)
    monkeypatch.setattr(syncer, "PACK_DIR", pack)
    return upstream, pack, sha, metadata


def test_sync_preserves_openai_bytes_and_excludes_other_agent_configs(tmp_path, monkeypatch):
    upstream, pack, sha, metadata = arrange_sync(tmp_path, monkeypatch)
    skill = upstream / syncer.UPSTREAM_PLUGIN / "skills/sample"

    syncer.sync(sha, "0.1.6")

    config = pack / "skills/sample/agents/openai.yaml"
    assert config.read_bytes() == metadata
    assert list(config.parent.iterdir()) == [config]
    assert (pack / "skills/sample/SKILL.md").read_bytes() == (skill / "SKILL.md").read_bytes()
    assert sha in (pack / "manifest.yaml").read_text()


@pytest.mark.parametrize(
    "relative",
    [
        "plugins",
        "plugins/otter-skills",
        "plugins/otter-skills/skills",
        "plugins/otter-skills/skills/sample",
        "plugins/otter-skills/skills/sample/agents",
        "plugins/otter-skills/skills/sample/agents/openai.yaml",
        "plugins/otter-skills/skills/sample/SKILL.md",
        "plugins/otter-skills/LICENSE",
        "plugins/otter-skills/NOTICE",
    ],
    ids=[
        "plugins-parent",
        "plugin",
        "skills-parent",
        "skill",
        "agents-parent",
        "openai",
        "skill-md",
        "license",
        "notice",
    ],
)
def test_symlinked_upstream_input_is_rejected_before_changing_vendored_pack(
    tmp_path, monkeypatch, relative
):
    upstream, pack, sha, _ = arrange_sync(tmp_path, monkeypatch)
    source = upstream / relative
    outside = tmp_path / "host-content"
    if source.is_dir():
        shutil.copytree(source, outside)
        shutil.rmtree(source)
    else:
        shutil.copyfile(source, outside)
        source.unlink()
    source.symlink_to(outside, target_is_directory=outside.is_dir())
    before = snapshot(pack)

    with pytest.raises(SystemExit, match="symlink"):
        syncer.sync(sha, "0.1.6")

    assert snapshot(pack) == before


@pytest.mark.parametrize("kind", ["external-file", "external-directory", "broken", "internal"])
def test_symlinked_supporting_resources_are_rejected_without_partial_refresh(
    tmp_path, monkeypatch, kind
):
    upstream, pack, sha, _ = arrange_sync(tmp_path, monkeypatch)
    skill = upstream / syncer.UPSTREAM_PLUGIN / "skills/sample"
    host = tmp_path / "host"
    host.mkdir()
    (host / "private.txt").write_text("Host content must not be vendored\n")
    targets = {
        "external-file": host / "private.txt",
        "external-directory": host,
        "broken": host / "absent",
        "internal": Path("SKILL.md"),
    }
    destination = targets[kind]
    (skill / "reference").symlink_to(destination, target_is_directory=kind == "external-directory")
    before = snapshot(pack)

    with pytest.raises(SystemExit, match="symlink"):
        syncer.sync(sha, "0.1.6")

    assert snapshot(pack) == before
