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
from .marker import warn_legacy_deprecation
from .validate import run_validation
from .validate_scope import run_scoped_validation


def cmd_validate(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    level = args.level
    if level:
        warn_legacy_deprecation()
    strict = getattr(args, "strict", False)
    only = getattr(args, "only", None)
    features = getattr(args, "feature", None) or []
    known_failures = getattr(args, "known_failures", None)
    expected_digest = getattr(args, "known_failures_digest", None)
    print_record = getattr(args, "print_known_failures", False)
    if not (features or known_failures or expected_digest or print_record):
        sys.exit(run_validation(target, level=level, strict=strict, only=only))
    sys.exit(
        run_scoped_validation(
            target,
            level=level,
            strict=strict,
            only=only,
            features=features,
            known_failures=Path(known_failures) if known_failures else None,
            expected_digest=expected_digest,
            print_record=print_record,
        )
    )


def register(subparsers) -> None:
    """Register the `validate` subcommand and its arguments."""
    p = subparsers.add_parser("validate", help="Check governance compliance in a project")
    p.add_argument("--target", required=True, help=paths.TARGET_HELP)
    p.add_argument("--level", choices=["3", "4", "5"], default=None,
                   help="Maturity level (default: read from .govkit or 4)")
    p.add_argument("--strict", action="store_true",
                   help="Promote extension manifest warnings and outstanding or unverifiable "
                        "architecture experiment evidence to failures")
    p.add_argument("--only", choices=["experiments"], default=None,
                   help="Run only the architecture experiment checks (any level)")
    p.add_argument("--feature", action="append", metavar="NAME",
                   help="Check only this feature directory under features/ (repeatable); "
                        "a name that matches no feature directory is an error")
    record = p.add_mutually_exclusive_group()
    record.add_argument("--known-failures", metavar="PATH",
                        help="Caller-reviewed record of failures accepted as existing: listed "
                             "failures are reported as known and do not fail the run; with "
                             "--strict, a listed failure that now passes fails the run")
    record.add_argument("--print-known-failures", action="store_true",
                        help="Print the current failures in the record format in place of the "
                             "report; govkit never writes or accepts the record")
    p.add_argument("--known-failures-digest", metavar="SHA256",
                   help="Fail unless the --known-failures record has this SHA-256 digest")
    p.set_defaults(func=cmd_validate)
