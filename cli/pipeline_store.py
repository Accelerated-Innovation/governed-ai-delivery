# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Preview and explicitly authorize two protected generated integration files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .gate_catalog import compose_catalog
from .pack_loading import load_pack
from .pack_store import _destination
from .pipeline_files import bound_pipeline_files
from .pipeline_layout import LOCK
from .pipeline_render import PipelineArtifact, parse_render, parse_settings, render_pipeline
from .pipeline_runtime import read_input
from .profiles import parse_profile
from .schema_validation import DocumentError, canonical_json, content_digest, parse_document


@dataclass(frozen=True)
class PipelineOperation:
    path: str
    action: str
    before: bytes | None
    content: bytes
    mode: int | None
    mtime_ns: int | None

    def summary(self):
        return {
            "path": self.path,
            "action": self.action,
            "before_digest": content_digest(self.before) if self.before is not None else None,
            "proposed_digest": content_digest(self.content),
            "before_mode": self.mode,
            "before_mtime_ns": self.mtime_ns,
        }


@dataclass(frozen=True)
class PipelinePreview:
    source: Path
    target: Path
    settings_source: Path
    packs: tuple
    source_content: bytes
    settings_content: bytes
    artifact: PipelineArtifact
    operations: tuple[PipelineOperation, ...]

    @property
    def document(self):
        return {
            "schema_version": 1,
            "kind": "pipeline-preview",
            "target": str(self.target),
            "profile_source": str(self.source),
            "settings_source": str(self.settings_source),
            "profile_source_digest": content_digest(self.source_content),
            "settings_source_digest": content_digest(self.settings_content),
            "artifact": self.artifact.document,
            "operations": [op.summary() for op in self.operations],
        }

    @property
    def digest(self):
        return content_digest(canonical_json(self.document).encode())

    def to_json(self):
        return canonical_json({**self.document, "digest": self.digest})


def _state(target, relative):
    path = _destination(target, relative)
    if not path.exists():
        return None, None, None
    info = path.stat()
    return read_input(path), info.st_mode & 0o777, info.st_mtime_ns


def preview_pipeline(source, target, settings_source, packs):
    source, target, settings_source = (
        Path(source).absolute(),
        Path(target).absolute(),
        Path(settings_source).absolute(),
    )
    source_content, settings_content = read_input(source), read_input(settings_source)
    profile = parse_profile(parse_document(source_content))
    settings = parse_settings(parse_document(settings_content))
    catalog = compose_catalog(profile, tuple(packs), govkit_version=settings.govkit_version)
    artifact = render_pipeline(catalog, settings)
    if len((artifact.to_json() + "\n").encode()) > 4 * 1024 * 1024:
        raise DocumentError("Proposed generated pipeline metadata is too large to read back")
    operations = preview_artifact_operations(target, artifact)
    return PipelinePreview(
        source,
        target,
        settings_source,
        tuple(packs),
        source_content,
        settings_content,
        artifact,
        operations,
    )


def preview_artifact_operations(target, artifact):
    """Compare a proposed render against managed originals, retaining all protection rules."""
    old_bytes, _, _ = _state(target, LOCK)
    old = None
    if old_bytes is not None:
        try:
            old = parse_render(parse_document(old_bytes))
            if old_bytes != (old.to_json() + "\n").encode():
                raise DocumentError("Noncanonical pipeline metadata")
        except ValueError as exc:
            raise DocumentError(f"Pipeline metadata is protected: {exc}") from exc
        if old.document["path"] != artifact.document["path"]:
            raise DocumentError(
                "Reconcile the existing provider integration before switching providers"
            )
    operations = []
    for relative, content in (
        (artifact.document["path"], artifact.document["content"].encode()),
        (LOCK, (artifact.to_json() + "\n").encode()),
    ):
        before, mode, mtime = _state(target, relative)
        previous = (
            None
            if old is None
            else (old_bytes if relative == LOCK else old.document["content"].encode())
        )
        if before is None:
            action = "create"
        elif previous is None or before != previous:
            action = "protected"
        else:
            action = "preserve" if before == content else "update"
        operations.append(PipelineOperation(relative, action, before, content, mode, mtime))
    return tuple(operations)


def check_pipeline(preview):
    actions = {op.action for op in preview.operations}
    configuration = (
        "drifted"
        if actions & {"protected", "update"}
        else "missing"
        if "create" in actions
        else "current"
    )
    return {
        "schema_version": 1,
        "kind": "pipeline-check",
        "configuration": configuration,
        "execution": "unknown",
        "enforcement": "unknown",
        "activation": "unknown",
        "artifact_digest": preview.artifact.document["digest"],
        "operations": [op.summary() for op in preview.operations],
        "follow_up": preview.artifact.document["requirements"],
    }


def _refresh(preview):
    packs = tuple(load_pack(pack.root, source_kind=pack.source_kind) for pack in preview.packs)
    return preview_pipeline(preview.source, preview.target, preview.settings_source, packs)


def apply_pipeline(preview, approved_digest):
    if approved_digest != preview.digest:
        raise DocumentError("Generate requires the exact preview digest")
    current = _refresh(preview)
    if current.document != preview.document:
        raise DocumentError("Stale pipeline preview; review changed inputs/destinations again")
    if any(op.action == "protected" for op in current.operations):
        raise DocumentError("Existing pipeline files are protected; reconcile edits explicitly")
    pending = [op for op in current.operations if op.action != "preserve"]
    if not pending:
        return
    with bound_pipeline_files(current.target) as files:
        staged, completed, stats, parents = {}, [], {}, {}
        try:
            for op in pending:
                parent = parents[op.path] = files.parent(op.path)
                before, info = parent.read(Path(op.path).name)
                if _bound_state(before, info) != (op.before, op.mode, op.mtime_ns):
                    raise DocumentError("Stale pipeline destination before staging")
                stats[op.path] = info
                staged[op.path] = parent.stage(op.content, info)
            if _refresh(preview).document != current.document:
                raise DocumentError("Stale pipeline inputs after staging; preview again")
            for op in pending:
                files.verify()
                parent, name = parents[op.path], Path(op.path).name
                if _bound_state(*parent.read(name)) != (op.before, op.mode, op.mtime_ns):
                    raise DocumentError("Stale pipeline destination before replacement")
                parent.replace(staged[op.path], name)
                completed.append(op)
                files.verify()
        except (OSError, ValueError) as exc:
            for op in reversed(completed):
                parent, name = parents[op.path], Path(op.path).name
                if parent.read(name)[0] != op.content:
                    raise DocumentError("Concurrent pipeline edit prevented safe rollback") from exc
                if op.before is None:
                    parent.unlink(name)
                else:
                    temporary = parent.stage(op.before, stats[op.path], restore_time=True)
                    parent.replace(temporary, name)
            raise DocumentError(f"Pipeline generation was not applied: {exc}") from exc


def _bound_state(content, info):
    if info is None:
        return None, None, None
    return content, info.st_mode & 0o777, info.st_mtime_ns
