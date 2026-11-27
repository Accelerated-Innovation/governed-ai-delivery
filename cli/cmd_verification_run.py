# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""`govkit verification-run`: build a run for the Product Definition Graph, then post it.

`build` reads the target and its baseline tag, and writes one document. It
opens no connection. `push` is the separate, explicit step that sends that
document's `request`, with an address and a token from the environment.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import paths, verification_push, verification_run
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


def cmd_push(args: argparse.Namespace) -> None:
    try:
        document = verification_push.read_run(Path(args.run))
    except verification_push.PushError as exc:
        _refuse(str(exc))
    request = document["request"]
    if request is None:
        # Not a failure of the build: the default branch is often ahead of the baseline.
        print(verification_run.render(document))
        print("Nothing was sent to the graph.")
        sys.exit(verification_push.EXIT_RECORDED)
    base_url = os.environ.get(verification_push.URL_ENV)
    token = os.environ.get(verification_push.TOKEN_ENV)
    if not base_url or not token:
        _refuse(
            f"set {verification_push.URL_ENV} to the graph's address and "
            f"{verification_push.TOKEN_ENV} to a service token. Neither is read "
            "from the repository or an option."
        )
    reference, count = request["run_reference"], len(request["results"])
    try:
        created = verification_push.post(base_url, request, token=token)
    except verification_push.PushError as exc:
        _refuse(str(exc))
    except verification_push.Refused as refused:
        print(
            f"The graph refused run {reference} ({refused.status} {refused.code}). "
            "Nothing was recorded.",
            file=sys.stderr,
        )
        for name in refused.names:
            print(f"  {name}", file=sys.stderr)
        sys.exit(verification_push.EXIT_REFUSED)
    except verification_push.Unanswered as silent:
        print(
            f"No usable answer for run {reference}: {silent}. Whether it was recorded "
            "is not known; sending the same run again is safe.",
            file=sys.stderr,
        )
        sys.exit(verification_push.EXIT_UNANSWERED)
    if created:
        print(f"The graph recorded run {reference} with {count} result(s).")
    else:
        print(f"The graph already held run {reference}, unchanged. Nothing was written.")
    sys.exit(verification_push.EXIT_RECORDED)


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
    push = actions.add_parser(
        "push",
        help=(
            "Post the request of a built run to the graph. The address and the service "
            "token come from the environment. Exits 0 when the run is recorded, already "
            "recorded or there is nothing to send, 1 when the graph refused it, 3 when "
            "it gave no usable answer and 2 when the push could not start."
        ),
    )
    push.add_argument(
        "--run",
        required=True,
        metavar="FILE",
        help="The document `verification-run build --output` wrote.",
    )
    push.set_defaults(func=cmd_push)
