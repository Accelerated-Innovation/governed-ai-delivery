#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit stack — list bundled stack overlays and re-apply one over an install."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from .marker import read_govkit_marker, write_govkit_marker
from .overlay import apply_overlay, list_overlays, load_overlay
from .setup_review import print_review_checklist, write_setup_review
from .skill_context import write_skill_context
from .stack_select import STACK_ID_ASSUMPTION


def cmd_stack_list(_args: argparse.Namespace) -> None:
    """Print every bundled stack overlay (id, display name, summary).

    Source of truth for "which stacks can I pass to --stack" — read by users
    before running `govkit apply --stack <id>` or `govkit stack apply <id>`.
    """
    overlays = list_overlays()
    if not overlays:
        print("No stack overlays found.")
        return
    print("\nAvailable stack overlays:\n")
    for ov in overlays:
        print(f"  {ov.id:24s} {ov.display_name}")
        if ov.summary:
            print(f"  {'':24s}   {ov.summary}")
    print(
        "\nApply at install time:\n"
        "  govkit apply --agent <agent> --target <path> --stack <id>\n"
        "Or swap an existing install:\n"
        "  govkit stack apply <id> --target <path>\n"
    )


def cmd_stack_apply(args: argparse.Namespace) -> None:
    """Re-apply a stack overlay over an existing install.

    Requires a .govkit/marker.json to exist (errors otherwise). Honors
    edit-protection — user-edited stack docs are not clobbered without
    --force. Updates the marker's `stack` and `options.stack` fields and
    rewrites GOVKIT_SETUP_REVIEW.md.
    """
    target = Path(args.target).resolve()
    if not target.exists():
        print(f"Error: target directory '{target}' does not exist.", file=sys.stderr)
        sys.exit(1)

    stored = read_govkit_marker(target)
    if not stored:
        print(
            "Error: no .govkit marker found. Run 'govkit apply' first to "
            "establish a baseline before swapping stacks.",
            file=sys.stderr,
        )
        sys.exit(1)

    overlay = load_overlay(args.stack_id)
    if overlay is None:
        print(
            f"Error: stack '{args.stack_id}' not found. "
            f"Run `govkit stack list` to see available stacks.",
            file=sys.stderr,
        )
        sys.exit(1)

    agent = stored.get("agent", "claude-code")
    level = stored.get("level", "4")
    prior_applied_at = stored.get("applied_at")
    prior_assumptions = stored.get("assumptions", []) or []
    options = {**stored.get("options", {}), "stack": overlay.id, "level": level}

    print(f"\nApplying stack overlay '{overlay.id}' to {target}")
    print(f"  {overlay.display_name}\n")
    apply_overlay(overlay, target, applied_at=prior_applied_at, force=args.force)

    stack_meta = {
        "id": overlay.id,
        "version": overlay.version,
        "display_name": overlay.display_name,
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }
    # Replace any prior stack.id assumption; keep the rest.
    assumptions = [a for a in prior_assumptions if a.get("id") != STACK_ID_ASSUMPTION]
    assumptions.append({
        "id": STACK_ID_ASSUMPTION,
        "value": overlay.id,
        "source": "flag",
        "confidence": "high",
        "evidence": [],
        "files_affected": [d["dest"] for d in overlay.docs],
        "review_required": False,
        "warning_message": None,
        "calibrated_at": None,
        "calibrated_against_overlay_version": None,
    })

    write_govkit_marker(
        target, agent, level, options,
        stack=stack_meta,
        assumptions=assumptions,
        calibration=stored.get("calibration"),
    )

    new_marker = read_govkit_marker(target)
    if new_marker is not None:
        write_setup_review(target, new_marker)
        write_skill_context(target, new_marker)
        print_review_checklist(target, new_marker)

    print(f"\nDone. Stack '{overlay.id}' applied to {target}")
