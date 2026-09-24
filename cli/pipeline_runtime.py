# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Execute one common-engine call from caller-prepared, explicitly bound inputs."""

from __future__ import annotations

import base64
import binascii
import os
import re
import sys
from pathlib import Path

from .change_conformance import inspect_change
from .pack_store import verified_lock_document
from .schema_validation import (
    DocumentError,
    canonical_json,
    content_digest,
    parse_document,
    validate_document,
)
from .version import GOVKIT_VERSION
from .workflows import parse_request


def read_input(path: Path, *, limit=4 * 1024 * 1024):
    """Bound a caller-named local input before parsing it."""
    with path.open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise DocumentError(f"Pipeline input exceeds {limit} bytes: {path}")
    return content


def run_bound(
    binding, target, policy_target, request_path, base, *, pack_arguments=None, observed_at=None
):
    validate_document(binding, "pipeline-binding")
    if binding["govkit_version"] != GOVKIT_VERSION:
        raise DocumentError("Installed GovKit does not match the exact pipeline runtime pin")
    if pack_arguments is not None and not isinstance(pack_arguments, dict):
        raise DocumentError("Pack arguments must be a mapping of check IDs to string arrays")
    target, policy_target, request_path = Path(target), Path(policy_target), Path(request_path)
    if not all(p.is_absolute() for p in (target, policy_target, request_path)):
        raise DocumentError("Pipeline checkout/request paths must be absolute")
    if not isinstance(base, str) or not re.fullmatch(r"(?:[a-fA-F0-9]{40}|[a-fA-F0-9]{64})", base):
        raise DocumentError("Pipeline base must be a full trusted Git commit SHA")
    lock = verified_lock_document(policy_target)
    if lock["govkit_version"] != binding["govkit_version"]:
        raise DocumentError("Trusted pack lock differs from the exact pipeline runtime pin")
    if lock["profile_digest"] != binding["profile_digest"]:
        raise DocumentError("Trusted policy differs from the pipeline profile pin")
    if content_digest(canonical_json(lock["packs"]).encode()) != binding["packs_digest"]:
        raise DocumentError("Trusted pack closure differs from pipeline pins")
    return inspect_change(
        target,
        parse_request(parse_document(read_input(request_path))),
        base=base,
        policy_target=policy_target,
        observed_at=observed_at,
        execute_checks=tuple(binding["execute_checks"]),
        pack_arguments=pack_arguments,
        allow_inapplicable_checks=True,
    )


def main():
    try:
        required = ("BINDING", "TARGET", "POLICY_TARGET", "REQUEST", "BASE")
        values = {name: os.environ.get("GOVKIT_" + name, "") for name in required}
        if any(not value for value in values.values()):
            raise DocumentError("Missing required GovKit pipeline input")
        if len(values["BINDING"]) > 65536:
            raise DocumentError("Pipeline binding is too large")
        binding = parse_document(base64.b64decode(values["BINDING"], validate=True))
        arguments = None
        path = os.environ.get("GOVKIT_PACK_ARGUMENTS", "")
        if path:
            if not Path(path).is_absolute():
                raise DocumentError("Pack arguments path must be absolute")
            arguments = parse_document(read_input(Path(path)))
        report = run_bound(
            binding,
            values["TARGET"],
            values["POLICY_TARGET"],
            values["REQUEST"],
            values["BASE"],
            pack_arguments=arguments,
            observed_at=os.environ.get("GOVKIT_OBSERVED_AT") or None,
        )
        print(report.to_json())
        return report.exit_code
    except (OSError, ValueError, binascii.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
