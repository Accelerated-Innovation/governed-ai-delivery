# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Expose read-only gate declarations; provider generation is a separate increment."""

from __future__ import annotations

import sys
from pathlib import Path

from . import paths
from .gate_catalog import compose_catalog
from .pack_loading import bundled_catalog, contained_file, load_pack
from .profiles import load_profile
from .version import GOVKIT_VERSION


def cmd_pipeline(args):
    try:
        target = Path(args.target).absolute()
        source = (
            Path(args.profile) if args.profile else contained_file(target, ".govkit/profile.yaml")
        )
        profile = load_profile(source)
        packs = bundled_catalog() + tuple(load_pack(Path(p)) for p in args.pack_source)
        catalog = compose_catalog(profile, packs, govkit_version=GOVKIT_VERSION)
        if args.json:
            print(catalog.to_json())
        else:
            document = catalog.document
            print(f"Gate catalog (read-only): {document['repository']}")
            print("Execution: not-run; enforcement: unknown. Catalog readiness is not runnable CI.")
            for gate in document["gates"]:
                policy = "blocking when applicable" if gate["blocking"] else "advisory"
                print(f"  {gate['id']}: {policy}")
            for decision in document["decisions"]:
                print(f"  Unresolved [{decision['code']}]: {decision['message']}")
        if not catalog.ready:
            sys.exit(1)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def register(subparsers):
    parser = subparsers.add_parser(
        "pipeline", help="Inspect shared gate contracts without generating CI"
    )
    parser.add_argument("action", choices=("catalog",))
    parser.add_argument("--target", default=".", help=paths.TARGET_HELP)
    parser.add_argument(
        "--profile", help="Explicit accepted profile; defaults to TARGET/.govkit/profile.yaml"
    )
    parser.add_argument(
        "--pack-source", action="append", default=[], help="Additional explicit local pack snapshot"
    )
    parser.add_argument("--json", action="store_true", help="Print the versioned gate catalog")
    parser.set_defaults(func=cmd_pipeline)
