# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Read-only release/resource inventory and explicitly isolated metadata refresh."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import paths
from .fs import stage_bytes
from .maintenance_inventory import inventory_repository, preview_candidate, read_bounded
from .pack_loading import contained_file, load_pack
from .profiles import load_profile
from .release_metadata import refresh_metadata
from .schema_validation import canonical_json, parse_document


def cmd_maintain(args):
    try:
        target = Path(args.target).absolute()
        as_of = args.as_of or datetime.now(timezone.utc).isoformat()
        if args.action == "refresh":
            if not args.output or not args.release_source:
                raise ValueError(
                    "Refresh requires --release-source and --output outside the target"
                )
            output = Path(args.output).absolute()
            if output.resolve().is_relative_to(target.resolve()) or output.is_symlink():
                raise ValueError(
                    "Metadata cache output must be outside the repository and not a symlink"
                )
            profile = load_profile(contained_file(target, ".govkit/profile.yaml"))
            report = refresh_metadata(profile, args.release_source, as_of=as_of)
            temporary = stage_bytes(output, (canonical_json(report) + "\n").encode())
            try:
                temporary.chmod(0o600)
                os.replace(temporary, output)
            finally:
                temporary.unlink(missing_ok=True)
        elif args.action == "preview":
            if not args.inventory or not args.component:
                raise ValueError("Preview requires --inventory and --component")
            inventory = parse_document(read_bounded(Path(args.inventory)))
            report = preview_candidate(
                target,
                inventory,
                args.component,
                catalog=tuple(load_pack(Path(path)) for path in args.pack_source),
            )
        else:
            documents = tuple(parse_document(read_bounded(Path(path))) for path in args.metadata)
            report = inventory_repository(target, as_of=as_of, metadata=documents).document
        if args.json:
            print(canonical_json(report))
        elif args.action == "inventory":
            print(f"Version/resource inventory (read-only): {report['repository']}")
            print(
                f"Running CLI: {report['running_cli']}; recorded install: {report['recorded_install'] or 'unknown'}"
            )
            print(
                f"Lock/resources: {report['lock_verification']}; not proof of enforcement or newest release."
            )
            for candidate in report["candidates"]:
                print(
                    f"  {candidate['component']}: newest known {candidate['newest_known'] or 'unknown'}; candidate {candidate['selected_target'] or 'none'}; freshness {candidate['freshness']}; policy {candidate['current_policy_state']}"
                )
            for resource in report["resources"]:
                if resource["state"] != "matching":
                    print(f"  {resource['action']}: {resource['path']} ({resource['state']})")
            for problem in report["problems"]:
                print(f"  Unknown/incomplete: {problem}")
        elif args.action == "refresh":
            print(f"Release metadata cache: {report['lookup_status']} — {args.output}")
        else:
            print(
                f"Candidate preview (read-only): {report['component']} → {report['target_version']}"
            )
            for operation in report["operations"]:
                print(f"  {operation['action']}: {operation['path']}")
            for decision in report["decisions"]:
                print(f"  Review: {decision}")
        if args.action == "refresh" and report["lookup_status"] in {"failed", "unavailable"}:
            sys.exit(1)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def register(subparsers):
    parser = subparsers.add_parser(
        "maintain", help="Inventory versions/resources and preview known release candidates"
    )
    parser.add_argument(
        "action", nargs="?", default="inventory", choices=("inventory", "preview", "refresh")
    )
    parser.add_argument("--target", default=".", help=paths.TARGET_HELP)
    parser.add_argument("--as-of", help="Explicit timezone-aware assessment time (defaults to now)")
    parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        help="Approved local metadata document; never fetched implicitly",
    )
    parser.add_argument(
        "--inventory", help="Saved inventory for a stale-input-protected candidate preview"
    )
    parser.add_argument("--component", help="Component ID from the inventory candidates")
    parser.add_argument(
        "--pack-source", action="append", default=[], help="Explicit local candidate pack directory"
    )
    parser.add_argument("--release-source", help="Approved source ID for explicit refresh")
    parser.add_argument(
        "--output", help="Explicit metadata cache destination outside the repository"
    )
    parser.add_argument("--json", action="store_true", help="Print the versioned record")
    parser.set_defaults(func=cmd_maintain)
