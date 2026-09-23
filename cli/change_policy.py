# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Accepted, local execution/measurement configuration for request conformance."""

from __future__ import annotations

from pathlib import Path

from .pack_loading import contained_file
from .schema_validation import DocumentError, content_digest, parse_document, validate_document
from .workflows import _scope


def load_change_policy(target: Path, profile):
    source = profile.document["policy"].get("conformance")
    if not source:
        raise DocumentError("Accepted policy has no conformance configuration")
    with contained_file(target, source["reference"]).open("rb") as stream:
        content = stream.read(65537)
    if len(content) > 65536:
        raise DocumentError("Conformance configuration exceeds 64 KiB")
    document = parse_document(content)
    validate_document(document, "change-policy")
    for collection in ("commands", "artifacts", "constraints"):
        identifiers = [item["id"] for item in document[collection]]
        if len(identifiers) != len(set(identifiers)):
            raise DocumentError(f"Duplicate {collection} IDs")
    for item in document["commands"]:
        if item["id"].startswith(("change:", "artifact:", "govkit:", "approval:", "defect:")):
            raise DocumentError("Commands cannot override built-in or platform approval checks")
    for item in document["impact_rules"] + document["constraints"]:
        item["paths"] = [_scope(p) for p in item["paths"]]
    for item in document["artifacts"]:
        item["references"] = [_scope(p) for p in item["references"]]
    contracts = list(profile.document["policy"].get("contracts", []))
    for transition in profile.document["policy"].get("transitions", []):
        contracts.extend(
            [
                transition,
                *transition["current"],
                *transition["target"],
                *transition.get("exceptions", []),
            ]
        )
    for contract in contracts:
        for scope in contract["scope"]:
            _scope(scope)
    return document, content_digest(content)
