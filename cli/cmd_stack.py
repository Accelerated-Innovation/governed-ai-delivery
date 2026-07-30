#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit stack — list bundled stack overlays and re-apply one over an install."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import paths
from .compat import is_ui_type
from .install_common import install_agent_file, post_install_finalize
from .manifest import load_manifest, resolve_variant_files
from .marker import read_govkit_marker, write_govkit_marker
from .overlay import apply_overlay, apply_rule_overrides, list_overlays, load_overlay
from .stack_select import STACK_ID_ASSUMPTION, build_stack_assumption, build_stack_meta


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

    stored_type = (stored.get("options") or {}).get("type")
    if is_ui_type(stored_type):
        print(
            f"Error: target type {stored_type!r} is a standalone UI project "
            "type and does not support stack overlays. Select UI frameworks "
            "with `govkit apply --type <ui-type>`.",
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

    # Agent rule files are govkit-owned and stack-scoped: the swap reinstalls
    # the resolved set — the new stack's rule overrides, or the type defaults
    # when it declares none — so rules always match the active stack.
    manifest = load_manifest(agent)
    if "variants" in manifest:
        files, _, _ = resolve_variant_files(manifest, options)
        files = apply_rule_overrides(files, overlay, agent)
        agent_dir = paths.AGENTS_DIR / agent
        print("\nAgent files (refreshed for the stack):")
        for entry in files:
            install_agent_file(agent_dir, entry, target, prior_applied_at)

    stack_meta = build_stack_meta(overlay)
    # Replace any prior stack.id assumption; keep the rest. The stack id is
    # an explicit CLI argument here, so source/confidence mirror the --stack
    # flag path in apply.
    assumptions = [a for a in prior_assumptions if a.get("id") != STACK_ID_ASSUMPTION]
    assumptions.append(
        build_stack_assumption(overlay, source="flag", confidence="high", evidence=[])
    )

    write_govkit_marker(
        target, agent, level, options,
        stack=stack_meta,
        assumptions=assumptions,
        calibration=stored.get("calibration"),
    )

    # Full finalize (setup review, skill_context, rule + skill templating,
    # checklist) — the reinstalled rule files carry template frontmatter that
    # must be expanded for the new stack's layers.
    post_install_finalize(target, agent)

    print(f"\nDone. Stack '{overlay.id}' applied to {target}")


def register(subparsers) -> None:
    """Register the `stack` subcommand tree (`stack list`, `stack apply`)."""
    stack_parser = subparsers.add_parser(
        "stack",
        help="List or apply bundled stack overlays",
    )
    stack_sub = stack_parser.add_subparsers(dest="stack_command", required=True)

    list_parser = stack_sub.add_parser("list", help="List bundled stack overlays")
    list_parser.set_defaults(func=cmd_stack_list)

    apply_parser = stack_sub.add_parser(
        "apply",
        help="Re-apply a stack overlay over an existing install",
    )
    apply_parser.add_argument(
        "stack_id",
        help="Stack overlay id (e.g. dotnet-aspnet). See `govkit stack list`.",
    )
    apply_parser.add_argument(
        "--target", required=True,
        help="Path to the target project root (must contain a .govkit marker)",
    )
    apply_parser.add_argument(
        "--force", action="store_true",
        help="Override edit-protection and overwrite user-edited stack docs",
    )
    apply_parser.set_defaults(func=cmd_stack_apply)
