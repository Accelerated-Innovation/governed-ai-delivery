# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Pinned resource installation and independent, explicit check execution.

Locks prove reproducible content/ownership, not authenticated policy approval.
Writes are per-file atomic with rollback on caught failures, not crash recovery
or a transaction against concurrent writers. Check code is explicitly trusted
by selecting its source; this module is not a sandbox for arbitrary pack code.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from packaging.version import InvalidVersion, Version

from . import version
from .agent_layout import AGENT_LAYOUTS
from .fs import stage_bytes
from .native_skills import SKILL_RENDERING, render_skill, skill_aliases
from .pack_loading import PackError, load_pack, safe_relative
from .pack_models import PackDecision, PackResolution, PackSnapshot
from .pack_resolution import resolve_packs
from .profiles import ProjectProfile, load_profile, parse_profile
from .schema_validation import (
    DocumentError,
    canonical_json,
    content_digest,
    read_document,
    validate_document,
)

_LOCK = ".govkit/pack-lock.json"
_PROFILE = ".govkit/profile.yaml"


@dataclass(frozen=True)
class PackOperation:
    path: str
    action: str
    before: bytes | None
    content: bytes | None
    owner: str

    def summary(self):
        return {
            "path": self.path,
            "action": self.action,
            "owner": self.owner,
            "before_digest": content_digest(self.before) if self.before is not None else None,
            "proposed_digest": content_digest(self.content) if self.content is not None else None,
        }


@dataclass(frozen=True)
class PackPreview:
    source: Path
    source_content: bytes
    target: Path
    catalog: tuple[PackSnapshot, ...]
    resolution: PackResolution
    operations: tuple[PackOperation, ...]

    def to_json(self):
        return canonical_json(
            {
                "schema_version": 1,
                "kind": "pack-preview",
                "resolution": json.loads(self.resolution.to_json()),
                "operations": [op.summary() for op in self.operations],
            }
        )


@dataclass(frozen=True)
class LockVerification:
    agent: str | None
    decisions: tuple[PackDecision, ...]

    @property
    def ready(self):
        return not self.decisions


def _destination(target: Path, relative: str) -> Path:
    safe_relative(relative)
    if target.is_symlink() or not target.is_dir():
        raise PackError(f"Target must be an existing directory, not a symlink: {target}")
    current = target
    parts = relative.split("/")
    for index, part in enumerate(parts):
        current /= part
        if current.is_symlink():
            raise PackError(f"Refusing symlink destination: {relative}")
        if current.exists() and index < len(parts) - 1 and not current.is_dir():
            raise PackError(f"Destination parent is not a directory: {relative}")
    if current.exists() and not current.is_file():
        raise PackError(f"Destination is not a regular file: {relative}")
    return current


def _existing(target: Path, relative: str) -> bytes | None:
    path = _destination(target, relative)
    return path.read_bytes() if path.exists() else None


def _resources(
    profile: ProjectProfile,
    resolution: PackResolution,
    *,
    skill_rendering: str | None = SKILL_RENDERING,
):
    """Derive every owned destination from verified manifests, never lock paths."""
    files, owners, checks = {}, {}, {}
    agent = profile.repository.integrations.agent
    native_skills = False
    for pack in resolution.packs:
        prefix = f".govkit/packs/{pack.id}/{pack.digest}"
        for item in pack.files:
            relative = f"{prefix}/{item.path}"
            files[relative], owners[relative] = item.content, pack.id
        source_files = {item.path: item.content for item in pack.files}
        aliases = (
            skill_aliases(
                (skill.install_as, source_files[f"{skill.path}/SKILL.md"]) for skill in pack.skills
            )
            if skill_rendering
            else {}
        )
        for skill in pack.skills:
            if agent not in AGENT_LAYOUTS:
                continue  # Resolution reports missing/unsupported integration.
            native_skills = True
            for item in pack.files:
                if not item.path.startswith(skill.path + "/"):
                    continue
                suffix = item.path[len(skill.path) + 1 :]
                relative = f"{AGENT_LAYOUTS[agent].skills_dir}/{skill.install_as}/{suffix}"
                content = item.content
                if skill_rendering and suffix == "SKILL.md":
                    content = render_skill(
                        content, skill.install_as, aliases, rendering=skill_rendering
                    )
                files[relative] = content.replace(b"{{pack_root}}", prefix.encode())
                owners[relative] = pack.id
        for check in pack.checks:
            checks[check.id] = {
                "pack": pack.id,
                "path": f"{prefix}/{check.path}",
                "required": check.id in resolution.required_checks,
            }
    lock = {
        "schema_version": 1,
        "kind": "pack-lock",
        "govkit_version": resolution.govkit_version,
        "profile_digest": profile.digest,
        "profile": profile.document,
        "agent": agent,
        "packs": [p.summary() for p in resolution.packs],
        "edges": [asdict(edge) for edge in resolution.edges],
        "required_checks": list(resolution.required_checks),
        "checks": checks,
        "files": {name: content_digest(content) for name, content in sorted(files.items())},
        "owners": dict(sorted(owners.items())),
        "execution": "not-run",
    }
    if native_skills and skill_rendering:
        lock["skill_rendering"] = skill_rendering
    return files, owners, lock


