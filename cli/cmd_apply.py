#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit apply — install an agent spec kit into a target project."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from . import paths, version
from .compat import validate_level_type
from .install_common import (
    copy_governed_or_shared,
    exclude_for_level,
    install_agent_file,
    post_install_finalize,
)
from .manifest import load_manifest, resolve_options, resolve_variant_files
from .marker import read_govkit_marker, write_govkit_marker
from .stack_select import apply_stack_overlay, print_detection_summary, resolve_stack_choice

if TYPE_CHECKING:
    from .detect import RepoProfile


def _cmd_apply_detect_dry_run(target: Path, args: argparse.Namespace) -> None:
    """`govkit apply --detect`: print the inferred configuration and exit
    without writing anything to the target.

    Useful before a real apply so the user can confirm the inferred stack
    matches their expectations, and for CI scripts that want to log what
    govkit would do without committing to a write.
    """
    from .detect import build_profile, infer_stack
    from .manifest import load_manifest

    profile = build_profile(target)
    inferred_stack, inferred_confidence = infer_stack(profile)

    # The per-type stack default differs (e.g. data -> python-dbt), so resolving
    # the stack requires a concrete type. When --type isn't given, real apply
    # prompts and pressing Enter yields the manifest default — use that same
    # default here so the reported stack matches the reported type instead of a
    # hardcoded 'api'.
    cli_type = getattr(args, "type", None)
    manifest = load_manifest(args.agent)
    default_type = manifest.get("options", {}).get("type", {}).get("default", "api")
    type_value = cli_type or default_type
    type_display = cli_type or f"{default_type} (default)"
    validate_level_type(getattr(args, "level", None), type_value)

    chosen_stack, stack_source, _, _ = resolve_stack_choice(
        getattr(args, "stack", None), type_value,
        profile, inferred_stack, inferred_confidence, target,
    )

    print(f"\n[dry-run --detect] govkit apply would target: {target}\n")
    print_detection_summary(
        profile, inferred_stack, inferred_confidence,
        chosen_stack, stack_source,
    )
    print("\nProposed configuration:")
    print(f"  agent:  {getattr(args, 'agent', None) or '(none)'}")
    print(f"  level:  {getattr(args, 'level', None) or '(prompted)'}")
    print(f"  type:   {type_display}")
    print(f"  ci:     {getattr(args, 'ci', None) or '(prompted)'}")
    print(f"  stack:  {chosen_stack}  (source: {stack_source})")
    print("\nNo files written. Re-run without --detect to apply.")


def _create_features_dir_if_missing(target: Path) -> None:
    """Create `features/` under target if absent. Idempotent."""
    features_dir = target / "features"
    if not features_dir.exists():
        features_dir.mkdir(parents=True)
        print(f"  Created {features_dir} (empty)")


def _ensure_features_dir(target: Path, level: str) -> None:
    """L3 ships agent rules + architecture contracts only. L4/L5 also get an
    empty `features/` so `govkit init <feature>` has somewhere to scaffold."""
    if level == "3":
        return
    _create_features_dir_if_missing(target)


def _apply_variant_install(
    target: Path, args: argparse.Namespace, manifest: dict, agent_dir: Path,
    prior_applied_at: str | None, force: bool, baseline: str,
) -> tuple[dict, RepoProfile | None]:
    """Variant-based manifest path (new format used by all 3 production agents).

    Returns `(marker, profile)` so the caller can thread both into
    `post_install_finalize` and skip one marker read + one repo-tree walk.
    """
    print(f"\nApplying govkit agent '{args.agent}' to {target}\n")
    options = resolve_options(manifest, args)
    validate_level_type(options.get("level"), options.get("type"))
    level = options.get("level", "3")

    stack_meta, stack_assumption, options, profile = apply_stack_overlay(
        target, getattr(args, "stack", None), options, prior_applied_at, force,
    )

    print(f"\n  Configuration: {options}\n")
    files, shared, governed = resolve_variant_files(manifest, options)

    print("Agent files:")
    for entry in files:
        install_agent_file(agent_dir, entry, target, prior_applied_at)

    l5_exclude = exclude_for_level(level)
    print("\nGoverned contracts (skip if present):")
    copy_governed_or_shared(governed, target, prior_applied_at, force, baseline, l5_exclude)
    print("\nShared governance:")
    copy_governed_or_shared(shared, target, prior_applied_at, force, baseline, l5_exclude)

    _ensure_features_dir(target, level)

    marker = write_govkit_marker(
        target, args.agent, level, options,
        stack=stack_meta,
        assumptions=[stack_assumption] if stack_assumption else [],
    )
    return marker, profile


