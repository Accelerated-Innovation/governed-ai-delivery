"""The ADR-authoring skills must teach the vocabulary and template the gates use.

Two defects, both shipped to all three agents:

1. **Status vocabulary drift.** `skills/backend/adr-author/SKILL.md` prescribed
   `Proposed / Approved / Rejected / Deprecated`, while both ADR templates
   prescribe `Proposed | Accepted | Rejected | Superseded`. The token the L4
   governance rule gates implementation on — *"ADRs ... must be Accepted before
   implementation proceeds"* — was absent from the vocabulary the ADR-authoring
   skill handed the agent, and the skill told the agent to follow a template it
   then contradicted. An agent resolving that contradiction has to invent.

2. **Wrong template path.** All three `skills/ui/adr-author/SKILL.md` pointed at
   `governance/ui/templates/architecture_preflight.md` — the *preflight* template,
   not `docs/ui/architecture/ADR/TEMPLATE.md`.

Fixing these authorizes nothing and closes no self-attestation gap. It removes an
incoherence, which is worth doing on its own terms.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

ADR_TEMPLATES = {
    "backend": REPO_ROOT / "docs" / "backend" / "architecture" / "ADR" / "TEMPLATE.md",
    "ui": REPO_ROOT / "docs" / "ui" / "architecture" / "ADR" / "TEMPLATE.md",
}

ADR_SKILLS = [
    (layer, REPO_ROOT / "agents" / agent / "skills" / layer / "adr-author" / "SKILL.md")
    for agent in ("claude-code", "codex", "copilot")
    for layer in ("backend", "ui")
]

# Status tokens the templates do NOT define. `Deprecated` and a capitalised
# `Approved` used as a status both drift from `Superseded` / `Accepted`.
STALE_STATUS_TOKENS = ["Approved / Rejected", "Deprecated"]

# The token `claude-md/l4-*.md` gates implementation on.
GATE_TOKEN = "Accepted"


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def _canonical_statuses(layer: str) -> list[str]:
    """Parse the `## Status` line out of the shipped ADR template."""
    text = ADR_TEMPLATES[layer].read_text(encoding="utf-8")
    match = re.search(r"^## Status\s*\n(.+)$", text, re.MULTILINE)
    assert match, f"{_rel(ADR_TEMPLATES[layer])} has no parseable '## Status' line"
    return [s.strip() for s in match.group(1).split("|")]


@pytest.mark.parametrize("layer", sorted(ADR_TEMPLATES))
def test_template_defines_the_gate_token(layer: str):
    """Guard the premise: the gate keys on `Accepted`, so the template must offer it."""
    assert GATE_TOKEN in _canonical_statuses(layer), (
        f"{_rel(ADR_TEMPLATES[layer])} status vocabulary lacks '{GATE_TOKEN}', "
        "which l4-*.md gates implementation on"
    )


def test_adr_skills_discovered():
    """Non-vacuous guard."""
    assert len(ADR_SKILLS) == 6, ADR_SKILLS
    for _, path in ADR_SKILLS:
        assert path.is_file(), f"missing {_rel(path)}"


@pytest.mark.parametrize("layer, skill", ADR_SKILLS, ids=lambda v: v if isinstance(v, str) else _rel(v))
def test_skill_uses_no_stale_status_token(layer: str, skill: Path):
    text = skill.read_text(encoding="utf-8")
    found = [t for t in STALE_STATUS_TOKENS if t in text]
    assert not found, (
        f"{_rel(skill)} uses status token(s) {found} that "
        f"{_rel(ADR_TEMPLATES[layer])} does not define "
        f"(canonical: {_canonical_statuses(layer)})"
    )


@pytest.mark.parametrize("layer, skill", ADR_SKILLS, ids=lambda v: v if isinstance(v, str) else _rel(v))
def test_skill_teaches_the_gate_token(layer: str, skill: Path):
    assert GATE_TOKEN in skill.read_text(encoding="utf-8"), (
        f"{_rel(skill)} never mentions '{GATE_TOKEN}' — the status the L4 "
        "governance rule requires before implementation may proceed"
    )


@pytest.mark.parametrize("layer, skill", ADR_SKILLS, ids=lambda v: v if isinstance(v, str) else _rel(v))
def test_skill_points_at_an_adr_template(layer: str, skill: Path):
    text = skill.read_text(encoding="utf-8")
    assert "architecture/ADR/TEMPLATE.md" in text, (
        f"{_rel(skill)} does not reference an ADR template path "
        f"(expected something ending 'architecture/ADR/TEMPLATE.md')"
    )
    assert "templates/architecture_preflight.md" not in text, (
        f"{_rel(skill)} points at the architecture-preflight template as though "
        "it were the ADR template"
    )


# ---------------------------------------------------------------------------
# The agent must never write `Accepted`
# ---------------------------------------------------------------------------
#
# This is the payload half of the approval-attestation decision. A CI gate that
# catches an agent-typed `Accepted` after the fact is cleanup; the record still
# says whatever the agent wrote. `Accepted` is a derived state — true because an
# approver named in governance/approval_policy.yaml approved that decision at
# that commit — so the only status an author can honestly write is `Proposed`.
#
# AUTONOMOUS_BUGFIX_AGENT_ANALYSIS.md §2 lists ADR-must-be-Accepted as the only
# "No. Hard stop." for an autonomous agent, precisely because nothing let a
# non-human set it. After this, nothing lets a *human* set it by typing either.

STATUS_MENU = "Proposed | Accepted | Rejected | Superseded"
POLICY_PATH = "governance/approval_policy.yaml"
GATE_JOB = "adr-approval-check"


@pytest.mark.parametrize("layer, skill", ADR_SKILLS, ids=lambda v: v if isinstance(v, str) else _rel(v))
def test_skill_does_not_hand_the_agent_the_status_menu(layer: str, skill: Path):
    """The template offers the vocabulary because a human reads it and picks.
    Repeating the menu in the skill is what let an agent pick `Accepted`."""
    assert STATUS_MENU not in skill.read_text(encoding="utf-8"), (
        f"{_rel(skill)} hands the agent the full status vocabulary, so nothing "
        f"stops it writing '{GATE_TOKEN}' — the one status it cannot earn"
    )


@pytest.mark.parametrize("layer, skill", ADR_SKILLS, ids=lambda v: v if isinstance(v, str) else _rel(v))
def test_skill_tells_the_agent_to_author_proposed(layer: str, skill: Path):
    assert "Proposed" in skill.read_text(encoding="utf-8"), (
        f"{_rel(skill)} never names the one status an author may write"
    )


@pytest.mark.parametrize("layer, skill", ADR_SKILLS, ids=lambda v: v if isinstance(v, str) else _rel(v))
def test_skill_names_where_approval_authority_lives(layer: str, skill: Path):
    """An instruction not to write `Accepted` is a rule in prose — the exact
    prohibited pattern AUTHORITY_AND_APPROVAL_CONTRACT.md names ('permission
    declarations inside prompt text') if it is not backed by something real. The
    skill must point at the policy and the gate that enforce it."""
    text = skill.read_text(encoding="utf-8")
    assert POLICY_PATH in text, f"{_rel(skill)} does not reference {POLICY_PATH}"
    assert GATE_JOB in text, f"{_rel(skill)} does not name the {GATE_JOB} gate"


# ---------------------------------------------------------------------------
# The templates' Approval section
# ---------------------------------------------------------------------------
#
# `## Status` and `## Approval` sat ~140 lines apart, unlinked, and Approval was
# three empty colon-terminated labels bound to no identity, no date and no
# commit. A name typed on one of those lines is not an approval — it is the
# prohibited pattern "treating chat acknowledgment ... as approval" written down.

ALL_ADR_TEMPLATES = ADR_TEMPLATES | {
    "data": REPO_ROOT / "docs" / "data" / "architecture" / "ADR" / "TEMPLATE.md",
}

# The numbered prefix differs by layer (UI numbers Approval `## 11.`), so match
# it the way cli/approval.py does rather than by an exact heading.
APPROVAL_HEADING_RE = re.compile(
    r"^##\s+(?:\d+\.\s*)?Approval\b.*$", re.MULTILINE | re.IGNORECASE,
)


def _approval_section(layer: str) -> str:
    text = ALL_ADR_TEMPLATES[layer].read_text(encoding="utf-8")
    match = APPROVAL_HEADING_RE.search(text)
    assert match, f"{_rel(ALL_ADR_TEMPLATES[layer])} has no Approval section"
    nxt = re.search(r"^##\s", text[match.end():], re.MULTILINE)
    return text[match.end():match.end() + nxt.start()] if nxt else text[match.end():]


def test_every_layer_ships_an_adr_template():
    """Non-vacuous guard for the parametrized tests below."""
    assert len(ALL_ADR_TEMPLATES) == 3
    for path in ALL_ADR_TEMPLATES.values():
        assert path.is_file(), f"missing {_rel(path)}"


@pytest.mark.parametrize("layer", sorted(ALL_ADR_TEMPLATES))
def test_approval_section_offers_no_name_field_to_fill_in(layer: str):
    """`Approved by:` invites a typed name to stand in for an approval."""
    section = _approval_section(layer)
    assert "Approved by:" not in section, (
        f"{_rel(ALL_ADR_TEMPLATES[layer])} still offers an 'Approved by:' field — "
        "a name typed there is bound to no identity, no date and no commit"
    )


@pytest.mark.parametrize("layer", sorted(ALL_ADR_TEMPLATES))
def test_approval_section_says_where_the_approval_actually_comes_from(layer: str):
    section = _approval_section(layer)
    for expected in ("governance/approval_policy.yaml", "adr-approval-check"):
        assert expected in section, (
            f"{_rel(ALL_ADR_TEMPLATES[layer])} Approval section never mentions "
            f"{expected}, so a reader cannot tell what makes this ADR Accepted"
        )


@pytest.mark.parametrize("layer", sorted(ALL_ADR_TEMPLATES))
def test_status_section_is_linked_to_the_approval_it_derives_from(layer: str):
    """The two sections were ~140 lines apart and unlinked. A reader who sees
    the vocabulary menu has to be told that one of those words is not theirs."""
    text = ALL_ADR_TEMPLATES[layer].read_text(encoding="utf-8")
    status = re.search(r"^## Status\s*\n(.+)$", text, re.MULTILINE)
    nxt = re.search(r"^##\s", text[status.end():], re.MULTILINE)
    body = text[status.end():status.end() + nxt.start()]
    assert "derived" in body.lower(), (
        f"{_rel(ALL_ADR_TEMPLATES[layer])} Status section does not say that "
        f"'{GATE_TOKEN}' is derived rather than typed"
    )


@pytest.mark.parametrize("layer", ["backend", "ui"])
def test_adr_skill_body_parity_across_agents(layer: str):
    """[[feedback_agent_parity]] — the ADR skill must not drift between agents."""
    bodies = {
        path: path.read_text(encoding="utf-8")
        for lyr, path in ADR_SKILLS
        if lyr == layer
    }
    assert len(set(bodies.values())) == 1, (
        f"{layer} adr-author SKILL.md differs across agents: "
        f"{[_rel(p) for p in bodies]}"
    )
