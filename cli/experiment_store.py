# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Bounded, read-only reads of one feature's experiment records (ADR 0020).

Reads stay inside the target, never follow symlinks and stop at fixed byte
limits. Unreadable inputs become findings or unverifiable digests rather than
exceptions. Nothing is written.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .experiments import Assessment, assess, parse_preflight_outcome
from .pack_loading import contained_file
from .schema_validation import DocumentError, parse_document

RECORD_NAME = "experiments.yaml"
PREFLIGHT_NAME = "architecture_preflight.md"
MAX_DOCUMENT_BYTES = 256 * 1024
MAX_HASHED_BYTES = 8 * 1024 * 1024
_CHUNK = 64 * 1024


@dataclass(frozen=True)
class FeatureExperiments:
    feature_dir: str
    assessment: Assessment


def assess_feature(
    target: Path, feature_dir: Path, *, now: datetime | None = None
) -> FeatureExperiments | None:
    """Assess a feature's preflight outcome and experiment records.

    Returns None when the feature declares neither a preflight_outcome block
    nor an experiments.yaml, so callers can leave existing output unchanged.
    """
    target = target.resolve()
    feature = feature_dir.resolve().relative_to(target).as_posix()
    default_record = f"{feature}/{RECORD_NAME}"

    outcome: dict | str | None = None
    preflight = f"{feature}/{PREFLIGHT_NAME}"
    if _present(target, preflight):
        text = _read_document(target, preflight)
        if isinstance(text, DocumentError):
            outcome = f"{preflight}: {text}"
        else:
            try:
                outcome = parse_preflight_outcome(text)
            except DocumentError as exc:
                outcome = f"{preflight}: {exc}"

    if outcome is None and not _present(target, default_record):
        return None

    wanted = {default_record}
    if isinstance(outcome, dict):
        wanted.update(r["record"] for r in outcome.get("relies_on", []) if "record" in r)
    records: dict[str, dict | str] = {}
    for path in sorted(wanted):
        if _present(target, path):
            records[path] = _load_record(target, path)

    assessment = assess(
        outcome,
        records,
        default_record=default_record,
        read_digest=lambda path: _digest(target, path),
        now=now,
    )
    return FeatureExperiments(feature, assessment)


def _present(target: Path, relative: str) -> bool:
    path = target / relative
    return path.is_symlink() or path.exists()


def _read_document(target: Path, relative: str) -> str | DocumentError:
    try:
        path = contained_file(target, relative)
        with path.open("rb") as stream:
            content = stream.read(MAX_DOCUMENT_BYTES + 1)
        if len(content) > MAX_DOCUMENT_BYTES:
            return DocumentError(f"exceeds the {MAX_DOCUMENT_BYTES}-byte limit")
        return content.decode("utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        return DocumentError(str(exc))


def _load_record(target: Path, relative: str) -> dict | str:
    text = _read_document(target, relative)
    if isinstance(text, DocumentError):
        return f"{relative}: {text}"
    try:
        document = parse_document(text)
    except DocumentError as exc:
        return f"{relative}: {exc}"
    if not isinstance(document, dict):
        return f"{relative}: an experiment set must be a mapping"
    return document


def _digest(target: Path, relative: str) -> str | None:
    """SHA-256 of a contained regular file, or None when it cannot be verified."""
    try:
        path = contained_file(target, relative)
        digest, size = hashlib.sha256(), 0
        with path.open("rb") as stream:
            while chunk := stream.read(_CHUNK):
                size += len(chunk)
                if size > MAX_HASHED_BYTES:
                    return None
                digest.update(chunk)
        return digest.hexdigest()
    except (OSError, ValueError):
        return None
