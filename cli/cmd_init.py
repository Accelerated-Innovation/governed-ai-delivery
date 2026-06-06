#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit init — scaffold a new feature folder from a starter template."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import paths
from .compat import validate_level_type
from .fs import copy_entry
from .marker import read_govkit_level


def _prompt_starter_type() -> str:
    """Interactively prompt for the starter template type."""
    choices = ["backend", "cli", "ui-react", "ui-angular", "data"]
    prompt_text = f"  Feature type? [{' / '.join(choices)}] (default: backend): "
    answer = input(prompt_text).strip().lower()
    if answer == "":
        answer = "backend"
    if answer not in choices:
        print(f"Error: invalid choice '{answer}'. Must be one of: {', '.join(choices)}")
        sys.exit(1)
    return answer


def _starter_dir_slug(starter_type: str) -> str:
    """Map a starter_type to its bundled directory slug.

    Most types map 1:1 (backend → starter_backend). UI variants currently
    share a single framework-agnostic starter — both ui-react and ui-angular
    resolve to starter_ui. If they diverge later, separate starter_ui_react
    and starter_ui_angular dirs can be added without resolver changes (the
    1:1 path is the default).
    """
    if starter_type in ("ui-react", "ui-angular"):
        return "ui"
    return starter_type


def _resolve_starter_dir(starter_type: str, level: str) -> Path:
    """Select the level-appropriate starter directory from the bundled govkit templates.

    L3 (Foundations) has no feature starter — `govkit init` is gated to L4+.
    """
    if level == "3":
        raise ValueError(
            "L3 (Governed AI Delivery — Foundations) has no feature starter. "
            "Run 'govkit apply --level 4' first to enable the spec-driven feature workflow."
        )
    bundled = paths.REPO_ROOT / "features"
    slug = _starter_dir_slug(starter_type)
    if level == "5":
        level_dir = bundled / f"starter_{slug}_l5"
        if level_dir.exists():
            return level_dir
    return bundled / f"starter_{slug}"


def cmd_init(args: argparse.Namespace) -> None:
    """Create a new feature folder from the appropriate starter template."""
    target = Path(args.target).resolve()

    # Determine level early so we can gate L3 before any other checks.
    level = args.level or read_govkit_level(target) or "3"

    if level == "3":
        print(
            "Error: 'govkit init' requires Level 4 (Spec-Driven Add-On) or higher.\n"
            "  Level 3 (Foundations) ships agent rules and architecture contracts only;\n"
            "  it has no features/ directory model.\n"
            "  Run 'govkit apply --level 4 --target <path>' to enable the spec-driven\n"
            "  feature workflow, then re-run 'govkit init'."
        )
        sys.exit(1)

    features_dir = target / "features"
    if not features_dir.exists():
        print(f"Error: no features/ directory found in {target}. Run 'govkit apply' first.")
        sys.exit(1)

    feature_name = args.feature
    feature_dir = features_dir / feature_name
    if feature_dir.exists():
        print(f"Error: feature '{feature_name}' already exists at {feature_dir}")
        sys.exit(1)

    starter_type = args.starter or _prompt_starter_type()
    starter_dir = _resolve_starter_dir(starter_type, level)

    if not starter_dir.exists():
        print(f"Error: starter template not found at {starter_dir}")
        sys.exit(1)

    if starter_type == "data":
        validate_level_type(level, "data", context_flag="--starter")

    copy_entry(starter_dir, feature_dir)
    print(f"\nCreated feature '{feature_name}' from {starter_dir.name} (level {level})")
    print(f"  Location: {feature_dir}")
    print("\nNext steps:")
    print(f"  1. Edit {feature_dir / 'acceptance.feature'} — write your Gherkin scenarios")
    print(f"  2. Edit {feature_dir / 'nfrs.md'} — replace all TBD entries")
    if level == "5":
        print(f"  3. Run /architecture-preflight {feature_name}")
        print(f"  4. Run /genai-preflight {feature_name}")
    else:  # L4
        print(f"  3. Run /architecture-preflight {feature_name}")
        print(f"  4. Run /spec-planning {feature_name}")


def register(subparsers) -> None:
    """Register the `init` subcommand and its arguments."""
    p = subparsers.add_parser("init", help="Create a new feature folder from a starter template")
    p.add_argument("feature", help="Feature name (e.g. user-auth, schema-publish)")
    p.add_argument("--target", default=".",
                   help="Path to the target project root (default: current directory)")
    p.add_argument("--starter", choices=["backend", "cli", "ui-react", "ui-angular", "data"], default=None,
                   help="Starter template type (default: prompted)")
    p.add_argument("--level", choices=["3", "4", "5"], default=None,
                   help="Maturity level (default: read from .govkit or 4)")
    p.set_defaults(func=cmd_init)
