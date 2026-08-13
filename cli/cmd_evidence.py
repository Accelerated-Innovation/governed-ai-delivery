#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""`govkit evidence` — report measured quality evidence per dimension.

Separate from `govkit validate` on purpose. `validate` checks that governed
*artifacts* are well-formed; this reports what an executed tool *observed*.
Collapsing them would put a forecast and an observation behind one verdict,
which is the confusion this work exists to remove.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import paths
from .evidence import Outcome, collect_evidence, summarize
from .marker import read_govkit_marker

_LABEL = {
    Outcome.PASS: "\033[32mPASS\033[0m",
    Outcome.FAIL: "\033[31mFAIL\033[0m",
    Outcome.INCONCLUSIVE: "\033[33mINCONCLUSIVE\033[0m",
    Outcome.ERROR: "\033[31mERROR\033[0m",
}


def cmd_evidence(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"Error: target directory '{target}' does not exist.", file=sys.stderr)
        sys.exit(1)

    # Report the dimensions that describe this project. An unreadable marker
    # reports everything — narrowing on uncertainty would hide a dimension,
    # and silence reads as a pass.
    marker = read_govkit_marker(target) or {}
    project_type = (marker.get("options") or {}).get("type")
    verdicts = collect_evidence(
        target,
        fast_max_seconds=args.fast_max_seconds,
        project_type=project_type,
    )
    print("\ngovkit evidence — measured quality evidence\n")
    width = max(len(v.dimension) for v in verdicts)
    for verdict in verdicts:
        print(f"  {verdict.dimension.ljust(width)}  {_LABEL[verdict.outcome]}  {verdict.detail}")

    exit_code, summary = summarize(verdicts)
    print(f"\n{summary}\n")
    sys.exit(exit_code)


def register(subparsers) -> None:
    """Register the `evidence` subcommand."""
    p = subparsers.add_parser(
        "evidence",
        help="Report measured quality evidence from CI artifacts",
    )
    p.add_argument("--target", default=".", help=paths.TARGET_HELP)
    p.add_argument(
        "--fast-max-seconds", type=float, default=None,
        help=(
            "Per-test duration ceiling. Without it, Fast reports its observed "
            "durations but stays INCONCLUSIVE — govkit will not invent a "
            "threshold your team has not calibrated."
        ),
    )
    p.set_defaults(func=cmd_evidence)
