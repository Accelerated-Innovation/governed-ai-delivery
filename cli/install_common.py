#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Shared install helpers used by both `govkit apply` and `govkit upgrade`.

The governed/shared copy loop, the L5-only governed-doc exclusion, and the
post-install finalization (derived files + rule re-templating + checklist) are
common to apply and upgrade. They live here so both command modules import
them inward without duplicating logic or reaching back into cli/govkit.py.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from . import paths
from .fs import copy_entry
from .marker import read_govkit_marker

if TYPE_CHECKING:
    from .detect import RepoProfile


# A6: govkit used to install its agent instructions at these top-level paths.
# They now live in the auto-loaded rules namespace, so on upgrade an existing
# install carries an orphaned copy. This maps each new governance dest back to
# the legacy path it superseded, so upgrade can retire the orphan.
_LEGACY_INSTRUCTION_DEST = {
    ".claude/rules/govkit/governance.md": "CLAUDE.md",
    ".claude/rules/govkit/governance-src.md": "src/CLAUDE.md",
    ".github/instructions/govkit/governance.instructions.md": ".github/copilot-instructions.md",
}


def reconcile_legacy_instruction_files(
    target: Path, agent_dir: Path, files: list,
) -> list:
    """Retire a pre-namespace govkit instruction file before writing governance.

    For each governance entry, if the legacy top-level file it superseded is
    present:
      - byte-identical to govkit's governance body ⇒ it is govkit's own
        untouched orphan; delete it and let governance install.
      - otherwise ⇒ treat it as the team's file: keep it, and drop the
        governance entry so upgrade does not install duplicate governance
        alongside it. A warning tells the team how to adopt the managed layout.

    Returns the files list to actually write. Upgrade-only: on a fresh apply a
    top-level CLAUDE.md is the team's, and governance is expected to coexist.
    """
    keep = []
    for entry in files:
        legacy_rel = _LEGACY_INSTRUCTION_DEST.get(entry["dest"])
        if legacy_rel is None:
            keep.append(entry)
            continue
        legacy = target / legacy_rel
        if not legacy.exists():
            keep.append(entry)
            continue
        govkit_body = (agent_dir / entry["src"]).read_text(encoding="utf-8")
        try:
            legacy_body = legacy.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            legacy_body = None
        if legacy_body == govkit_body:
            legacy.unlink()
            print(f"  migrated {legacy_rel} -> {entry['dest']}  (removed govkit-authored orphan)")
            keep.append(entry)
        else:
            print(
                f"  warning: {legacy_rel} exists and is not govkit's governance; "
                f"leaving it and skipping {entry['dest']} to avoid duplicate governance. "
                f"If it is no longer needed, delete {legacy_rel} and re-run upgrade to "
                "adopt the managed governance.",
                file=sys.stderr,
            )
    return keep


# PR 6c: L5-only architecture docs. These live in docs/backend/architecture/
# alongside the universal baseline files for repo-self-governance purposes,
# but they must NOT install at L3/L4 — doctor D007 (LLM-leakage in non-L5)
# is the canary. Future PR may relocate these into a separate dir and drop
# the exclusion machinery.
_L5_ONLY_GOVERNED_BASENAMES: set[str] = {
    "AGENT_ARCHITECTURE.md",
    "LLM_GATEWAY_CONTRACT.md",
    "GUARDRAILS_CONTRACT.md",
    "OBSERVABILITY_LLM_CONTRACT.md",
    "EVALUATION_LLM_CONTRACT.md",
}


def exclude_for_level(level: str) -> set[str] | None:
    """Return basenames to exclude from governed copy at this level.

    None at L5 (everything ships); the L5-only set at L3/L4.
    """
    if level == "5":
        return None
    return _L5_ONLY_GOVERNED_BASENAMES


def copy_governed_or_shared(
    rel_paths: list, target: Path, prior_applied_at: str | None,
    force: bool, baseline: str, exclude: set[str] | None,
    skip_existing: bool = True,
) -> None:
    """Copy each governed/shared dir from the bundle (REPO_ROOT) to target.

    `features/` entries are deferred — those land via `govkit init`, not
    apply/upgrade. `skip_existing=True` (the default) is correct for `apply`
    governed/shared and for `upgrade` shared. `upgrade` governed passes
    `skip_existing=False` because upgrade re-installs governed contracts.
    """
    for rel in rel_paths:
        if rel.startswith(paths.FEATURES_PREFIX):
            continue
        copy_entry(
            paths.REPO_ROOT / rel, target / rel,
            skip_existing=skip_existing,
            applied_at=prior_applied_at,
            force=force,
            header_baseline=baseline,
            exclude_basenames=exclude,
        )


def post_install_finalize(
    target: Path, agent: str,
    marker: dict | None = None, profile: RepoProfile | None = None,
) -> None:
    """Write derived files (setup review + skill_context), re-template rule
    globs to match the team's actual layout, print the post-install checklist.

    `marker` and `profile` may be passed in by callers that already have them
    in hand (cmd_apply, cmd_upgrade) so we skip a redundant marker read +
    repo-tree walk. If omitted, both are derived from disk/target.

    No-op when no marker is available (something earlier failed)."""
    from .extensions import report_extensions
    report_extensions(target)

    if marker is None:
        marker = read_govkit_marker(target)
    if marker is None:
        return
    from .rule_templating import template_installed_rules
    from .setup_review import print_review_checklist, write_setup_review
    from .skill_context import load_skill_context, write_skill_context
    write_setup_review(target, marker)
    write_skill_context(target, marker, profile=profile)
    sc = load_skill_context(target)
    if sc is not None:
        template_installed_rules(target, agent, sc.layers)
    print_review_checklist(target, marker)
