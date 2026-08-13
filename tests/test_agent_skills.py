"""Increment 3 — parity test for the new Section 2.5 (Extension Discovery)
added to all architecture-preflight SKILL.md files across the three agents
(claude-code, codex, copilot) and both layers (backend, ui).

Per [[feedback_agent_parity]], all 3 agents must ship identical rules and
skills. This test pins that invariant for the new section."""

import re
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


UI_SKILLS = [
    REPO_ROOT / "agents" / agent / "skills" / "ui" / skill / "SKILL.md"
    for agent in ("claude-code", "codex", "copilot")
    for skill in ("adr-author", "architecture-preflight", "spec-planning", "implementation-plan")
]


@pytest.mark.parametrize(
    "skill_path", UI_SKILLS,
    ids=lambda p: f"{p.parents[3].name}/{p.parent.name}",
)
def test_ui_skills_enforce_nextjs_boundary_and_design(skill_path: Path):
    text = skill_path.read_text(encoding="utf-8")
    assert "database" in text.lower()
    if skill_path.parent.name != "adr-author":
        assert "design.md" in text


@pytest.mark.parametrize(
    "skill_path",
    [p for p in UI_SKILLS if p.parent.name != "adr-author"],
    ids=lambda p: f"{p.parents[3].name}/{p.parent.name}",
)
def test_ui_skills_cover_prototype_references(skill_path: Path):
    """UI_DOCS_PARITY_AND_DESIGN_REFERENCES_PLAN.md increment 4: the
    planning skills inventory prototypes (including AI-generated HTML
    prototypes) alongside screenshots/mockups, as advisory references
    whose code is never imported into src/."""
    text = skill_path.read_text(encoding="utf-8")
    assert "prototype" in text.lower(), (
        f"{skill_path.parent.name} must cover prototype references"
    )


@pytest.mark.parametrize(
    "skill", ("adr-author", "architecture-preflight", "spec-planning", "implementation-plan"),
)
def test_ui_nextjs_skill_content_parity(skill: str):
    texts = [
        (
            REPO_ROOT / "agents" / agent / "skills" / "ui" / skill / "SKILL.md"
        ).read_text(encoding="utf-8")
        for agent in ("claude-code", "codex", "copilot")
    ]
    assert all(text == texts[0] for text in texts[1:]), (
        f"{skill} drifted across agents"
    )


# ---------------------------------------------------------------------------
# Multi-service planning — #86 increment 3
# ---------------------------------------------------------------------------

PLANNING_SKILL_PATHS = [
    REPO_ROOT / "agents" / agent / "skills" / "backend" / skill / "SKILL.md"
    for agent in ("claude-code", "codex", "copilot")
    # fix-record plans a defect the way spec-planning plans a feature: it scopes
    # to one service, reads the recorded architecture rather than asserting one,
    # and must not guess. Registering it here inherits those guarantees instead
    # of restating them in a parallel test.
    for skill in ("spec-planning", "implementation-plan", "fix-record")
]

SERVICES_HEADING = "## Multi-service repos"


def _planning_id(p: Path) -> str:
    return f"{p.parent.parent.parent.parent.name}/{p.parent.name}"


def test_the_planning_skill_set_is_what_we_think_it_is():
    """Nine files: three planning skills across three agents. If a path moved,
    the parametrized tests below would silently cover fewer files."""
    assert len(PLANNING_SKILL_PATHS) == 9
    missing = [p for p in PLANNING_SKILL_PATHS if not p.is_file()]
    assert not missing, f"planning skills not found: {missing}"


@pytest.mark.parametrize("skill_path", PLANNING_SKILL_PATHS, ids=_planning_id)
def test_planning_skills_have_a_multi_service_section(skill_path: Path):
    text = skill_path.read_text(encoding="utf-8")
    assert SERVICES_HEADING in text, (
        f"{skill_path.relative_to(REPO_ROOT)} missing '{SERVICES_HEADING}'"
    )


