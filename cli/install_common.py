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

from pathlib import Path
from typing import TYPE_CHECKING

from . import paths
from .fs import copy_entry
from .marker import read_govkit_marker

if TYPE_CHECKING:
    from .detect import RepoProfile


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