def _read_lock(target: Path):
    """Replay the lock from pinned resource closure; native edits stay inspectable."""
    path = _destination(target, _LOCK)
    document = read_document(path)
    validate_document(document, "pack-lock")
    try:
        Version(document["govkit_version"])
    except InvalidVersion as exc:
        raise PackError("Invalid GovKit version in pack lock") from exc
    profile = parse_profile(document["profile"])
    catalog = []
    for entry in document["packs"]:
        root = f".govkit/packs/{entry['id']}/{entry['digest']}"
        _destination(target, root + "/manifest.yaml")
        pack = load_pack(target / root, source_kind=entry["source"])
        if pack.digest != entry["digest"] or pack.id != entry["id"]:
            raise PackError(f"Pinned resource digest mismatch: {entry['id']}")
        if Version(version.GOVKIT_VERSION) < Version(pack.govkit_min_version):
            raise PackError(
                f"{pack.id} requires GovKit >= {pack.govkit_min_version}; running {version.GOVKIT_VERSION}"
            )
        catalog.append(pack)
    resolution = resolve_packs(profile, tuple(catalog), govkit_version=document["govkit_version"])
    if not resolution.ready:
        raise PackError("Pinned lock has unresolved requirements")
    files, owners, expected = _resources(
        profile, resolution, skill_rendering=document.get("skill_rendering")
    )
    if canonical_json(document) != canonical_json(expected):
        raise PackError(
            "Lock does not match its pinned manifests/profile/ownership; reconcile it explicitly"
        )
    if path.read_bytes() != (canonical_json(expected) + "\n").encode():
        raise PackError("Lock metadata was edited; reconcile it explicitly")
    return document, files, owners


def preview_install(
    source: Path, target: Path, catalog: tuple[PackSnapshot, ...], *, govkit_version: str
) -> PackPreview:
    source, target = source.absolute(), target.absolute()
    try:
        _destination(target, _PROFILE)
        source_content = source.read_bytes()
        profile = load_profile(source)
        resolution = resolve_packs(profile, catalog, govkit_version=govkit_version)
        proposed, owners, lock = _resources(profile, resolution)
        old, old_owners = {}, {}
        previous_lock = _existing(target, _LOCK)
        if previous_lock is not None:
            _, old, old_owners = _read_lock(target)
        operations = []
        for relative in sorted(old.keys() | proposed.keys()):
            before = _existing(target, relative)
            content = proposed.get(relative)
            if before is None:
                action = "create" if content is not None else "preserve"
            elif relative not in old or before != old[relative]:
                action = "protected"
            elif content is None:
                action = "remove"
            else:
                action = "preserve" if before == content else "update"
            operations.append(
                PackOperation(
                    relative,
                    action,
                    before,
                    content,
                    owners.get(relative, old_owners.get(relative)),
                )
            )
        lock_content = (canonical_json(lock) + "\n").encode()
        operations.append(
            PackOperation(
                _LOCK,
                "preserve"
                if previous_lock == lock_content
                else "create"
                if previous_lock is None
                else "update",
                previous_lock,
                lock_content,
                "govkit",
            )
        )
        return PackPreview(source, source_content, target, catalog, resolution, tuple(operations))
    except (OSError, DocumentError) as exc:
        raise PackError(f"Cannot preview packs: {exc}") from exc


def _accepted(preview: PackPreview):
    accepted = _destination(preview.target, _PROFILE)
    if not accepted.exists() or load_profile(accepted).digest != preview.resolution.profile_digest:
        raise PackError(
            "Apply requires the same accepted .govkit/profile.yaml; accept the profile explicitly first"
        )