@pytest.mark.parametrize("skill_path", PLANNING_SKILL_PATHS, ids=_planning_id)
def test_multi_service_section_tells_the_agent_to_ask(skill_path: Path):
    """#86's third question: several services, and the request names none.
    The answer is to ask, not to guess and not to plan across all of them."""
    section = _extract_section(skill_path.read_text(encoding="utf-8"), SERVICES_HEADING)
    required = [
        "architecture.services",   # the field to read
        "architecture.source_root",  # the single-service fallback
        "root",                    # each service carries one
        "ask",                     # the required behaviour when ambiguous
    ]
    missing = [p for p in required if p not in section]
    assert not missing, (
        f"{skill_path.relative_to(REPO_ROOT)} multi-service section missing: {missing}"
    )


@pytest.mark.parametrize("skill_path", PLANNING_SKILL_PATHS, ids=_planning_id)
def test_multi_service_section_forbids_guessing(skill_path: Path):
    section = _extract_section(
        skill_path.read_text(encoding="utf-8"), SERVICES_HEADING,
    ).lower()
    assert "do not guess" in section
    assert "do not plan across" in section


@pytest.mark.parametrize("skill_path", PLANNING_SKILL_PATHS, ids=_planning_id)
def test_multi_service_section_scopes_output_paths_to_the_service(skill_path: Path):
    """Naming the service is not enough — the plan's file paths have to land
    inside it, or the agent writes `services/x.py` into a repo where that
    folder only exists as `src/orders/services/`."""
    section = _extract_section(skill_path.read_text(encoding="utf-8"), SERVICES_HEADING)
    assert "src/orders/services/" in section, (
        f"{skill_path.relative_to(REPO_ROOT)} does not show a path scoped to a service root"
    )


def test_multi_service_section_parity_across_agents():
    """Byte-identical across all six files, per [[feedback_agent_parity]]."""
    sections = {
        _planning_id(p): _extract_section(p.read_text(encoding="utf-8"), SERVICES_HEADING)
        for p in PLANNING_SKILL_PATHS
    }
    assert all(sections.values()), (
        f"empty section in: {[k for k, v in sections.items() if not v]}"
    )
    distinct = set(sections.values())
    assert len(distinct) == 1, (
        "multi-service section differs across agents:\n"
        + "\n".join(f"--- {k} ---\n{v}" for k, v in sections.items())
    )


def test_ui_planning_skills_do_not_gain_the_section():
    """UI installs have no service packages — #86 puts them out of scope, and
    a section telling a UI agent to pick a service would be noise."""
    ui_paths = [
        REPO_ROOT / "agents" / agent / "skills" / "ui" / skill / "SKILL.md"
        for agent in ("claude-code", "codex", "copilot")
        for skill in ("spec-planning", "implementation-plan")
    ]
    present = [p for p in ui_paths if p.is_file() and SERVICES_HEADING in p.read_text(encoding="utf-8")]
    assert not present, f"UI skills carry the multi-service section: {present}"


# ---------------------------------------------------------------------------
# Planning skills describe the project's own architecture — #119
# ---------------------------------------------------------------------------

# Tokens that assert a specific architecture as this project's, rather than
# reading the one govkit detected. Matched case-insensitively on word
# boundaries, so `Hexagonal architecture`, `HEXAGONAL` and a bare `hexagonal`
# are caught alongside the exact phrasing #119 removed.
#
# The bare style ids are here because they are what `architecture.style`
# holds: a skill that names one has decided the answer instead of reading it.
# `clean` and `layered` are ordinary English, so banning them costs the
# occasional reworded sentence — accepted deliberately. A false positive is
# loud and fixable in one edit; a false negative is silent, and this whole
# check exists because a silent one shipped.
#
# `ports/inbound` and `ports/outbound` are hexagonal-only package names.
# A bare `services/` deliberately is **not** banned: the multi-service
# section legitimately uses `services/pricing.py` to show a path scoped to a
# service root, which is a claim about paths, not about this repo's layers.
_STYLE_ASSERTIONS = (
    "hexagonal",
    "clean",
    "layered",
    "dbt-layered",
    "ports/inbound",
    "ports/outbound",
)

