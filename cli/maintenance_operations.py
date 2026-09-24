# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Revalidate canonical maintenance findings before routing read-only previews."""

from __future__ import annotations

from .maintenance import parse_assessment, reassess
from .maintenance_inventory import preview_candidate
from .schema_validation import DocumentError


def preview_operation(target, document, recommendation_id, *, catalog=(), as_of=None):
    prior = parse_assessment(document)
    captured = reassess(target, document)
    if captured.digest != prior.digest:
        raise DocumentError("Stale maintenance assessment; refresh it before previewing")
    current = reassess(target, document, as_of=as_of) if as_of is not None else captured
    selected = next(
        (r for r in current.document["recommendations"] if r["id"] == recommendation_id), None
    )
    if selected is None:
        raise DocumentError("Stale or unknown recommendation; fresh assessment is required")
    if selected["action"] in {"upgrade-cli", "upgrade-pack"}:
        preview = preview_candidate(
            target, current.document["inventory"], selected["component"], catalog=catalog
        )
    else:
        preview = {
            "schema_version": 1,
            "kind": "maintenance-operation-preview",
            "ready": False,
            "operations": [],
            "affected_controls": selected["controls"],
            "protected_customizations": selected["customizations"],
            "target_version": selected["target_version"],
            "decisions": [
                selected["reason"],
                "Route this reviewed finding to "
                + selected["preview"]["operation"]
                + "; policy acceptance and writes require its separate owning workflow.",
            ],
        }
    return {**preview, "assessment_digest": current.digest, "recommendation": selected}
