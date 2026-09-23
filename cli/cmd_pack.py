# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""govkit pack — explicit composition, portable installation and offline checks."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import paths, version
from .pack_loading import PackError, bundled_catalog, load_pack
from .pack_store import apply_install, execute_check, preview_install, verify_lock
from .schema_validation import DocumentError, canonical_json


def cmd_pack(args: argparse.Namespace) -> None:
    try:
        if args.pack_command == "check":
            arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
            result = execute_check(Path(args.target), args.check_id, tuple(arguments))
            print(result.stdout, end="")
            print(result.stderr, end="", file=sys.stderr)
            sys.exit(result.returncode if result.returncode >= 0 else 1)
        if args.pack_command == "verify":
            result = verify_lock(Path(args.target))
            if args.json:
                print(
                    canonical_json(
                        {
                            "ready": result.ready,
                            "agent": result.agent,
                            "decisions": [asdict(d) for d in result.decisions],
                        }
                    )
                )
            else:
                print("Pack resources verified." if result.ready else "Pack verification failed.")
                for decision in result.decisions:
                    print(f"[{decision.code}] {', '.join(decision.subjects)}: {decision.message}")
            if not result.ready:
                sys.exit(1)
            return
        catalog = bundled_catalog() + tuple(load_pack(Path(source)) for source in args.source)
        if args.pack_command == "list":
            summaries = [pack.summary() for pack in catalog]
            if args.json:
                print(canonical_json({"available": summaries}))
            else:
                for pack in summaries:
                    print(
                        f"{pack['id']} {pack['version']} ({pack['source']}) sha256:{pack['digest']}"
                    )
            return
        target = Path(args.target).absolute()
        source = Path(args.profile) if args.profile else target / ".govkit/profile.yaml"
        preview = preview_install(source, target, catalog, govkit_version=version.GOVKIT_VERSION)
        applied = args.pack_command == "apply"
        if applied:
            apply_install(preview)
        if args.json:
            report = json.loads(preview.to_json())
            report["applied"] = applied
            print(canonical_json(report))
        else:
            print("Pack resources applied." if applied else "Pack preview — no files written.")
            print("Selected: " + (", ".join(p.id for p in preview.resolution.packs) or "none"))
            print(
                "Required checks (not executed): "
                + (", ".join(preview.resolution.required_checks) or "none")
            )
            for decision in preview.resolution.decisions:
                print(f"Unresolved [{decision.code}]: {decision.message}")
            for op in preview.operations:
                print(f"  {op.action}: {op.path} (owner: {op.owner})")
        if not preview.resolution.ready or any(
            op.action == "protected" for op in preview.operations
        ):
            sys.exit(1)
    except (PackError, DocumentError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def register(subparsers) -> None:
    parser = subparsers.add_parser("pack", help="Compose and install explicit capability packs")
    actions = parser.add_subparsers(dest="pack_command", required=True)
    for name in ("list", "preview", "apply", "verify"):
        action = actions.add_parser(name)
        action.add_argument("--json", action="store_true", help="Print a structured report")
        if name != "list":
            action.add_argument("--target", default=".", help=paths.TARGET_HELP)
        if name != "verify":
            action.add_argument(
                "--source",
                action="append",
                default=[],
                help="Explicit local pack directory; repeat for multiple packs (no network fetch)",
            )
        if name in ("preview", "apply"):
            action.add_argument(
                "--profile", help="Input profile (default: TARGET/.govkit/profile.yaml)"
            )
        action.set_defaults(func=cmd_pack)
    check = actions.add_parser("check", help="Run a pinned control without loading a skill")
    check.add_argument("--target", default=".", help=paths.TARGET_HELP + " (place before CHECK_ID)")
    check.add_argument("check_id", metavar="CHECK_ID")
    check.add_argument("arguments", nargs=argparse.REMAINDER, help="Check arguments after --")
    check.set_defaults(func=cmd_pack)
