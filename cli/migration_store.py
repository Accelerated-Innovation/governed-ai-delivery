# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Bounded snapshots and reversible, create-only migration writes."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from .fs import stage_bytes
from .pack_loading import safe_relative
from .schema_validation import DocumentError, canonical_json, content_digest

EXCLUDED = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}


@dataclass(frozen=True)
class FileState:
    content: bytes
    mode: int
    mtime_ns: int

    def summary(self):
        return {
            "digest": content_digest(self.content),
            "mode": self.mode,
            "mtime_ns": self.mtime_ns,
        }


@dataclass(frozen=True)
class Snapshot:
    files: dict[str, FileState]
    directories: tuple[str, ...]

    @property
    def digest(self):
        return content_digest(
            canonical_json(
                {
                    "files": {p: f.summary() for p, f in sorted(self.files.items())},
                    "directories": self.directories,
                }
            ).encode()
        )


def capture(target: Path) -> Snapshot:
    if target.is_symlink() or not target.is_dir():
        raise DocumentError("Migration target must be a real directory")
    files, directories, count, total = {}, [], 0, 0

    def visit(directory, depth):
        nonlocal count, total
        if depth > 20:
            raise DocumentError("Migration snapshot exceeds depth limit")
        with os.scandir(directory) as entries:
            for entry in entries:
                count += 1
                if count > 8192:
                    raise DocumentError("Migration snapshot exceeds entry limit")
                if entry.name in EXCLUDED:
                    continue
                path = Path(entry.path)
                name = path.relative_to(target).as_posix()
                safe_relative(name)
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(metadata.st_mode):
                    directories.append(name)
                    visit(path, depth + 1)
                elif stat.S_ISREG(metadata.st_mode):
                    with path.open("rb") as stream:
                        content = stream.read(2 * 1024 * 1024 + 1)
                    total += len(content)
                    if (
                        len(content) > 2 * 1024 * 1024
                        or total > 64 * 1024 * 1024
                        or len(files) >= 4096
                    ):
                        raise DocumentError("Migration snapshot exceeds content/file limits")
                    files[name] = FileState(
                        content, stat.S_IMODE(metadata.st_mode), metadata.st_mtime_ns
                    )
                else:
                    raise DocumentError(f"Migration snapshot cannot verify nonregular path: {name}")

    try:
        visit(target, 0)
    except OSError as exc:
        raise DocumentError("Migration snapshot is unavailable") from exc
    return Snapshot(files, tuple(sorted(directories)))


def materialize(target: Path, snapshot: Snapshot):
    target.mkdir()
    for name in snapshot.directories:
        (target / name).mkdir(parents=True, exist_ok=True)
    for name, file in snapshot.files.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file.content)
        path.chmod(file.mode)
        os.utime(path, ns=(file.mtime_ns, file.mtime_ns))


def write_changes(
    target: Path,
    before: Snapshot,
    additions: dict[str, FileState],
    *,
    removals=(),
    prune_directories=(),
):
    """Atomic per-file replacement with caught-failure rollback, not crash recovery.

    Caller derives all paths from fresh verified previews. No serialized actions
    are executed. Every existing destination outside explicit removals is protected.
    """
    if capture(target) != before:
        raise DocumentError("Stale migration inputs; preview again")
    for name in (*additions, *removals):
        safe_relative(name)
    if set(additions) & (before.files.keys() - set(removals)):
        raise DocumentError("Migration cannot overwrite existing content")
    for name in additions:
        path = target / name
        for parent in (path, *path.parents):
            if parent == target:
                break
            if parent.is_symlink():
                raise DocumentError("Migration cannot write through a symlink")
        if path.exists() and name not in removals:
            if not (path.is_dir() and name in prune_directories):
                raise DocumentError(
                    "Migration destination already exists outside its owned snapshot"
                )
    completed, removed, created_dirs, removed_dirs = [], [], set(), []
    try:
        for name in removals:
            (target / name).unlink()
            removed.append(name)
        for name in sorted(prune_directories, key=lambda p: len(p.split("/")), reverse=True):
            path = target / name
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
                removed_dirs.append(name)
        # A flat marker can now become a directory, or its empty directory can
        # become the original file on rollback. Never remove a nonempty directory.
        for name, file in additions.items():
            path = target / name
            if path.is_dir():
                path.rmdir()
            parent = path.parent
            while not parent.exists():
                created_dirs.add(parent)
                parent = parent.parent
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = stage_bytes(path, file.content)
            try:
                temporary.chmod(file.mode)
                os.utime(temporary, ns=(file.mtime_ns, file.mtime_ns))
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
            completed.append(name)
    except (OSError, ValueError) as exc:
        for name in reversed(completed):
            (target / name).unlink(missing_ok=True)
        for directory in sorted(created_dirs, key=lambda p: len(p.parts), reverse=True):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
        for name in removed:
            path = target / name
            if path.is_dir():
                path.rmdir()
            file = before.files[name]
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = stage_bytes(path, file.content)
            try:
                temporary.chmod(file.mode)
                os.utime(temporary, ns=(file.mtime_ns, file.mtime_ns))
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        for name in removed_dirs:
            (target / name).mkdir(parents=True, exist_ok=True)
        raise DocumentError(f"Migration operation rolled back after write failure: {exc}") from exc
