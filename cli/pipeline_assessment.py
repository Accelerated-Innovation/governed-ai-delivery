# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Explicit assessment publication and read-only candidate integration proposals."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from packaging.version import Version

from .gate_catalog import compose_catalog
from .maintenance_operations import preview_operation
from .pack_loading import load_pack
from .pipeline_layout import LOCK
from .pipeline_render import parse_render, parse_settings, render_pipeline
from .pipeline_runtime import read_input
from .pipeline_store import preview_artifact_operations
from .profiles import load_profile
from .schema_validation import DocumentError, parse_document


def upgrade_integration_preview(
    target, document, recommendation_id, settings_source, *, catalog=(), as_of=None
):
    """Compose the selected upgrade's gate/configuration delta without granting writes."""
    target = Path(target).absolute()
    proposed = preview_operation(target, document, recommendation_id, catalog=catalog, as_of=as_of)
    selected = proposed["recommendation"]
    if selected["action"] not in {"upgrade-cli", "upgrade-pack"}:
        raise DocumentError(
            "Integration upgrade preview requires a selected upgrade recommendation"
        )
    settings = parse_settings(parse_document(read_input(Path(settings_source))))
    lock = document["inventory"]["locked_packs"]
    packs = []
    for entry in lock:
        if entry["id"] == selected["component"]:
            candidates = [
                p
                for p in catalog
                if p.id == entry["id"] and Version(p.version) == Version(selected["target_version"])
            ]
            if len(candidates) != 1:
                raise DocumentError("Supply exactly one explicit selected candidate pack snapshot")
            packs.extend(candidates)
        else:
            packs.append(
                load_pack(
                    target / f".govkit/packs/{entry['id']}/{entry['digest']}",
                    source_kind=entry["source"],
                )
            )
    if selected["component"] == "govkit":
        settings = replace(settings, govkit_version=selected["target_version"])
    artifact = render_pipeline(
        compose_catalog(
            load_profile(target / ".govkit/profile.yaml"),
            tuple(packs),
            govkit_version=settings.govkit_version,
        ),
        settings,
    )
    operations = preview_artifact_operations(target, artifact)
    previous = next(op.before for op in operations if op.path == LOCK)
    old = parse_render(parse_document(previous)).document if previous else None
    gates = {g["id"]: g for g in artifact.document["catalog"]["gates"]}
    old_gates = {g["id"]: g for g in old["catalog"]["gates"]} if old else {}
    binding_changed = old is None or old["binding"] != artifact.document["binding"]
    return {
        **proposed,
        "integration": {
            "artifact": artifact.document,
            "operations": [op.summary() for op in operations if op.action != "preserve"],
            "affected_gates": sorted(
                key
                for key in gates.keys() | old_gates.keys()
                if binding_changed or gates.get(key) != old_gates.get(key)
            ),
            "binding_changed": binding_changed,
            "permissions": [
                "Read-only checkout/provider export collection; artifact publication requires caller-managed permissions."
            ],
            "follow_up": [
                "Review the selected package/resource upgrade through its owning workflow.",
                "After upgrading, review new pipeline settings and a fresh pipeline preview; only its accepted digest authorizes generation.",
                "Recheck protected caller permissions, required checks and reviewer policies, then collect fresh CI evidence.",
            ],
            "writes_authorized": False,
        },
    }
