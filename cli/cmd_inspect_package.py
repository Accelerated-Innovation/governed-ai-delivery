#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit inspect-package — draft a baseline from an existing feature package.

Registration only. The logic lives in `inspect_package.py`, the split every
sibling command uses (`cmd_validate_baseline.py` beside `baseline_check.py`).
Keeping it means command discovery and the architecture checks treat this
registrar the same as the others rather than as a special case.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import paths
from .inspect_package import main as _main


def cmd_inspect_package(args: argparse.Namespace) -> None:
    sys.exit(_main([
        "--target", str(args.target),
        "--feature", args.feature,
        "--source-key", args.source_key,
        "--out", str(args.out),
    ]))


def register(subparsers) -> None:
    """Register the `inspect-package` subcommand and its arguments."""
    p = subparsers.add_parser(
        "inspect-package",
        help="Draft a behavioral baseline from an existing feature package",
    )
    p.add_argument("--target", required=True, type=Path, help=paths.TARGET_HELP)
    p.add_argument("--feature", required=True, help="the feature key under features/")
    p.add_argument("--source-key", required=True,
                   help="the source_key every reference is qualified with")
    p.add_argument("--out", required=True, type=Path,
                   help="where to write the draft baseline")
    p.set_defaults(func=cmd_inspect_package)
