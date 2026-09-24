# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Explicit local export of saved canonical maintenance facts."""

import sys
from pathlib import Path

from .artifact_publication import publish_assessment
from .maintenance import read_assessment
from .posture import export_posture, render_posture


def cmd_posture(args):
    try:
        assessment = read_assessment(Path(args.assessment))
        report = export_posture(assessment.document)
        # Construct both output forms before publication; neither can expose raw
        # source error messages, filenames or evidence payloads.
        display = report.to_json() if args.json else render_posture(report)
        if args.output is not None:
            if not args.output:
                raise ValueError("Empty output")
            publish_assessment(report.document, assessment.document["target"], Path(args.output))
    except (OSError, ValueError, RecursionError):
        print(
            "Unable to export posture: invalid input or unsafe output; inspect the local assessment and destination.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(display)
    # This is an export command, not an evidence gate. The canonical nonpassing
    # states and exit code remain in its maintenance section.
    sys.exit(0)


def register(subparsers):
    parser = subparsers.add_parser(
        "posture", help="Export privacy-filtered canonical maintenance facts"
    )
    actions = parser.add_subparsers(dest="action", required=True)
    export = actions.add_parser("export", help="Project a saved canonical assessment, offline")
    export.add_argument(
        "--assessment", required=True, help="Local canonical maintenance-assessment JSON/YAML"
    )
    export.add_argument(
        "--output", help="Create a new private JSON artifact outside the assessed repository"
    )
    export.add_argument("--json", action="store_true", help="Print deterministic versioned JSON")
    export.set_defaults(func=cmd_posture)
