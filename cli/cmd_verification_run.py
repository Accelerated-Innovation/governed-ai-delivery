# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""`govkit verification-run build`: the run for the Product Definition Graph, offline.

The command reads the target and its baseline tag, and writes one document.
It opens no connection. The document's `request` is what a later, separate
step may send.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import paths, verification_run
from .artifact_publication import publish_assessment


def cmd_build(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    if not target.is_dir():
        _refuse(f"target directory '{target}' does not exist.")
    try:
        facts = verification_run.check_facts(
            run_reference=args.run_reference,
            repository=args.repository,
            baseline_tag=args.baseline,
            build_reference=args.build_ref,
            artifact_reference=args.artifact,
        )
        document = verification_run.build(target, facts)
    except (verification_run.RunError, ValueError, RecursionError) as exc:
        _refuse(str(exc))
    if args.output is not None:
        try:
            if not args.output:
                raise ValueError("empty output")
            publish_assessment(document, target, Path(args.output))
        except (OSError, ValueError):
            _refuse(
                "the output must be a new file outside the target; "
                "an existing file is never replaced."
            )
    else:
        print(json.dumps(document, indent=2))
    print(verification_run.render(document), file=sys.stderr)
    sys.exit(verification_run.exit_code(document))


def _refuse(message: str) -> None:
    """Exit 2, so a caller can tell a run that could not start from one with nothing to send."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(verification_run.EXIT_REFUSED)


def register(subparsers) -> None:
    """Register the `verification-run` subcommand."""
    parser = subparsers.add_parser(
        "verification-run",
        help="Build a verification run for the Product Definition Graph, offline",
    )
    actions = parser.add_subparsers(dest="action", required=True)
    build = actions.add_parser(
        "build",
        help=(
            "Project the recorded results of every feature into one verification run. "
            "Sends nothing. Exits 0 when a request was built, 1 when nothing can be "
            "sent and 2 when the run could not start."
        ),
    )
    build.add_argument("--target", default=".", help=paths.TARGET_HELP)
    build.add_argument(
        "--baseline",
        required=True,
        metavar="TAG",
        help=(
            "The baseline tag the graph has indexed. A result is sent only when the "
            "tag holds its scenario or criterion at the same revision."
        ),
    )
    build.add_argument(
        "--repository", required=True, metavar="OWNER/NAME", help="The indexed repository."
    )
    build.add_argument(
        "--run-reference",
        required=True,
        metavar="SYSTEM:RUN-ID",
        help="The run's own name in the graph, such as github:1234567890-1.",
    )
    build.add_argument(
        "--build-ref", required=True, metavar="REF", help="The CI run's identifier or address."
    )
    build.add_argument(
        "--artifact",
        required=True,
        metavar="URL",
        help="An https:// address of the report for this run. It is stored, never fetched.",
    )
    build.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help=(
            "Write the document to a new file outside the target, in place of "
            "standard output. An existing file is never replaced."
        ),
    )
    build.set_defaults(func=cmd_build)
