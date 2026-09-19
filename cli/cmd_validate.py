#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit validate — check per-feature governance compliance in a project."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import paths
from .validate import run_validation


def cmd_validate(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    level = args.level
    strict = getattr(args, "strict", False)
    sys.exit(run_validation(target, level=level, strict=strict))


def register(subparsers) -> None:
    """Register the `validate` subcommand and its arguments."""
    p = subparsers.add_parser("validate", help="Check governance compliance in a project")
    p.add_argument("--target", required=True, help=paths.TARGET_HELP)
    p.add_argument("--level", choices=["3", "4", "5"], default=None,
                   help="Maturity level (default: read from .govkit or 4)")
    p.add_argument("--strict", action="store_true",
                   help="Promote extension manifest warnings to failures")
    p.set_defaults(func=cmd_validate)
