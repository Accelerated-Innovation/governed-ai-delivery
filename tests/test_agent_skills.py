"""Increment 3 — parity test for the new Section 2.5 (Extension Discovery)
added to all architecture-preflight SKILL.md files across the three agents
(claude-code, codex, copilot) and both layers (backend, ui).

Per [[feedback_agent_parity]], all 3 agents must ship identical rules and
skills. This test pins that invariant for the new section."""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATHS = [
    REPO_ROOT / "agents" / agent / "skills" / layer / "architecture-preflight" / "SKILL.md"
    for agent in ("claude-code", "codex", "copilot")
    for layer in ("backend", "ui")
]

SECTION_HEADING = "## 2.6 Extension Discovery"


def _extract_section(text: str, start_heading: str) -> str:
    """Extract from start_heading through (but not including) the next `## ` heading.
    A trailing horizontal-rule line (`---`) is stripped so the comparison ignores
    the layer-specific separator style. Returns '' when start_heading is missing."""
    start = text.find(start_heading)
    if start == -1:
        return ""
    # find next ## heading after the section start (search past the heading itself)
    search_from = start + len(start_heading)
    end = text.find("\n## ", search_from)
    section = text[start:] if end == -1 else text[start:end + 1]
    # Strip trailing horizontal-rule separators (UI files use `---` between sections; backend does not)
    lines = section.rstrip().splitlines()
    while lines and lines[-1].strip() == "---":
        lines.pop()
    return "\n".join(lines).rstrip()


@pytest.mark.parametrize("skill_path", SKILL_PATHS, ids=lambda p: f"{p.parent.parent.parent.parent.name}/{p.parent.parent.name}")
def test_section_25_present(skill_path: Path):
    text = skill_path.read_text(encoding="utf-8")
    assert SECTION_HEADING in text, (
        f"{skill_path.relative_to(REPO_ROOT)} missing '{SECTION_HEADING}'"
    )


@pytest.mark.parametrize("skill_path", SKILL_PATHS, ids=lambda p: f"{p.parent.parent.parent.parent.name}/{p.parent.parent.name}")
def test_section_25_mentions_required_concepts(skill_path: Path):
    text = skill_path.read_text(encoding="utf-8")
    section = _extract_section(text, SECTION_HEADING)
    required_phrases = [
        "extensions/*/manifest.yaml",   # discovery scan
        "applies_to",                   # applicability check
        "capabilities",
        "relates_to",                   # conflict-resolution model
        "extends",
        "supersedes",
        "ADR",                          # escalation
    ]
    missing = [p for p in required_phrases if p not in section]
    assert not missing, (
        f"{skill_path.relative_to(REPO_ROOT)} Section 2.5 missing phrases: {missing}"
    )


def test_section_25_parity_across_all_skills():
    """The Section 2.5 block must be byte-identical across all 6 SKILL.md files.
    Enforces [[feedback_agent_parity]] for the new section."""
    sections = {
        skill_path: _extract_section(
            skill_path.read_text(encoding="utf-8"),
            SECTION_HEADING,
        )
        for skill_path in SKILL_PATHS
    }
    canonical = sections[SKILL_PATHS[0]]
    mismatches = [
        str(path.relative_to(REPO_ROOT))
        for path, section in sections.items()
        if section != canonical
    ]
    assert not mismatches, (
        f"Section 2.5 must be identical across all SKILL.md files; mismatches: {mismatches}"
    )


# ---------------------------------------------------------------------------
# Data-native preflight sections (hardening plan Increment 6)
# ---------------------------------------------------------------------------

BACKEND_PREFLIGHT_PATHS = [
    REPO_ROOT / "agents" / agent / "skills" / "backend" / "architecture-preflight" / "SKILL.md"
    for agent in ("claude-code", "codex", "copilot")
]
BACKEND_SPEC_PLANNING_PATHS = [
    REPO_ROOT / "agents" / agent / "skills" / "backend" / "spec-planning" / "SKILL.md"
    for agent in ("claude-code", "codex", "copilot")
]

DATA_IMPACT_HEADING = "## 3.7 Data Impact"
DATA_IMPACT_SUBSECTIONS = [
    "### Pipeline Impact",
    "### Contract Impact",
    "### PII Impact",
    "### Lineage Impact",
]
SPEC_PLANNING_DATA_HEADING = "### Data projects"


@pytest.mark.parametrize(
    "skill_path", BACKEND_PREFLIGHT_PATHS, ids=lambda p: p.parent.parent.parent.parent.name,
)
def test_preflight_has_data_impact_block(skill_path: Path):
    """Data installs receive the backend preflight source; it must carry the
    data-native impact sections (backend/UI reports skip them)."""
    text = skill_path.read_text(encoding="utf-8")
    assert DATA_IMPACT_HEADING in text
    section = _extract_section(text, DATA_IMPACT_HEADING)
    missing = [s for s in DATA_IMPACT_SUBSECTIONS if s not in section]
    assert not missing, f"{skill_path.relative_to(REPO_ROOT)} missing: {missing}"


def test_data_impact_block_parity_across_agents():
    sections = {
        p: _extract_section(p.read_text(encoding="utf-8"), DATA_IMPACT_HEADING)
        for p in BACKEND_PREFLIGHT_PATHS
    }
    canonical = sections[BACKEND_PREFLIGHT_PATHS[0]]
    mismatches = [
        str(p.relative_to(REPO_ROOT)) for p, s in sections.items() if s != canonical
    ]
    assert not mismatches, f"Data Impact block must be identical: {mismatches}"


@pytest.mark.parametrize(
    "skill_path", BACKEND_SPEC_PLANNING_PATHS, ids=lambda p: p.parent.parent.parent.parent.name,
)
def test_spec_planning_has_data_projects_note(skill_path: Path):
    """spec-planning must tell data projects which NFR categories to tag and
    that data eval criteria are deterministic (no LLM evaluator tools)."""
    text = skill_path.read_text(encoding="utf-8")
    assert SPEC_PLANNING_DATA_HEADING in text
    section = _extract_section(text, SPEC_PLANNING_DATA_HEADING)
    for phrase in ("freshness", "quality", "pii", "lineage", "cost", "deterministic"):
        assert phrase in section, (skill_path.relative_to(REPO_ROOT), phrase)


def test_spec_planning_data_note_parity_across_agents():
    sections = {
        p: _extract_section(p.read_text(encoding="utf-8"), SPEC_PLANNING_DATA_HEADING)
        for p in BACKEND_SPEC_PLANNING_PATHS
    }
    canonical = sections[BACKEND_SPEC_PLANNING_PATHS[0]]
    mismatches = [
        str(p.relative_to(REPO_ROOT)) for p, s in sections.items() if s != canonical
    ]
    assert not mismatches, f"Data projects note must be identical: {mismatches}"


def test_starter_data_preflight_mirrors_skill_sections():
    """The worked example must be exactly what the shipped skill produces:
    every data-impact section the skill prescribes appears in the starter,
    and the starter uses the skill's report section set."""
    starter = (
        REPO_ROOT / "features" / "starter_data" / "architecture_preflight.md"
    ).read_text(encoding="utf-8")
    for heading in DATA_IMPACT_SUBSECTIONS:
        assert heading in starter, heading
    for heading in (
        "## 1. Summary", "## 2. Standards Check", "## 2.6 Extension Discovery",
        "## 3. Boundary Analysis", "## 3.5 Repository Scope Analysis",
        "## 3.7 Data Impact", "## 4. ADR Decision", "## 5. Tests Required",
        "## 6. Risks & Unknowns",
    ):
        assert heading in starter, heading
