# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Expose shared catalogs and explicit protected provider entry-point generation."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from . import paths
from .artifact_publication import publish_assessment
from .gate_catalog import compose_catalog
from .maintenance import assess_repository, parse_assessment, read_assessment, render_assessment
from .pack_loading import bundled_catalog, contained_file, load_pack
from .pipeline_assessment import upgrade_integration_preview
from .pipeline_evidence import collect_evidence
from .pipeline_runtime import read_input
from .pipeline_store import apply_pipeline, check_pipeline, preview_pipeline
from .profiles import load_profile
from .release_metadata import refresh_metadata
from .schema_validation import canonical_json, parse_document
from .version import GOVKIT_VERSION


def cmd_pipeline(args):
    try:
        incompatible = {
            "evidence": ("assessment", "recommendation", "metadata", "release_source"),
            "assess": ("assessment", "recommendation"),
            "upgrade-preview": ("change_report", "observation", "metadata", "release_source"),
        }
        for name in incompatible.get(args.action, ()):
            value = getattr(args, name)
            if value is not None and value != []:
                raise ValueError(
                    f"--{name.replace('_', '-')} is not valid for pipeline {args.action}"
                )
        target = Path(args.target).absolute()
        source = (
            Path(args.profile) if args.profile else contained_file(target, ".govkit/profile.yaml")
        )
        profile = load_profile(source)
        packs = bundled_catalog() + tuple(load_pack(Path(p)) for p in args.pack_source)
        if args.action in {"evidence", "assess", "upgrade-preview"}:
            if not args.settings or args.accept_digest or args.profile:
                raise ValueError(
                    "Evidence/assessment/upgrade-preview require --settings, target policy and no generation approval"
                )
            as_of = args.as_of or datetime.now(timezone.utc).isoformat()
            if args.action == "upgrade-preview":
                if not args.assessment or not args.recommendation:
                    raise ValueError("Upgrade preview requires --assessment and --recommendation")
                output = upgrade_integration_preview(
                    target,
                    read_assessment(Path(args.assessment)).document,
                    args.recommendation,
                    Path(args.settings),
                    catalog=packs,
                    as_of=as_of,
                )
            else:
                evidence = collect_evidence(
                    target,
                    Path(args.settings),
                    packs,
                    as_of=as_of,
                    change_report=parse_document(read_input(Path(args.change_report)))
                    if args.change_report
                    else None,
                    observation=parse_document(read_input(Path(args.observation)))
                    if args.observation
                    else None,
                )
                if args.action == "evidence":
                    output = evidence.to_document()
                else:
                    metadata = tuple(parse_document(read_input(Path(p))) for p in args.metadata)
                    metadata += tuple(
                        refresh_metadata(profile, name, as_of=as_of) for name in args.release_source
                    )
                    output = assess_repository(
                        target, as_of=as_of, metadata=metadata, ci_report=evidence.to_document()
                    ).document
            if args.output:
                publish_assessment(output, target, Path(args.output))
            if args.json or args.action != "assess":
                print(canonical_json(output))
            else:
                print(render_assessment(parse_assessment(output)))
            if args.action == "evidence" and output["exit_code"]:
                sys.exit(output["exit_code"])
            return
        if any(
            (
                args.output,
                args.change_report,
                args.observation,
                args.as_of,
                args.metadata,
                args.release_source,
                args.assessment,
                args.recommendation,
            )
        ):
            raise ValueError("Assessment inputs require evidence, assess or upgrade-preview")
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
    parser.add_argument(
        "action",
        choices=(
            "catalog",
            "preview",
            "check",
            "generate",
            "evidence",
            "assess",
            "upgrade-preview",
        ),
    )
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
    parser.add_argument("--as-of", help="Explicit assessment time (defaults to current UTC)")
    parser.add_argument(
        "--change-report", help="Explicit change-results JSON from the trusted CI run"
    )
    parser.add_argument("--observation", help="Caller-approved provider-observation JSON export")
    parser.add_argument(
        "--metadata", action="append", default=[], help="Explicit cached release metadata"
    )
    parser.add_argument(
        "--release-source",
        action="append",
        default=[],
        help="Explicitly refresh this accepted release source during assess",
    )
    parser.add_argument(
        "--output", help="Create a new report artifact outside the target; never overwrite"
    )
    parser.add_argument("--assessment", help="Prior canonical assessment for a selected upgrade")
    parser.add_argument("--recommendation", help="Selected upgrade recommendation ID")
    parser.set_defaults(func=cmd_pipeline)
