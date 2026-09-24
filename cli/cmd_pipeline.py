# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Expose shared catalogs and explicit protected provider entry-point generation."""

from __future__ import annotations

import sys
from pathlib import Path

from . import paths
from .gate_catalog import compose_catalog
from .pack_loading import bundled_catalog, contained_file, load_pack
from .pipeline_store import apply_pipeline, check_pipeline, preview_pipeline
from .profiles import load_profile
from .schema_validation import canonical_json
from .version import GOVKIT_VERSION


def cmd_pipeline(args):
    try:
        target = Path(args.target).absolute()
        source = (
            Path(args.profile) if args.profile else contained_file(target, ".govkit/profile.yaml")
        )
        profile = load_profile(source)
        packs = bundled_catalog() + tuple(load_pack(Path(p)) for p in args.pack_source)
        if args.action != "catalog":
            if not args.settings:
                raise ValueError("Pipeline preview/check/generate requires explicit --settings")
            if args.accept_digest and args.action != "generate":
                raise ValueError("--accept-digest is only valid for generate")
            preview = preview_pipeline(source, target, Path(args.settings), packs)
            if args.action == "generate":
                if not args.accept_digest:
                    raise ValueError("Generate requires --accept-digest from a reviewed preview")
                apply_pipeline(preview, args.accept_digest)
                output = {
                    "schema_version": 1,
                    "kind": "pipeline-generated",
                    "digest": preview.digest,
                    "execution": "not-run",
                    "enforcement": "unknown",
                }
            elif args.action == "check":
                output = check_pipeline(preview)
            else:
                output = {**preview.document, "digest": preview.digest}
            if args.json:
                print(canonical_json(output))
            else:
                print(
                    f"Pipeline {args.action}: {output.get('configuration', output.get('digest'))}"
                )
                print(
                    "Execution/enforcement are unverified; configure and verify a trusted caller."
                )
                for operation in preview.operations:
                    print(f"  {operation.action}: {operation.path}")
                if args.action == "preview":
                    print(preview.artifact.document["content"])
            if args.action == "check" and output["configuration"] != "current":
                sys.exit(1)
            return
        if args.settings or args.accept_digest:
            raise ValueError("Catalog does not accept generation settings or an approval digest")
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
        "pipeline",
        help="Inspect gate contracts and preview/check/generate reusable CI entry points",
    )
    parser.add_argument("action", choices=("catalog", "preview", "check", "generate"))
    parser.add_argument("--target", default=".", help=paths.TARGET_HELP)
    parser.add_argument(
        "--profile", help="Explicit accepted profile; defaults to TARGET/.govkit/profile.yaml"
    )
    parser.add_argument(
        "--pack-source", action="append", default=[], help="Additional explicit local pack snapshot"
    )
    parser.add_argument("--json", action="store_true", help="Print the versioned gate catalog")
    parser.add_argument(
        "--settings", help="Explicit accepted runtime pin and execution opt-ins JSON"
    )
    parser.add_argument("--accept-digest", help="Authorize this exact current generation preview")
    parser.set_defaults(func=cmd_pipeline)
