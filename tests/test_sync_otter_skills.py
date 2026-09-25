"""The dev-time sync retains supported native metadata at the exact pin."""

import shutil

from scripts import sync_otter_skills as syncer


def test_sync_preserves_openai_bytes_and_excludes_other_agent_configs(tmp_path, monkeypatch):
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
    sha = "a" * 40

    def git(args, cwd=None):
        if args[1] == "clone":
            shutil.copytree(upstream, args[-1])
        return sha if args[1] == "rev-parse" else ""

    monkeypatch.setattr(syncer, "_run", git)
    monkeypatch.setattr(syncer, "PACK_DIR", pack)

    syncer.sync(sha, "0.1.6")

    config = pack / "skills/sample/agents/openai.yaml"
    assert config.read_bytes() == metadata
    assert list(config.parent.iterdir()) == [config]
    assert (pack / "skills/sample/SKILL.md").read_bytes() == (skill / "SKILL.md").read_bytes()
    assert sha in (pack / "manifest.yaml").read_text()
