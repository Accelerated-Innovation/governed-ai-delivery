# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""govkit profile preview/apply — explicit desired configuration and metadata."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import paths
from .profile_store import ProfilePreview, apply_profile, preview_materialization
from .profiles import ProfileError


def _print_preview(preview: ProfilePreview, applied: bool) -> None:
    record = preview.resolution
    print("Profile metadata applied." if applied else "Profile preview — no files written.")
    print("Capability resources are not installed by this command.")
    print(f"Profile digest: {record.profile_digest}")
    print(
        "Capabilities: " + (", ".join(c.id for c in record.plan.selections.capabilities) or "none")
    )
    print(
        "Required checks (not executed): "
        + (", ".join(c.id for c in record.plan.selections.checks) or "none")
    )
    print(
        "Permitted workflows (not routed): "
        + (", ".join(w.id for w in record.profile.workflows) or "none")
    )
    print("Unknown context: " + (", ".join(record.unknowns) or "none"))
    print("Release metadata: not queried; freshness unknown.")
    for contract in record.plan.policy.contracts:
        print(f"Accepted contract: {contract.source.reference} ({', '.join(contract.scope)})")
    for decision in record.plan.selections.unresolved:
        print(f"Unresolved [{decision.code}]: {decision.message}")
    for operation in preview.operations:
        print(f"  {operation.action}: {operation.path}")


def cmd_profile(args: argparse.Namespace) -> None:
    target = Path(args.target).absolute()
    source = Path(args.profile) if args.profile else target / ".govkit/profile.yaml"
    overrides = {key: getattr(args, key) for key in ("agent", "type", "ci", "stack", "level")}
    try:
        preview = preview_materialization(source, target, overrides=overrides)
        applied = args.profile_command == "apply"
        if applied:
            apply_profile(preview)
        if args.json:
            print(preview.to_json(applied=applied))
        else:
            _print_preview(preview, applied)
        if not preview.resolution.ready or any(
            op.action == "protected" for op in preview.operations
        ):
            sys.exit(1)
    except ProfileError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def register(subparsers) -> None:
    parser = subparsers.add_parser("profile", help="Preview or save declarative profile metadata")
    actions = parser.add_subparsers(dest="profile_command", required=True)
    for name in ("preview", "apply"):
        action = actions.add_parser(
            name,
            help="Preview without writes"
            if name == "preview"
            else "Save profile/resolution metadata",
        )
        action.add_argument(
            "--profile", help="Input profile (default: TARGET/.govkit/profile.yaml)"
        )
        action.add_argument("--target", default=".", help=paths.TARGET_HELP)
        action.add_argument("--json", action="store_true", help="Print the structured preview")
        for flag in ("agent", "type", "ci", "stack"):
            action.add_argument(f"--{flag}", help="Assert a value already accepted in the profile")
        action.add_argument("--level", help=argparse.SUPPRESS)
        action.set_defaults(func=cmd_profile)
