# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Explicit preview, digest-bound application and protected rollback."""

from __future__ import annotations

import sys
from pathlib import Path

from . import paths
from .maintenance import read_assessment
from .migration import apply_migration, preview_migration, rollback_migration
from .schema_validation import canonical_json


def cmd_migrate(args):
    try:
        target = Path(args.target)
        if args.action == "rollback":
            if not args.expected_digest:
                raise ValueError("Rollback requires --expected-digest from the migration preview")
            result = rollback_migration(target, expected_digest=args.expected_digest)
        else:
            preview = preview_migration(
                target,
                profile_path=Path(args.profile) if args.profile else None,
                assessment=read_assessment(Path(args.assessment)).document
                if args.assessment
                else None,
            )
            result = preview.document
            if args.action == "apply":
                if (
                    not args.profile
                    or args.expected_digest
                    not in {preview.digest, preview.document["migration_id"]}
                    or not args.expected_digest
                ):
                    raise ValueError(
                        "Apply requires an accepted --profile and the exact preview --expected-digest"
                    )
                result = apply_migration(preview)
        if args.json:
            print(canonical_json(result))
        elif args.action == "preview":
            print("Migration preview — no target files written.")
            print(f"Preview digest: {preview.digest}")
            print(
                "Capabilities: "
                + ", ".join(c["id"] for c in result["proposed_profile"]["capabilities"])
            )
            for decision in result["decisions"]:
                print("Review: " + decision)
            for operation in result["operations"]:
                print(f"  {operation['action']}: {operation['path']}")
            for item in result["maintenance"]["recommendations"]:
                print(f"  Maintenance ({item['urgency']}): {item['action']} — {item['reason']}")
            print("Use --json to review proposed_profile, controls and observed evidence.")
        else:
            print(
                "Migration metadata applied."
                if args.action == "apply"
                else "Migration rolled back."
            )
            if args.action == "apply":
                print(
                    "Enforcement parity remains unverified; inspect the verification report with --json."
                )
                print(
                    f"Maintenance: {len(result['maintenance']['resolved'])} resolved; {len(result['maintenance']['remaining'])} remaining; {len(result['maintenance']['unverified'])} unverified."
                )
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def register(subparsers):
    parser = subparsers.add_parser(
        "migrate", help="Preview safe legacy migration; apply only reviewed operations"
    )
    parser.add_argument(
        "action", nargs="?", default="preview", choices=("preview", "apply", "rollback")
    )
    parser.add_argument("--target", default=".", help=paths.TARGET_HELP)
    parser.add_argument("--profile", help="Explicit reviewed profile; never inferred acceptance")
    parser.add_argument(
        "--assessment",
        help="Optional saved canonical maintenance assessment; rechecked before preview/apply",
    )
    parser.add_argument(
        "--expected-digest", help="Exact reviewed preview digest required for writes"
    )
    parser.add_argument(
        "--json", action="store_true", help="Print structured proposal or verification"
    )
    parser.set_defaults(func=cmd_migrate)