def apply_install(preview: PackPreview) -> None:
    """Re-read every source/destination before writing; apply the lock last."""
    try:
        catalog = tuple(
            load_pack(pack.root, source_kind=pack.source_kind) for pack in preview.catalog
        )
        current = preview_install(
            preview.source,
            preview.target,
            catalog,
            govkit_version=preview.resolution.govkit_version,
        )
        if current != preview:
            raise PackError("Stale pack preview: inputs or destinations changed; preview again")
        if not current.resolution.ready:
            raise PackError("Pack requirements are unresolved; reconcile them before applying")
        if any(op.action == "protected" for op in current.operations):
            raise PackError("Pack resources are protected; reconcile user edits explicitly")
        _accepted(current)
        pending = [op for op in current.operations if op.action != "preserve"]
        staged, completed, created_dirs, stats = {}, [], set(), {}
        try:
            for op in pending:
                destination = _destination(preview.target, op.path)
                if destination.exists():
                    stats[op.path] = destination.stat()
                if op.content is None:
                    continue
                parent = destination.parent
                while not parent.exists():
                    created_dirs.add(parent)
                    parent = parent.parent
                destination.parent.mkdir(parents=True, exist_ok=True)
                staged[op.path] = stage_bytes(destination, op.content)
            if preview.source.read_bytes() != preview.source_content:
                raise PackError("Stale profile source; preview again")
            _accepted(current)
            for op in current.operations:
                if _existing(preview.target, op.path) != op.before:
                    raise PackError("Stale pack destination; preview again")
            for op in pending:
                destination = _destination(preview.target, op.path)
                if op.content is None:
                    destination.unlink()
                else:
                    os.replace(staged[op.path], destination)
                completed.append(op)
        except (OSError, PackError, DocumentError):
            for op in reversed(completed):
                destination = _destination(preview.target, op.path)
                if op.before is None:
                    destination.unlink(missing_ok=True)
                else:
                    restore = stage_bytes(destination, op.before)
                    try:
                        os.replace(restore, destination)
                        stat = stats[op.path]
                        destination.chmod(stat.st_mode & 0o777)
                        os.utime(destination, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                    finally:
                        restore.unlink(missing_ok=True)
            raise
        finally:
            for temporary in staged.values():
                temporary.unlink(missing_ok=True)
            for directory in sorted(created_dirs, key=lambda p: len(p.parts), reverse=True):
                if directory.is_dir() and not any(directory.iterdir()):
                    directory.rmdir()
    except (OSError, DocumentError) as exc:
        raise PackError(f"Packs were not applied: {exc}") from exc


def _verify_lock_snapshot(
    target: Path, *, include_skills: bool = True
) -> tuple[dict | None, LockVerification]:
    """Keep the replayed document together with its profile/resource verification."""
    target = target.absolute()
    try:
        lock, files, _ = _read_lock(target)
        profile = load_profile(_destination(target, _PROFILE))
        if profile.digest != lock["profile_digest"]:
            raise PackError("Accepted profile changed; preview and apply its pack plan")
        decisions = []
        for relative, expected in files.items():
            if not include_skills and not relative.startswith(".govkit/packs/"):
                continue
            if _existing(target, relative) != expected:
                decisions.append(
                    PackDecision(
                        "resource-drift", (relative,), "Missing or modified installed resource"
                    )
                )
        return lock, LockVerification(lock["agent"], tuple(decisions))
    except (OSError, DocumentError, PackError) as exc:
        return None, LockVerification(None, (PackDecision("invalid-lock", (_LOCK,), str(exc)),))


def verify_lock(target: Path, *, include_skills: bool = True) -> LockVerification:
    return _verify_lock_snapshot(target, include_skills=include_skills)[1]


def locked_check_requirements(target: Path) -> tuple[tuple[str, bool], ...]:
    """Expose selected controls only after replaying their pinned lock inputs."""
    lock, _, _ = _read_lock(target.absolute())
    return tuple(
        (identifier, check["required"]) for identifier, check in sorted(lock["checks"].items())
    )


def verified_lock_document(target: Path) -> dict:
    """Read the replayed lock only when current profile and all resources match.

    Planning consumers may advertise native guidance only through this verified
    boundary. Return that exact snapshot, never a later unverified reread. This
    is an observation, not a transaction against concurrent filesystem writers
    or approval/check-execution evidence.
    """
    lock, verification = _verify_lock_snapshot(target)
    if lock is None or not verification.ready:
        raise PackError("Pinned profile/resources are unavailable or modified; run pack verify")
    return lock


def execute_check(
    target: Path,
    check_id: str,
    arguments: tuple[str, ...],
    *,
    working_directory: Path | None = None,
) -> subprocess.CompletedProcess:
    """Execute an explicitly requested pinned Python control, independently of skills."""
    target = target.absolute()
    lock, verification = _verify_lock_snapshot(target, include_skills=False)
    if lock is None or not verification.ready:
        raise PackError(
            "Pinned check verification failed: "
            + "; ".join(d.message for d in verification.decisions)
        )
    if check_id not in lock["checks"]:
        raise PackError(f"No selected executable check: {check_id}")
    script = _destination(target, lock["checks"][check_id]["path"])
    return subprocess.run(
        [sys.executable, "-I", str(script), *arguments],
        cwd=working_directory if working_directory is not None else target,
        capture_output=True,
        text=True,
        check=False,
    )
