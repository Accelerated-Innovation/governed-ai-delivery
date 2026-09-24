"""Public tutorial skill references must resolve to real manifest selections."""

import re
from pathlib import Path

import pytest

from cli.manifest import load_manifest, resolve_variant_files

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("agent", ["claude-code", "codex", "copilot"])
def test_tutorial_skill_references_are_shipped_by_each_agent(agent):
    tutorial = (ROOT / "GOVKIT_TUTORIAL.md").read_text()
    referenced = set(re.findall(r"`/?(govkit-[a-z-]+)`", tutorial))
    selected = set()
    manifest = load_manifest(agent)
    for kind in manifest["variants"]["type"]:
        for level in ("3", "4", "5"):
            for provider in ("github", "azure"):
                files, _, _ = resolve_variant_files(
                    manifest, {"type": kind, "level": level, "ci": provider}
                )
                for entry in files:
                    source = ROOT / "agents" / agent / entry["src"]
                    if source.is_dir() and (source / "SKILL.md").is_file():
                        selected.add(Path(entry["dest"]).name)
    assert referenced, "Tutorial should identify the real legacy skills"
    assert referenced <= selected, (
        f"{agent}: tutorial names unshipped skills {referenced - selected}"
    )


def test_tutorial_inventory_paths_cover_the_real_codex_skill_sources():
    text = (ROOT / "GOVKIT_TUTORIAL.md").read_text()
    declared = set(re.findall(r"`(agents/codex/skills/[^`]+/SKILL.md)`", text))
    actual = {
        p.relative_to(ROOT).as_posix() for p in (ROOT / "agents/codex/skills").rglob("SKILL.md")
    }
    assert declared == actual, {"missing": actual - declared, "unshipped": declared - actual}
