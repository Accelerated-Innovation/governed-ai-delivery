# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""govkit conform — local/JSON views of explicit check and evidence states."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import paths
from .check_models import Identity
from .conformance import inspect_repository, render_report
from .schema_validation import read_document


def cmd_conform(args: argparse.Namespace) -> None:
    target = Path(args.target).absolute()
    try:
        arguments = read_document(Path(args.pack_arguments)) if args.pack_arguments else {}
        if not isinstance(arguments, dict):
            raise ValueError("Pack arguments must map check IDs to arrays of strings")
        identity = Identity(target.name, revision=args.revision, observed_at=args.observed_at)
        report = inspect_repository(
            target,
            identity=identity,
            execute_pack_checks=tuple(args.execute_pack_check),
            pack_arguments=arguments,
        )
        print(report.to_json() if args.json else render_report(report))
        if report.exit_code:
            sys.exit(report.exit_code)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def register(subparsers) -> None:
    parser = subparsers.add_parser("conform", help="Inspect check results and required evidence")
    parser.add_argument("--target", default=".", help=paths.TARGET_HELP)
    parser.add_argument("--json", action="store_true", help="Print versioned raw check results")
    parser.add_argument(
        "--execute-pack-check",
        action="append",
        default=[],
        metavar="CHECK_ID",
        help="Explicitly execute a selected pinned control; repeat for multiple controls",
    )
    parser.add_argument(
        "--pack-arguments", help="JSON/YAML file mapping pack check IDs to argument arrays"
    )
    parser.add_argument(
        "--revision", help="Explicit revision annotation; not verified against a diff"
    )
    parser.add_argument(
        "--observed-at", help="Explicit ISO timestamp annotation; omitted stays unknown"
    )
    parser.set_defaults(func=cmd_conform)
