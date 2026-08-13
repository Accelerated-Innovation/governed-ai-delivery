"""Agent-facing artifact contracts must agree with the validator that enforces them.

`cli/validate.py` enforces five artifacts at L4. The payload shipped four different
counts beside it:

* `rules/generic/spec-compliance.md` — "all **three** artifacts", installed to
  `.claude/rules/govkit/spec-compliance.md` at L4/L5, right next to a governance
  rule saying five.
* `claude-md/l4-ui-*.md` and `agents-md/l4-ui-*.md` — **no artifact contract at
  all**, while copilot's equivalent lists five. A claude-code L4 ui-react install
  therefore had the 3-artifact rule as its *only* statement.
* `features/README.md` and `claude-md/l4-ui-nextjs.md` — six for UI (the five plus
  `design.md`).

This is deliberately an **inclusion list**, not a repo-wide markdown scan. Most of
the ~166 files naming these artifacts restate them correctly for their own level
and type (L3 states none; the preflight template lists four because a preflight
cannot require itself). A general "vertical parity" axis would need a per-file
exemption allowlist that becomes its own drift surface. These are the files whose
counts are known to contradict the validator.

`design.md` is asserted only in **prose** for UI. It is deliberately advisory to
`govkit validate` — see `tests/test_validate.py::
test_ui_nextjs_design_artifact_is_advisory_to_completeness` and the comment at
`cli/doctor.py`. Nothing here should make it enforced.
"""

from pathlib import Path

import pytest

from cli.validate import L4_REQUIRED_ARTIFACTS

REPO_ROOT = Path(__file__).resolve().parent.parent

UI_DESIGN_ARTIFACT = "design.md"

# Generic rule shipped to every type at L4/L5 — must state the universal five.
SPEC_COMPLIANCE_PATHS = [
    REPO_ROOT / "agents" / "claude-code" / "rules" / "generic" / "spec-compliance.md",
    REPO_ROOT / "agents" / "codex" / "rules" / "generic" / "spec-compliance.md",
    REPO_ROOT
    / "agents"
    / "copilot"
    / "instructions"
    / "generic"
    / "spec-compliance.instructions.md",
]

# Per-type L4 UI root instructions — must state the five plus design.md.
UI_L4_PATHS = [
    REPO_ROOT / "agents" / "claude-code" / "claude-md" / f"l4-{t}.md"
    for t in ("ui-react", "ui-angular")
] + [
    REPO_ROOT / "agents" / "codex" / "agents-md" / f"l4-{t}.md"
    for t in ("ui-react", "ui-angular")
] + [
    REPO_ROOT / "agents" / "copilot" / "copilot-instructions" / f"l4-{t}.md"
    for t in ("ui-react", "ui-angular")
]

STALE_COUNTS = ["all three artifacts", "all four artifacts"]


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def test_validator_contract_is_five():
    """Guard the premise. If the enforced set changes, these expectations must be
    revisited deliberately rather than silently drifting."""
    assert len(L4_REQUIRED_ARTIFACTS) == 5, L4_REQUIRED_ARTIFACTS
    assert UI_DESIGN_ARTIFACT not in L4_REQUIRED_ARTIFACTS, (
        "design.md became validator-enforced; that reverses a pinned decision "
        "and would fail features/ui_task_dashboard/, which ships without it"
    )


@pytest.mark.parametrize("path", SPEC_COMPLIANCE_PATHS, ids=_rel)
def test_spec_compliance_lists_every_enforced_artifact(path: Path):
    text = path.read_text(encoding="utf-8")
    missing = [a for a in L4_REQUIRED_ARTIFACTS if a not in text]
    assert not missing, (
        f"{_rel(path)} omits enforced artifact(s) {missing} — an agent obeying "
        "this rule stops short of what `govkit validate` requires"
    )


@pytest.mark.parametrize("path", SPEC_COMPLIANCE_PATHS + UI_L4_PATHS, ids=_rel)
def test_no_stale_artifact_count(path: Path):
    text = path.read_text(encoding="utf-8").lower()
    found = [c for c in STALE_COUNTS if c in text]
    assert not found, (
        f"{_rel(path)} states {found} but the validator enforces "
        f"{len(L4_REQUIRED_ARTIFACTS)}"
    )


@pytest.mark.parametrize("path", UI_L4_PATHS, ids=_rel)
def test_ui_l4_declares_the_full_artifact_set(path: Path):
    """claude-code and codex shipped no artifact contract for L4 UI at all, so the
    generic 3-artifact rule was the user's only statement of the requirement."""
    text = path.read_text(encoding="utf-8")
    expected = list(L4_REQUIRED_ARTIFACTS) + [UI_DESIGN_ARTIFACT]
    missing = [a for a in expected if a not in text]
    assert not missing, (
        f"{_rel(path)} does not name {missing} — UI features require the five "
        "enforced artifacts plus design.md (features/README.md)"
    )


def test_ui_l4_artifact_contract_is_consistent_across_agents():
    """[[feedback_agent_parity]] — all three agents must state the same UI contract."""
    for variant in ("ui-react", "ui-angular"):
        paths = [p for p in UI_L4_PATHS if p.name == f"l4-{variant}.md"]
        assert len(paths) == 3, f"expected 3 agents for {variant}, got {paths}"
        sets = {}
        for p in paths:
            text = p.read_text(encoding="utf-8")
            sets[p] = frozenset(
                a for a in list(L4_REQUIRED_ARTIFACTS) + [UI_DESIGN_ARTIFACT] if a in text
            )
        assert len(set(sets.values())) == 1, (
            f"l4-{variant} artifact sets differ across agents: "
            + ", ".join(f"{_rel(p)}={sorted(s)}" for p, s in sets.items())
        )
