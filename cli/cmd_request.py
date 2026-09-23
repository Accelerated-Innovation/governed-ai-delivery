# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Local normalization template and read-only per-request planning."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import paths
from .schema_validation import canonical_json, read_document
from .workflow_store import load_workflow_plan, plan_request, render_workflow
from .workflows import parse_request, request_template


def cmd_request(args: argparse.Namespace) -> None:
    try:
        if args.request_command == "template":
            print(canonical_json(request_template()))
            return
        report = plan_request(
            Path(args.target),
            parse_request(read_document(Path(args.request))),
            observed_scope=read_document(Path(args.scope)) if args.scope else None,
            previous=load_workflow_plan(Path(args.previous)) if args.previous else None,
        )
        print(report.to_json() if args.json else render_workflow(report, explain=args.explain))
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "request", help="Normalize intent and plan proportional workflow evidence"
    )
    commands = parser.add_subparsers(dest="request_command", required=True)
    template = commands.add_parser(
        "template", help="Print a proposed request template with unknown impacts"
    )
    template.set_defaults(func=cmd_request)
    plan = commands.add_parser(
        "plan", help="Resolve a local request against current accepted policy and pinned resources"
    )
    plan.add_argument("request", help="Normalized request JSON or YAML")
    plan.add_argument("--target", default=".", help=paths.TARGET_HELP)
    plan.add_argument("--scope", help="Explicit scope observations; does not derive a Git diff")
    plan.add_argument("--previous", help="Previous saved plan to compare with current inputs")
    output = plan.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="Print a replayable versioned plan")
    output.add_argument(
        "--explain", action="store_true", help="Show policy reasons and all unresolved decisions"
    )
    plan.set_defaults(func=cmd_request)