_STYLE_ASSERTION_RE = re.compile(
    "|".join(rf"(?<![\w-]){re.escape(token)}(?![\w-])" for token in _STYLE_ASSERTIONS),
    re.IGNORECASE,
)


def _prose(text: str) -> str:
    """`text` with fenced code blocks removed.

    Same split `tests/test_stack_neutral_docs.py` makes, for the same reason:
    a rule must be architecture-neutral, while an *example* may be concrete.
    A fenced snippet showing `style: hexagonal` documents the file format a
    skill has to read; the same words in prose assert what this repo is.
    """
    kept, in_fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            kept.append(line)
    return "\n".join(kept)


@pytest.mark.parametrize("skill_path", PLANNING_SKILL_PATHS, ids=_planning_id)
def test_planning_skill_reads_the_recorded_architecture(skill_path: Path):
    """govkit detects the style and writes the layer folders down. A planning
    skill that hardcodes folder names instead plans against packages the repo
    may not have."""
    text = skill_path.read_text(encoding="utf-8")
    for token in (".govkit/skill_context.yaml", "architecture.layers"):
        assert token in text, (
            f"{skill_path.relative_to(REPO_ROOT)} never references {token}"
        )


@pytest.mark.parametrize("skill_path", PLANNING_SKILL_PATHS, ids=_planning_id)
def test_planning_skill_asserts_no_architecture_style(skill_path: Path):
    """The same six files ship to every backend stack and every layout. A
    repo govkit reads as `clean` gets `Presentation/`, `Application/` and
    `Infrastructure/`; one it reads as `dbt-layered` gets `models/staging/`.
    Telling either agent to produce `ports/inbound/` names folders that do
    not exist."""
    offenders = sorted({
        m.group(0).lower()
        for m in _STYLE_ASSERTION_RE.finditer(_prose(skill_path.read_text(encoding="utf-8")))
    })
    assert not offenders, (
        f"{skill_path.relative_to(REPO_ROOT)} asserts an architecture style "
        f"instead of reading the detected one: {offenders}. Read "
        f"`architecture.style` and `architecture.layers` from "
        f".govkit/skill_context.yaml instead. If this is a false positive on "
        f"ordinary English, reword it — the ban is intentionally blunt."
    )


# (text, should_match) — what the matcher must and must not catch. Written as
# a table so trimming the ban list to whatever happens to pass fails here.
_STYLE_MATCHER_CASES = [
    # The exact wording #119 removed.
    ("3. Identify required design elements aligned to Hexagonal Architecture:", True),
    ("- Inbound ports (`ports/inbound/`)", True),
    ("- Outbound ports (`ports/outbound/**`)", True),
    ("- Follow Hexagonal Architecture (ports + adapters)", True),
    # Capitalisation variants — the bypass a case-sensitive check allowed.
    ("Follow Hexagonal architecture", True),
    ("follow HEXAGONAL ARCHITECTURE", True),
    # Bare style ids: what `architecture.style` holds. Naming one is deciding
    # the answer rather than reading it.
    ("This project uses a hexagonal layout.", True),
    ("Assume a clean layout.", True),
    ("Assume a layered layout.", True),
    ("Assume dbt-layered.", True),
    # Must NOT match: the multi-service example names a path inside a
    # service, which is a claim about paths, not about this repo's layers.
    ("   `src/orders/services/pricing.py`.", False),
    ("- Domain logic modules and their services", False),
    # Word boundaries: no firing inside longer words.
    ("Cleanup of the task list is out of scope.", False),
    ("Apply the guidance layer-by-layer.", False),
    ("Read the multilayered guidance.", False),
    # The wording that replaced it must survive.
    ("   - Read `.govkit/skill_context.yaml` for the architecture style and the", False),
    ("     folder hints under `architecture.layers` (inbound / outbound / domain).", False),
]