def _apply_legacy_install(
    target: Path, args: argparse.Namespace, manifest: dict, agent_dir: Path,
    prior_applied_at: str | None, force: bool, baseline: str,
) -> tuple[dict | None, None]:
    """Pre-variant flat-manifest path; retained for back-compat with custom agents.

    Returns `(None, None)` — legacy manifests don't write a govkit marker,
    so `post_install_finalize` will read from disk if needed (it'll find
    nothing and no-op cleanly).
    """
    print(f"\nApplying govkit agent '{args.agent}' to {target}\n")
    print("Agent files:")
    for entry in manifest["files"]:
        install_agent_file(agent_dir, entry, target, prior_applied_at)

    print("\nShared governance:")
    copy_governed_or_shared(
        manifest.get("shared", []), target, prior_applied_at, force, baseline, None,
    )

    _create_features_dir_if_missing(target)
    return None, None


def cmd_apply(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    if not target.exists():
        print(f"Error: target directory '{target}' does not exist.")
        sys.exit(1)

    # PR 3 / Chunk D: --detect runs inference and exits without writing.
    if getattr(args, "detect", False):
        _cmd_apply_detect_dry_run(target, args)
        return

    manifest = load_manifest(args.agent)
    agent_dir = paths.AGENTS_DIR / args.agent

    # Edit-protection (A2): consult any prior marker for applied_at so
    # governed/shared docs the user has edited since last apply are protected.
    prior_marker = read_govkit_marker(target)
    prior_applied_at = prior_marker.get("applied_at") if prior_marker else None
    force = bool(getattr(args, "force", False))
    baseline = f"govkit@{version.GOVKIT_VERSION}"

    # Variant manifests are the post-v0.6 format used by all 3 production
    # agents; the flat path is retained for custom agents on the old layout.
    if "variants" in manifest:
        marker, profile = _apply_variant_install(
            target, args, manifest, agent_dir, prior_applied_at, force, baseline,
        )
    else:
        marker, profile = _apply_legacy_install(
            target, args, manifest, agent_dir, prior_applied_at, force, baseline,
        )

    post_install_finalize(target, args.agent, marker=marker, profile=profile)

    print(f"\nDone. '{args.agent}' spec kit applied to {target}")
    print("\nNext step: add your first feature package.")
    print("  govkit init <feature-name> --target <target>   # scaffold from a starter template")
    print("  or drop a feature folder manually into features/")


def register(subparsers) -> None:
    """Register the `apply` subcommand and its arguments."""
    p = subparsers.add_parser("apply", help="Apply an agent spec kit to a target project")
    p.add_argument("--agent", required=True, help="Agent name (e.g. claude-code, copilot)")
    p.add_argument("--target", required=True, help=paths.TARGET_HELP)
    p.add_argument("--level", choices=["3", "4", "5"], default=None,
                   help="Maturity level (default: prompted)")
    p.add_argument("--type", choices=["api", "cli", "ui-react", "ui-angular", "data"], default=None,
                   help="Project type (default: prompted)")
    p.add_argument("--ci", choices=["github", "azure"], default=None,
                   help="CI platform (default: prompted)")
    p.add_argument(
        "--stack", default=None,
        help="Stack overlay id (default depends on --type: python-fastapi for api/cli, "
             "python-dbt for data). Run `govkit stack list` to see available stacks.",
    )
    p.add_argument(
        "--detect", action="store_true",
        help="Dry-run: run repo inference, print the proposed config, and exit "
             "without writing anything to the target",
    )
    p.add_argument(
        "--force", action="store_true",
        help="Override edit-protection and overwrite user-edited governed/shared "
             "docs (those carrying a govkit:editable header)",
    )
    p.set_defaults(func=cmd_apply)
