"""
Anchor-string verification for the Level-3 entry-point instruction files
authored in Increment 5 of the L3/L4 maturity-model swap (plan §5.1, §11 row 5).

The kit's parity invariant is that all three agents (claude-code, copilot,
codex) ship equivalent governance content. This test enforces that the L3
foundation files satisfy the six anchor criteria from the plan and that the
12 files have line-count parity (within ±20% of the median).

Failures here mean the L3 instruction set has drifted — fix the affected
files rather than relaxing the anchors.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

L3_FILES = [
    REPO_ROOT / "agents" / "claude-code" / "claude-md" / "backend-api.md",
    REPO_ROOT / "agents" / "claude-code" / "claude-md" / "backend-cli.md",
    REPO_ROOT / "agents" / "claude-code" / "claude-md" / "ui-react.md",
    REPO_ROOT / "agents" / "claude-code" / "claude-md" / "ui-angular.md",
    REPO_ROOT / "agents" / "copilot" / "copilot-instructions" / "backend-api.md",
    REPO_ROOT / "agents" / "copilot" / "copilot-instructions" / "backend-cli.md",
    REPO_ROOT / "agents" / "copilot" / "copilot-instructions" / "ui-react.md",
    REPO_ROOT / "agents" / "copilot" / "copilot-instructions" / "ui-angular.md",
    REPO_ROOT / "agents" / "codex" / "agents-md" / "backend-api.md",
    REPO_ROOT / "agents" / "codex" / "agents-md" / "backend-cli.md",
    REPO_ROOT / "agents" / "codex" / "agents-md" / "ui-react.md",
    REPO_ROOT / "agents" / "codex" / "agents-md" / "ui-angular.md",
]


def _short(path: Path) -> str:
    """Repo-relative, slash-normalized id for parametrize output."""
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


@pytest.fixture(params=L3_FILES, ids=[_short(p) for p in L3_FILES])
def l3_file(request) -> Path:
    return request.param


# ---------------------------------------------------------------------------
# Anchor (a) — references docs/<area>/architecture/
# ---------------------------------------------------------------------------


def test_references_architecture_docs(l3_file: Path):
    text = l3_file.read_text(encoding="utf-8")
    is_ui = "ui-" in l3_file.name
    expected = "docs/ui/architecture/" if is_ui else "docs/backend/architecture/"
    assert expected in text, (
        f"{_short(l3_file)} must reference {expected} (anchor a)"
    )


# ---------------------------------------------------------------------------
# Anchor (b) — no `features/$ARGUMENTS` or `features/<feature>/`
# ---------------------------------------------------------------------------


def test_no_feature_artifact_path_references(l3_file: Path):
    text = l3_file.read_text(encoding="utf-8")
    forbidden_patterns = [
        r"features/\$ARGUMENTS",
        r"features/<feature_name>",
        r"features/<feature>/",
    ]
    for pattern in forbidden_patterns:
        assert not re.search(pattern, text), (
            f"{_short(l3_file)} contains forbidden L4 feature path "
            f"`{pattern}` (anchor b)"
        )


# ---------------------------------------------------------------------------
# Anchor (c) — mentions when an ADR is required
# ---------------------------------------------------------------------------


def test_mentions_adr_required(l3_file: Path):
    text = l3_file.read_text(encoding="utf-8")
    # The L3 files use either "ADR Rules" (backend) or "ADR Required For" (UI)
    has_adr_section = "ADR Rules" in text or "ADR Required For" in text
    assert has_adr_section, (
        f"{_short(l3_file)} must include an `ADR Rules` or `ADR Required For` "
        f"section (anchor c)"
    )


# ---------------------------------------------------------------------------
# Anchor (d) — points to `govkit apply --level 4`
# ---------------------------------------------------------------------------


def test_points_to_l4_upgrade(l3_file: Path):
    text = l3_file.read_text(encoding="utf-8")
    assert "govkit apply --level 4" in text, (
        f"{_short(l3_file)} must point to `govkit apply --level 4` for the "
        f"spec-driven add-on upgrade (anchor d)"
    )


# ---------------------------------------------------------------------------
# Anchor (f) — anchor string "Feature artifacts are not part of L3"
# ---------------------------------------------------------------------------


def test_contains_anchor_string(l3_file: Path):
    text = l3_file.read_text(encoding="utf-8")
    assert "Feature artifacts are not part of L3" in text, (
        f"{_short(l3_file)} must contain the anchor string "
        f'"Feature artifacts are not part of L3" (anchor f)'
    )


# ---------------------------------------------------------------------------
# Anchor (e) — line-count parity within ±20% of median
# ---------------------------------------------------------------------------


def test_line_count_parity_within_20_percent():
    counts = {
        _short(p): len(p.read_text(encoding="utf-8").splitlines())
        for p in L3_FILES
    }
    sorted_counts = sorted(counts.values())
    median = sorted_counts[len(sorted_counts) // 2]
    lower = median * 0.8
    upper = median * 1.2
    outliers = {
        name: n for name, n in counts.items()
        if not (lower <= n <= upper)
    }
    assert not outliers, (
        f"L3 instruction files should be within ±20% of median {median} lines "
        f"(range {lower:.0f}–{upper:.0f}). Outliers: {outliers}. All counts: {counts}"
    )


# ---------------------------------------------------------------------------
# Parity invariant — L3 files do not mention discarded L4-only feature concepts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("forbidden", [
    "/govkit-spec-planning",
    "/govkit-architecture-preflight",
    "/govkit-implementation-plan",
    "$govkit-spec-planning",
    "$govkit-architecture-preflight",
    "$govkit-implementation-plan",
    "Mandatory Feature Structure",
    "Evaluation Compliance Summary",
    "Architecture Preflight Triggers",
])
def test_l3_files_do_not_mention_l4_only_concepts(l3_file: Path, forbidden: str):
    """L3 files must not invoke or describe L4-only feature workflow.

    The "Upgrading to Spec-Driven Add-On (Level 4)" section is allowed to mention
    these in the context of *what L4 adds*; that section is delimited by the
    'Upgrading to Spec-Driven Add-On' heading. We strip that section before checking.
    """
    text = l3_file.read_text(encoding="utf-8")
    # Strip the upgrade section (everything from the upgrade heading onward).
    upgrade_marker = "Upgrading to Spec-Driven Add-On"
    idx = text.find(upgrade_marker)
    body = text if idx == -1 else text[:idx]
    assert forbidden not in body, (
        f"{_short(l3_file)}: L4-only concept '{forbidden}' must not appear "
        f"outside the upgrade section"
    )
