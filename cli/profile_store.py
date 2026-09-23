# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Reviewable, bounded materialization of profile metadata, never pack installation."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .profiles import (
    ProfileError,
    ProfileResolution,
    canonical_json,
    content_digest,
    load_profile,
    load_resolution,
    resolve_profile,
)

_PROFILE = ".govkit/profile.yaml"
_RESOLUTION = ".govkit/resolution.json"


@dataclass(frozen=True)
class MetadataOperation:
    path: str
    action: str
    before: bytes | None
    content: bytes

    def summary(self) -> dict:
        return {
            "path": self.path,
            "action": self.action,
            "before_digest": content_digest(self.before) if self.before is not None else None,
            "proposed_digest": content_digest(self.content),
        }


@dataclass(frozen=True)
class ProfilePreview:
    source: Path
    source_content: bytes
    target: Path
    overrides: tuple[tuple[str, str | None], ...]
    resolution: ProfileResolution
    operations: tuple[MetadataOperation, ...]

    def to_json(self, *, applied: bool = False) -> str:
        return canonical_json(
            {
                "kind": "profile-preview",
                "schema_version": 1,
                "applied": applied,
                "resolution": json.loads(self.resolution.to_json()),
                "operations": [op.summary() for op in self.operations],
            }
        )


def _check_paths(target: Path) -> None:
    if target.is_symlink() or not target.is_dir():
        raise ProfileError(f"Target must be an existing directory, not a symlink: {target}")
    for relative in (".govkit", _PROFILE, _RESOLUTION):
        path = target / relative
        if path.is_symlink():
            raise ProfileError(f"Refusing symlink at {relative}")
    managed = target / ".govkit"
    if managed.exists() and not managed.is_dir():
        raise ProfileError(".govkit must be a directory")


def _existing(path: Path) -> bytes | None:
    if not path.exists():
        return None
    if not path.is_file():
        raise ProfileError(f"Metadata destination is not a regular file: {path}")
    return path.read_bytes()


def preview_materialization(
    source: Path,
    target: Path,
    *,
    overrides: dict[str, str | None] | None = None,
) -> ProfilePreview:
    """Read inputs and both destinations. Never mkdir, install, fetch or write."""
    source, target = source.absolute(), target.absolute()
    try:
        _check_paths(target)
        source_content = source.read_bytes()
        profile = load_profile(source)
        resolution = resolve_profile(profile, overrides=overrides)
        operations = []
        for relative, proposed in (
            (_PROFILE, source_content),
            (_RESOLUTION, (resolution.to_json() + "\n").encode("utf-8")),
        ):
            path = target / relative
            before = _existing(path)
            action = "create"
            if before is not None:
                action = "protected"
                try:
                    if relative == _PROFILE:
                        if load_profile(path).digest == profile.digest:
                            action, proposed = "preserve", before
                    else:
                        existing = load_resolution(path)
                        if before == (existing.to_json() + "\n").encode("utf-8"):
                            action = "preserve" if before == proposed else "update"
                except ProfileError:
                    pass  # Invalid or edited content remains protected.
            operations.append(MetadataOperation(relative, action, before, proposed))
        return ProfilePreview(
            source,
            source_content,
            target,
            tuple((overrides or {}).items()),
            resolution,
            tuple(operations),
        )
    except OSError as exc:
        raise ProfileError(f"Cannot preview profile metadata: {exc}") from exc


def _stage(path: Path, content: bytes) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=".govkit-profile-", dir=path.parent)
    staged = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            staged.chmod(path.stat().st_mode & 0o777)
        return staged
    except BaseException:
        staged.unlink(missing_ok=True)
        raise


def apply_profile(preview: ProfilePreview) -> None:
    """Apply an explicit fresh preview, preserving edits and the legacy marker.

    Recompute from source and destinations rather than trusting serialized actions.
    Individual replacements are atomic; caught write failures roll back completed
    replacements. This is not a cross-process transaction or crash recovery journal.
    """
    current = preview_materialization(
        preview.source, preview.target, overrides=dict(preview.overrides)
    )
    if current != preview:
        raise ProfileError("Stale profile preview: inputs or destinations changed; preview again")
    if not current.resolution.ready:
        raise ProfileError("Profile has unresolved decisions; reconcile them before applying")
    if any(op.action == "protected" for op in current.operations):
        raise ProfileError(
            "Profile metadata is protected; edit/reconcile it explicitly before applying"
        )
    pending = [op for op in current.operations if op.action != "preserve"]
    if not pending:
        return
    managed = preview.target / ".govkit"
    created_directory = not managed.exists()
    staged: list[tuple[MetadataOperation, Path]] = []
    completed: list[MetadataOperation] = []
    try:
        managed.mkdir(exist_ok=True)
        _check_paths(preview.target)
        for operation in pending:
            destination = preview.target / operation.path
            staged.append((operation, _stage(destination, operation.content)))
        # Detect intervening changes after staging, before replacing any file.
        if preview.source.read_bytes() != preview.source_content:
            raise ProfileError("Stale profile source; preview again")
        _check_paths(preview.target)
        for operation in current.operations:
            if _existing(preview.target / operation.path) != operation.before:
                raise ProfileError("Stale metadata destination; preview again")
        for operation, temporary in staged:
            os.replace(temporary, preview.target / operation.path)
            completed.append(operation)
    except (OSError, ProfileError) as exc:
        for operation in reversed(completed):
            destination = preview.target / operation.path
            if operation.before is None:
                destination.unlink(missing_ok=True)
            else:
                restore = _stage(destination, operation.before)
                try:
                    os.replace(restore, destination)
                finally:
                    restore.unlink(missing_ok=True)
        raise ProfileError(f"Profile metadata was not applied: {exc}") from exc
    finally:
        for _, temporary in staged:
            temporary.unlink(missing_ok=True)
        if created_directory and managed.is_dir() and not any(managed.iterdir()):
            managed.rmdir()
