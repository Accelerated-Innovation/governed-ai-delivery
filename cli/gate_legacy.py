# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Load the shared legacy selection at the I/O boundary; keep the adapter pure."""

from copy import deepcopy

from . import paths
from .schema_validation import DocumentError, parse_document, validate_document


def expand_legacy_ci(manifest):
    result = deepcopy(manifest)
    if "ci_catalog" not in result:
        return result
    if result["ci_catalog"] != "builtin:legacy-ci-v1" or "ci" in result.get("variants", {}):
        raise DocumentError("Unknown or ambiguous shared CI catalog reference")
    try:
        with (paths.GOVERNANCE_DIR / "ci/legacy-selection.json").open("rb") as stream:
            content = stream.read(262145)
        if len(content) > 262144:
            raise DocumentError("Shared CI catalog exceeds 256 KiB")
        document = parse_document(content)
        if (
            not isinstance(document, dict)
            or set(document) != {"schema_version", "kind", "variants"}
            or type(document["schema_version"]) is not int
            or document["schema_version"] != 1
            or document["kind"] != "legacy-ci-selection"
            or not isinstance(document["variants"], dict)
            or set(document["variants"]) != {"github", "azure"}
        ):
            raise DocumentError("Invalid shared CI catalog envelope")
        validate_document(
            {
                "agent": "shared-ci",
                "description": "Shared legacy CI selection",
                "variants": {"ci": document["variants"]},
            },
            "agent-manifest",
        )
    except (OSError, ValueError) as exc:
        raise DocumentError(f"Cannot load shared CI catalog: {exc}") from exc
    result.setdefault("variants", {})["ci"] = document["variants"]
    del result["ci_catalog"]
    return result
