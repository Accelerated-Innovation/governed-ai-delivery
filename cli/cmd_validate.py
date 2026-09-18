#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit validate — check per-feature governance compliance in a project."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import paths
from .validate import run_validation


def cmd_validate(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    level = args.level
    strict = getattr(args, "strict", False)
    sys.exit(run_validation(target, level=level, strict=strict))


def cmd_validate_baseline(args: argparse.Namespace) -> None:
    """Check a working tree against an approved behavioral baseline.

    Exit status is what a CI gate reads, so the two failing outcomes are kept
    distinct in the output and identical in the status: a **difference** means
    the spec changed, a **refusal** means the check could not be performed.
    Both exit non-zero, because "I could not look" reported as "nothing
    changed" is the one answer a protected boundary must never receive.

    This reports artifact consistency. Whether the baseline currently carries
    authority is the engine's question, and saying so here keeps a locally
    consistent tree from reading as an authorized one.
    """
    from .baseline_check import check

    target = Path(args.target).resolve()
    baseline_path = Path(args.baseline).resolve()
    if not baseline_path.is_file():
        print(f"baseline file not found: {baseline_path}", file=sys.stderr)
        sys.exit(2)
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as broken:
        print(f"baseline file is not valid JSON: {broken}", file=sys.stderr)
        sys.exit(2)

    roots = {s.get("source_key"): target for s in baseline.get("sources") or ()}
    report = check(baseline, roots)

    for refusal in report.refusals:
        print(f"REFUSED  {refusal}", file=sys.stderr)
    for difference in report.differences:
        print(f"CHANGED  {difference.ref}\n         {difference.role}: {difference.detail}")

    if report.voided:
        print("\nA semantic change voids what was issued against the previous spec:")
        for item in report.voided:
            print(f"  - {item}")
        print(
            "\nThe readiness verdict and Development Token were issued for a spec that no "
            "longer exists. Re-run refinement rather than continuing."
        )

    if report.ok:
        print("no differences: the working tree still says what the baseline recorded.")
        print("(Artifact consistency only — whether this baseline currently authorizes "
              "work is the engine's answer, not this one.)")
        sys.exit(0)
    sys.exit(1)


def register(subparsers) -> None:
    """Register the `validate` subcommand and its arguments."""
    p = subparsers.add_parser("validate", help="Check governance compliance in a project")
    p.add_argument("--target", required=True, help=paths.TARGET_HELP)
    p.add_argument("--level", choices=["3", "4", "5"], default=None,
                   help="Maturity level (default: read from .govkit or 4)")
    p.add_argument("--strict", action="store_true",
                   help="Promote extension manifest warnings to failures")
    p.set_defaults(func=cmd_validate)

    b = subparsers.add_parser(
        "validate-baseline",
        help="Check a working tree against an approved behavioral baseline",
    )
    b.add_argument("--target", required=True, help=paths.TARGET_HELP)
    b.add_argument("--baseline", required=True,
                   help="Path to the approved baseline JSON")
    b.set_defaults(func=cmd_validate_baseline)