@pytest.mark.parametrize(
    "text, should_match", _STYLE_MATCHER_CASES,
    ids=[f"{'catch' if m else 'allow'}:{t[:38].strip()}" for t, m in _STYLE_MATCHER_CASES],
)
def test_the_style_matcher_catches_the_defect_and_nothing_else(text, should_match):
    assert bool(_STYLE_ASSERTION_RE.search(_prose(text))) is should_match


def test_a_fenced_example_may_name_a_style():
    """Documenting the file format is not asserting an architecture. A skill
    showing what `.govkit/skill_context.yaml` looks like has to be able to
    put a real value in it — the same split `test_stack_neutral_docs.py`
    makes between a rule and an illustration."""
    fenced = "Read it:\n\n```yaml\narchitecture:\n  style: hexagonal\n```\n\nThen plan.\n"
    assert not _STYLE_ASSERTION_RE.search(_prose(fenced))
    # ...but the same sentence outside a fence is still caught.
    assert _STYLE_ASSERTION_RE.search(_prose("The style is hexagonal.\n"))


def test_the_style_assertion_list_still_describes_the_original_defect():
    """Guard against the ban list being trimmed to whatever happens to pass.
    Every id here is a value `architecture.style` can hold, and the two
    package names were in codex's and copilot's copies before #119."""
    assert {"hexagonal", "clean", "layered", "dbt-layered"} <= set(_STYLE_ASSERTIONS)
    assert {"ports/inbound", "ports/outbound"} <= set(_STYLE_ASSERTIONS)
    # The ban must not grow to forbid the multi-service example.
    assert not any("services/pricing" in token for token in _STYLE_ASSERTIONS)


def test_architecture_guidance_parity_across_agents():
    """The three agents may phrase their skills differently, but they must
    not disagree about *where this project's layers come from*. #119 existed
    because claude-code read the recorded architecture and the other two
    asserted hexagonal — a divergence the frontmatter-and-named-sections
    parity checks cannot see."""
    for skill in ("spec-planning", "implementation-plan"):
        refs = {}
        for agent in ("claude-code", "codex", "copilot"):
            text = (REPO_ROOT / "agents" / agent / "skills" / "backend" / skill
                    / "SKILL.md").read_text(encoding="utf-8")
            refs[agent] = (
                "architecture.layers" in text,
                bool(_STYLE_ASSERTION_RE.search(_prose(text))),
            )
        assert len(set(refs.values())) == 1, (
            f"{skill}: agents disagree on where the architecture comes from: {refs}"
        )
        assert refs["claude-code"] == (True, False)


def test_parity_doc_skill_count_matches_reality():
    """PARITY_TEST.md states the skill inventory as a number, and it had already
    drifted (11 skills / 33 files against an actual 12 / 36) before the defect
    lane added one. A stated count nothing checks is a count that goes stale."""
    import re

    skill_files = sorted(REPO_ROOT.glob("agents/*/skills/*/*/SKILL.md"))
    agents = {p.parents[3].name for p in skill_files}
    assert agents == {"claude-code", "codex", "copilot"}, agents

    per_agent = len(skill_files) // len(agents)
    doc = (REPO_ROOT / "PARITY_TEST.md").read_text(encoding="utf-8")
    match = re.search(
        r"The (\d+) skills \((\d+) backend \+ (\d+) UI\) × 3 agents = (\d+) SKILL\.md files",
        doc,
    )
    assert match, "PARITY_TEST.md no longer states the skill inventory in the pinned form"
    stated_total, stated_backend, stated_ui, stated_files = (int(g) for g in match.groups())

    backend = len({p.parent.name for p in skill_files if p.parents[1].name == "backend"})
    ui = len({p.parent.name for p in skill_files if p.parents[1].name == "ui"})
    assert (stated_backend, stated_ui) == (backend, ui), (
        f"PARITY_TEST.md says {stated_backend} backend + {stated_ui} UI; "
        f"the tree has {backend} + {ui}"
    )
    assert stated_total == per_agent == backend + ui
    assert stated_files == len(skill_files)
