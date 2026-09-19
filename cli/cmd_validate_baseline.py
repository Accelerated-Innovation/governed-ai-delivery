#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit validate-baseline — check a working tree against an approved baseline.

Its own module with its own registrar, following every other subcommand.
It first shared `cmd_validate`'s, which meant neither command's registration
could change without touching the other's.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import paths


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

    roots = _checkouts(args, baseline, target)
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


def _checkouts(
    args: argparse.Namespace, baseline: dict, target: Path
) -> dict[str, Path]:
    """Where each declared source is checked out.

    `--source key=path`, repeatable. A baseline may span independent
    repositories, and mapping every source to the single `--target` inspected
    later sources inside the first one — false refusals, or a clean result
    against unrelated content wherever paths and revisions happened to
    overlap.

    A single-source baseline still defaults to `--target`, because that is the
    common case and requiring the flag for it would be ceremony. A source with
    no mapping is refused by name downstream rather than guessed at.
    """
    declared = [s.get("source_key") for s in baseline.get("sources") or ()]
    roots: dict[str, Path] = {}
    if len(declared) == 1 and declared[0]:
        roots[declared[0]] = target
    for pair in getattr(args, "source", None) or ():
        key, _, where = pair.partition("=")
        if not key or not where:
            print(f"--source expects key=path, got {pair!r}", file=sys.stderr)
            sys.exit(2)
        roots[key] = Path(where).resolve()
    return roots


def register(subparsers) -> None:
    """Register the `validate-baseline` subcommand and its arguments."""
    p = subparsers.add_parser(
        "validate-baseline",
        help="Check a working tree against an approved behavioral baseline",
    )
    p.add_argument("--target", required=True, help=paths.TARGET_HELP)
    p.add_argument("--baseline", required=True, help="Path to the approved baseline JSON")
    p.add_argument(
        "--source", action="append", metavar="KEY=PATH", default=[],
        help="Checkout for a declared source, repeatable. Required when the baseline "
             "spans more than one source; a single-source baseline defaults to --target.",
    )
    p.set_defaults(func=cmd_validate_baseline)
