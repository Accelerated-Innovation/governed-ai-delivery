# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""govkit conform — local/JSON views of explicit check and evidence states."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import paths
from .change_conformance import inspect_change
from .check_models import Identity
from .conformance import inspect_repository, render_report
from .schema_validation import read_document
from .workflow_store import load_workflow_plan
from .workflows import parse_request


def cmd_conform(args: argparse.Namespace) -> None:
    target = Path(args.target).absolute()
    try:
        arguments = read_document(Path(args.pack_arguments)) if args.pack_arguments else {}
        if not isinstance(arguments, dict):
            raise ValueError("Pack arguments must map check IDs to arrays of strings")
        identity = Identity(target.name, revision=args.revision, observed_at=args.observed_at)
        if args.request:
            if not args.base or not args.policy_target:
                raise ValueError(
                    "Change conformance requires --base and a separate trusted --policy-target"
                )
            report = inspect_change(
                target,
                parse_request(read_document(Path(args.request))),
                base=args.base,
                policy_target=Path(args.policy_target),
                observed_at=args.observed_at,
                previous=load_workflow_plan(Path(args.plan)) if args.plan else None,
                execute_checks=tuple(args.execute_check + args.execute_pack_check),
                pack_arguments=arguments,
            )
            if args.revision and args.revision != report.checks.identity.revision:
                raise ValueError("Explicit revision does not match observed Git HEAD")
            summary = (
                f"Workflow: {report.plan.document['workflow']}; {len(report.change['changes'])} changed paths from {report.change['base']}\n"
                + render_report(report.checks)
            )
        else:
            if args.base or args.policy_target or args.plan or args.execute_check:
                raise ValueError("Change options require --request")
            report = inspect_repository(
                target,
                identity=identity,
                execute_pack_checks=tuple(args.execute_pack_check),
                pack_arguments=arguments,
            )
            summary = render_report(report)
        print(report.to_json() if args.json else summary)
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
        "--revision",
        help="Revision annotation for repository reports; must match Git HEAD with --request",
    )
    parser.add_argument(
        "--observed-at", help="Explicit ISO timestamp annotation; omitted stays unknown"
    )
    parser.add_argument(
        "--request", help="Accepted normalized local request; enables actual-change conformance"
    )
    parser.add_argument(
        "--base", help="Explicit Git base commit/ref selected by the trusted caller"
    )
    parser.add_argument(
        "--policy-target",
        help="Separate trusted checkout containing accepted profile, config and pinned resources",
    )
    parser.add_argument(
        "--plan", help="Optional prior workflow plan to check for stale requirements"
    )
    parser.add_argument(
        "--execute-check",
        action="append",
        default=[],
        metavar="CHECK_ID",
        help="Explicitly run a selected trusted command or pinned control for the change",
    )
    parser.set_defaults(func=cmd_conform)
