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


def test_accelerator_plan_skill_links_resolve_from_the_document_to_real_sections():
    plan = ROOT / "plans/02_GOVERNANCE_ACCELERATOR_PLAN.md"
    links = re.findall(r"\[[^\]]+\]\(([^)]+/SKILL\.md#[^)]+)\)", plan.read_text())
    assert links, "The plan must link its preserved skill contract to the implementation"
    for link in links:
        relative, fragment = link.split("#", 1)
        target = (plan.parent / relative).resolve()
        assert target.is_file(), f"{plan.name}: broken relative skill link {link}"
        headings = re.findall(r"^#{1,6} (.+)$", target.read_text(), re.MULTILINE)
        anchors = {
            re.sub(r"[^\w -]", "", heading.lower()).replace(" ", "-") for heading in headings
        }
        assert fragment in anchors, f"{plan.name}: missing skill section {link}"
