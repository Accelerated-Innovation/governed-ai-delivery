# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Bounded local Git observations, including staged, dirty and untracked files."""

from __future__ import annotations

import os
import stat
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .pack_loading import contained_file, safe_relative
from .schema_validation import canonical_json, content_digest


@dataclass(frozen=True)
class ChangedPath:
    path: str
    status: str
    before: str | None
    after: str | None


@dataclass(frozen=True)
class ChangeSnapshot:
    base: str | None
    revision: str | None
    changes: tuple[ChangedPath, ...]
    files: dict[str, bytes] = field(repr=False)
    base_files: dict[str, bytes] = field(repr=False)
    problems: tuple[str, ...] = ()
    file_modes: dict[str, str] = field(default_factory=dict, repr=False)

    @property
    def complete(self):
        return not self.problems

    @property
    def paths(self):
        return tuple(c.path for c in self.changes)

    @property
    def digest(self):
        return content_digest(canonical_json(self.document).encode())

    @property
    def document(self):
        return {
            "base": self.base,
            "revision": self.revision,
            "changes": [asdict(c) for c in self.changes],
            "complete": self.complete,
            "problems": list(self.problems),
            "tree_digest": content_digest(
                canonical_json(
                    {
                        p: {"digest": content_digest(b), "mode": self.file_modes.get(p)}
                        for p, b in sorted(self.files.items())
                    }
                ).encode()
            ),
        }


def _git(target, *args, data=None, limit=16 * 1024 * 1024):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "-C", str(target), *args],
        input=data,
        capture_output=True,
        timeout=30,
        env=env,
        check=False,
    )
    if result.returncode or len(result.stdout) > limit:
        raise ValueError("Git input is unavailable or exceeds the observation limit")
    return result.stdout


def capture_change(
    target: Path,
    base: str,
    *,
    max_files=2048,
    max_bytes=1024 * 1024,
    max_total_bytes=16 * 1024 * 1024,
    max_changed=256,
) -> ChangeSnapshot:
    """Compare one explicit base commit to the Git-visible working tree.

    No checkout, index refresh, network operation, diff helper or textconv runs.
    Ignored untracked files are outside this observation. Bounds fail closed.
    """
    target = target.absolute()
    before, after, changes, problems = {}, {}, [], []
    resolved, revision = None, None
    current_modes = {}
    try:
        if target.is_symlink() or not target.is_dir():
            raise ValueError("Target must be a real directory")
        root = _git(target, "rev-parse", "--show-toplevel").decode().strip()
        if Path(root).resolve() != target.resolve():
            raise ValueError("Change inspection requires the Git repository root")
        resolved = (
            _git(target, "rev-parse", "--verify", "--end-of-options", base + "^{commit}")
            .decode()
            .strip()
        )
        revision = _git(target, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
        tree = _git(target, "ls-tree", "-r", "-l", "-z", "--full-tree", resolved)
        entries = []
        for entry in tree.split(b"\0"):
            if not entry:
                continue
            metadata, name = entry.split(b"\t", 1)
            mode, kind, sha, size = metadata.split()
            path = name.decode("utf-8")
            safe_relative(path)
            if kind != b"blob" or mode not in (b"100644", b"100755"):
                raise ValueError("Unsupported baseline file kind")
            entries.append((path, mode, sha, int(size)))
        names = {
            n.decode("utf-8")
            for n in _git(
                target, "ls-files", "-z", "--cached", "--others", "--exclude-standard"
            ).split(b"\0")
            if n
        }
        if (
            len(entries) > max_files
            or len(names) > max_files
            or any(e[3] > max_bytes for e in entries)
            or sum(e[3] for e in entries) > max_total_bytes
        ):
            raise ValueError("Repository exceeds file/content observation limits")
        blobs = _git(
            target,
            "cat-file",
            "--batch",
            data=b"".join(e[2] + b"\n" for e in entries),
            limit=max_total_bytes + len(entries) * 128,
        )
        cursor, modes = 0, {}
        for path, mode, sha, size in entries:
            end = blobs.index(b"\n", cursor)
            if blobs[cursor:end] != sha + b" blob " + str(size).encode():
                raise ValueError("Git blob snapshot changed unexpectedly")
            content = blobs[end + 1 : end + 1 + size]
            if len(content) != size or blobs[end + 1 + size : end + 2 + size] != b"\n":
                raise ValueError("Incomplete baseline content")
            before[path], modes[path] = content, mode
            cursor = end + 2 + size
        total, current_modes = 0, {}
        for name in sorted(names):
            safe_relative(name)
            try:
                metadata = (target / name).lstat()
            except FileNotFoundError:
                continue  # A tracked working-tree deletion.
            path = contained_file(target, name)
            with path.open("rb") as stream:
                content = stream.read(max_bytes + 1)
            total += len(content)
            if len(content) > max_bytes or total > max_total_bytes:
                raise ValueError("Working tree exceeds content observation limits")
            after[name] = content
            current_modes[name] = b"100755" if metadata.st_mode & stat.S_IXUSR else b"100644"
        for path in sorted(before.keys() | after.keys()):
            old, new = before.get(path), after.get(path)
            if old == new and modes.get(path) == current_modes.get(path):
                continue
            changes.append(
                ChangedPath(
                    path,
                    "added" if old is None else "deleted" if new is None else "modified",
                    content_digest(old) if old is not None else None,
                    content_digest(new) if new is not None else None,
                )
            )
        if len(changes) > max_changed:
            raise ValueError("Change exceeds the workflow scope limit")
        if _git(target, "rev-parse", "--verify", "HEAD^{commit}").decode().strip() != revision:
            raise ValueError("HEAD changed during observation")
    except (OSError, ValueError, subprocess.SubprocessError):
        problems.append(
            "Git scope is incomplete, unsafe, unavailable or exceeds observation limits; inspect the repository and retry."
        )
    return ChangeSnapshot(
        resolved,
        revision,
        tuple(changes),
        after,
        before,
        tuple(problems),
        {p: m.decode("ascii") for p, m in current_modes.items()},
    )
