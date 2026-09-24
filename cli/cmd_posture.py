# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Explicit local export of saved canonical maintenance or change facts."""

import sys
from pathlib import Path

from .artifact_publication import publish_assessment
from .change_conformance import load_change_report
from .maintenance import read_assessment
from .posture import export_posture, render_posture
from .posture_aggregate import aggregate_posture, render_aggregate
from .posture_change import export_change_posture, render_change_posture
from .schema_validation import read_document


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


def cmd_change_posture(args):
    try:
        if (args.output is None) != (args.target is None):
            raise ValueError("Publication requires an explicit protected target")
        source = load_change_report(Path(args.results))
        report = export_change_posture(source.document)
        display = report.to_json() if args.json else render_change_posture(report)
        if args.output is not None:
            if not args.output or not args.target or not Path(args.target).is_dir():
                raise ValueError("Invalid publication paths")
            publish_assessment(report.document, args.target, Path(args.output))
    except (OSError, ValueError, RecursionError):
        print(
            "Unable to export change posture: invalid input or unsafe output; inspect the local results and destination.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(display)
    sys.exit(0)


def cmd_aggregate_posture(args):
    try:
        report = aggregate_posture(
            (read_document(Path(path)) for path in args.report),
            repository_refs=args.repository_ref,
            as_of=args.as_of,
            max_age_hours=args.max_age_hours,
        )
        display = report.to_json() if args.json else render_aggregate(report)
    except (OSError, ValueError, RecursionError):
        print(
            "Unable to aggregate posture: invalid exports, cohort or reporting window; inspect the local inputs.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(display)
    sys.exit(0)


def register(subparsers):
    parser = subparsers.add_parser(
        "posture", help="Export privacy-filtered canonical maintenance or change facts"
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
    change = actions.add_parser("change", help="Project saved canonical change results, offline")
    change.add_argument("--results", required=True, help="Local canonical change-results JSON/YAML")
    change.add_argument("--target", help="Protect this checkout when publishing with --output")
    change.add_argument("--output", help="Create a new private JSON artifact outside --target")
    change.add_argument("--json", action="store_true", help="Print deterministic versioned JSON")
    change.set_defaults(func=cmd_change_posture)
    aggregate = actions.add_parser(
        "aggregate", help="Summarize an explicit cohort of saved exports, offline"
    )
    aggregate.add_argument(
        "--report",
        action="append",
        default=[],
        help="Selected posture JSON/YAML; repeat per snapshot",
    )
    aggregate.add_argument(
        "--repository-ref",
        action="append",
        required=True,
        help="Expected pseudonymous repository reference; repeat for the cohort",
    )
    aggregate.add_argument("--as-of", required=True, help="Explicit timezone-aware reporting time")
    aggregate.add_argument(
        "--max-age-hours",
        type=int,
        default=24,
        help="Reporting freshness window (default: 24 hours)",
    )
    aggregate.add_argument("--json", action="store_true", help="Print deterministic versioned JSON")
    aggregate.set_defaults(func=cmd_aggregate_posture)
