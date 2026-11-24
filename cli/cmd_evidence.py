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
import json
import sys
from pathlib import Path

from . import evidence_report, paths
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

    feature = getattr(args, "feature", None)
    as_json = getattr(args, "json", False)
    if feature is not None:
        _feature_report(target, feature, as_json, args.fast_max_seconds)
    if as_json:
        _usage_error("--json needs --feature: the JSON report describes one feature.")

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


def _usage_error(message: str) -> None:
    """Exit 2, so a caller can tell a bad invocation from a feature that is not done."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(2)


def _feature_report(target: Path, feature: str, as_json: bool, fast_max_seconds) -> None:
    """One feature's scenarios against the test results. Reads no marker: a
    feature report needs neither a level nor a project type."""
    if fast_max_seconds is not None:
        _usage_error(
            "--fast-max-seconds does not apply with --feature. "
            "Durations are reported for the whole test run, without --feature."
        )
    try:
        report = evidence_report.build_report(target, feature)
    except evidence_report.SelectionError as exc:
        _usage_error(str(exc))
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print(evidence_report.render_text(report))
    sys.exit(evidence_report.exit_code(report))


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
    p.add_argument(
        "--feature",
        metavar="NAME",
        default=None,
        help=(
            "Report one feature: each scenario in features/NAME/acceptance.feature "
            "with the test result bound to it, and each criterion in its "
            "eval_criteria.yaml with its measured score. Exits 0 only when all passed."
        ),
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="With --feature, print the report as JSON (schema: evidence-report).",
    )
    p.set_defaults(func=cmd_evidence)
