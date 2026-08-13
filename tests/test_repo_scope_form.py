"""Repository Scope declaration must use one form across the whole payload.

Three vocabularies shipped for the same concept:

1. Rule files said `"This feature is contained to" has a checked box` — a phrase
   that appears in **no** shipped artifact, so a literal-minded agent HALTs on a
   correctly-filled `nfrs.md`.
2. Preflight skills and the guidance doc said `One box is checked: "This
   repository only" OR "Multiple repositories"` — matching only `starter_data`.
3. Every other starter, the worked example, and `ci/*/repo-scope-check.yml`
   use ``**Scope:** `single-repo` ``.

The CI gate is authoritative: it greps `^\\*\\*Scope:\\*\\*` and fails without it.
These tests pin form 3 everywhere, and pin the starters to what that gate accepts
so `govkit init` cannot emit a feature that fails its own repository's gate.

Per [[feedback_agent_parity]], the rule text is checked across all three agents.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# The form the shipped CI gate accepts: **Scope:** `single-repo` | `multi-repo`
SCOPE_LINE_RE = re.compile(r"^\*\*Scope:\*\*\s*`(single-repo|multi-repo)`", re.MULTILINE)

# Phrases that reference a representation nothing in the payload emits.
STALE_PHRASES = [
    "This feature is contained to",
    'One box is checked: "This repository only"',
]

RULE_PATHS = [
    REPO_ROOT / "agents" / "claude-code" / "rules" / "generic" / f"repo-scope-{layer}.md"
    for layer in ("backend", "ui")
] + [
    REPO_ROOT / "agents" / "codex" / "rules" / "generic" / f"repo-scope-{layer}.md"
    for layer in ("backend", "ui")
] + [
    REPO_ROOT
    / "agents"
    / "copilot"
    / "instructions"
    / "generic"
    / f"repo-scope-{layer}.instructions.md"
    for layer in ("backend", "ui")
]

PREFLIGHT_PATHS = [
    REPO_ROOT / "agents" / agent / "skills" / layer / "architecture-preflight" / "SKILL.md"
    for agent in ("claude-code", "codex", "copilot")
    for layer in ("backend", "ui")
]

GUIDANCE_PATH = REPO_ROOT / "docs" / "REPO_SCOPE_ANALYSIS_GUIDANCE.md"

STARTER_NFRS = sorted((REPO_ROOT / "features").glob("starter_*/nfrs.md"))

GATE_PATHS = [
    REPO_ROOT / "ci" / "github" / "repo-scope-check.yml",
    REPO_ROOT / "ci" / "azure" / "repo-scope-check.yml",
]


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def test_starter_nfrs_discovered():
    """Guard against the glob silently matching nothing (a vacuous suite)."""
    assert len(STARTER_NFRS) >= 4, (
        f"expected several starter nfrs.md files, found {[_rel(p) for p in STARTER_NFRS]}"
    )


@pytest.mark.parametrize("gate_path", GATE_PATHS, ids=lambda p: p.parent.name)
def test_gate_still_requires_the_scope_line(gate_path: Path):
    """Pin this suite to the shipped gate.

    If the gate ever stops enforcing `**Scope:**`, these tests are asserting a
    contract nothing enforces and must be revisited rather than silently passing.
    """
    assert r"^\*\*Scope:\*\*" in gate_path.read_text(encoding="utf-8"), (
        f"{_rel(gate_path)} no longer greps for '**Scope:**' — "
        "the canonical repo-scope form changed; update this test suite deliberately"
    )


@pytest.mark.parametrize("nfrs_path", STARTER_NFRS, ids=lambda p: p.parent.name)
def test_starter_nfrs_uses_scope_declaration(nfrs_path: Path):
    """`govkit init` copies a starter verbatim into a non-`starter_*` directory,
    where the CI gate no longer skips it. A starter that lacks the `**Scope:**`
    line therefore produces a feature that fails repo-scope-check on day one."""
    text = nfrs_path.read_text(encoding="utf-8")
    assert SCOPE_LINE_RE.search(text), (
        f"{_rel(nfrs_path)} has no '**Scope:** `single-repo`' line — a feature "
        "created from this starter fails ci/*/repo-scope-check.yml"
    )


@pytest.mark.parametrize(
    "doc_path",
    RULE_PATHS + PREFLIGHT_PATHS + [GUIDANCE_PATH],
    ids=_rel,
)
def test_no_stale_scope_vocabulary(doc_path: Path):
    """Agent-facing text must not instruct the agent to look for a representation
    the payload never emits — that produces a false HALT on a correct file."""
    text = doc_path.read_text(encoding="utf-8")
    found = [phrase for phrase in STALE_PHRASES if phrase in text]
    assert not found, (
        f"{_rel(doc_path)} references a repo-scope form nothing emits: {found}"
    )


@pytest.mark.parametrize("doc_path", RULE_PATHS + PREFLIGHT_PATHS, ids=_rel)
def test_agent_text_names_the_canonical_form(doc_path: Path):
    """The rule and preflight text must name the form the starters and the gate
    actually use, so the completeness check the agent runs can succeed."""
    text = doc_path.read_text(encoding="utf-8")
    assert "**Scope:**" in text, (
        f"{_rel(doc_path)} never mentions the '**Scope:**' declaration the "
        "starters emit and ci/*/repo-scope-check.yml enforces"
    )


def test_rule_scope_check_is_identical_across_agents():
    """[[feedback_agent_parity]] — the completeness checklist must not drift
    between the three agents."""
    by_layer: dict[str, dict[Path, str]] = {"backend": {}, "ui": {}}
    for path in RULE_PATHS:
        layer = "backend" if "backend" in path.name else "ui"
        text = path.read_text(encoding="utf-8")
        start = text.find("## Repository Scope Clarity")
        assert start != -1, f"{_rel(path)} missing '## Repository Scope Clarity'"
        end = text.find("\n---", start)
        by_layer[layer][path] = text[start : end if end != -1 else len(text)].strip()

    for layer, sections in by_layer.items():
        distinct = set(sections.values())
        assert len(distinct) == 1, (
            f"{layer} repo-scope checklist differs across agents: "
            f"{[_rel(p) for p in sections]}"
        )
