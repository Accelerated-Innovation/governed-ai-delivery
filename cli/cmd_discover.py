# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Read-only discovery command; explicit profile/pack commands own installation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import paths
from .discovery import discover, load_baseline, render_discovery
from .discovery_scan import DiscoveryLimits


def cmd_discover(args: argparse.Namespace) -> None:
    try:
        limits = DiscoveryLimits(
            **{name: getattr(args, name) for name in DiscoveryLimits.__dataclass_fields__}
        )
        report = discover(
            Path(args.target),
            profile_path=Path(args.profile) if args.profile else None,
            baseline=load_baseline(Path(args.baseline)) if args.baseline else None,
            references=tuple(args.reference),
            capabilities=tuple(args.capability),
            limits=limits,
        )
        print(report.to_json() if args.json else render_discovery(report))
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "discover", help="Inspect existing evidence and focused governance needs without writes"
    )
    parser.add_argument("--target", default=".", help=paths.TARGET_HELP)
    parser.add_argument("--json", action="store_true", help="Print a versioned discovery report")
    parser.add_argument(
        "--profile",
        help="Explicit accepted desired profile; otherwise inspect existing .govkit/profile.yaml",
    )
    parser.add_argument(
        "--baseline",
        help="Explicit last-reviewed discovery JSON; never accepted or replaced automatically",
    )
    parser.add_argument(
        "--reference",
        action="append",
        default=[],
        help="Repository-relative evidence reference; repeat as needed",
    )
    parser.add_argument(
        "--capability",
        action="append",
        default=[],
        help="Propose a capability for review; does not select or install it",
    )
    defaults = DiscoveryLimits()
    for name in DiscoveryLimits.__dataclass_fields__:
        parser.add_argument(
            "--" + name.replace("_", "-"),
            type=int,
            default=getattr(defaults, name),
            help=f"Bound inspection ({name.replace('_', ' ')})",
        )
    parser.set_defaults(func=cmd_discover)
