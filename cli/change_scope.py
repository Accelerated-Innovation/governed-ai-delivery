# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Bounded local Git observations, including staged, dirty and untracked files."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .observation_limits import DEFAULT_OBSERVATION_LIMITS, ObservationLimits
from .pack_loading import contained_file, safe_relative
from .schema_validation import canonical_json, content_digest


class _ObservationLimit(ValueError):
    """A locally constructed budget diagnostic, safe to include in a report."""


def _diagnostic_path(path: str) -> str:
    """Leave room for the diagnostic inside the schema's 4096-character bound."""
    escaped = json.dumps(path)
    if len(escaped) <= 2048:
        return escaped
    # One code point expands to at most 12 ASCII characters in JSON. Encode the
    # prefix separately so truncation cannot split an escape or surrogate pair.
    prefix = json.dumps(path[:128])
    return f"{prefix}... (truncated; path sha256:{content_digest(path.encode())})"


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
    base_file_modes: dict[str, str] = field(default_factory=dict, repr=False)
    index_digest: str | None = None
    observation: dict | None = None

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
            **({"observation": self.observation} if self.observation is not None else {}),
            "base": self.base,
            "revision": self.revision,
            "changes": [asdict(c) for c in self.changes],
            "complete": self.complete,
            "problems": list(self.problems),
            "tree_digest": content_digest(
                canonical_json(
                    {
                        "index": self.index_digest,
                        "files": {
                            p: {"digest": content_digest(b), "mode": self.file_modes.get(p)}
                            for p, b in sorted(self.files.items())
                        },
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
    max_files=DEFAULT_OBSERVATION_LIMITS.max_files,
    max_bytes=DEFAULT_OBSERVATION_LIMITS.max_file_bytes,
    max_total_bytes=DEFAULT_OBSERVATION_LIMITS.max_total_bytes,
    max_changed=DEFAULT_OBSERVATION_LIMITS.max_changed_paths,
    limits: ObservationLimits | None = None,
) -> ChangeSnapshot:
    """Compare one explicit base commit to the Git-visible working tree.

    No checkout, index refresh, network operation, diff helper or textconv runs.
    Ignored untracked files are outside this observation. Bounds fail closed.
    Legacy keywords remain available within the validated ceilings; nondefault
    legacy values cannot be combined with a limits object. These internal
    arguments do not accept policy or add provenance to historical records.
    """
    legacy_limits = ObservationLimits(
        max_files=max_files,
        max_file_bytes=max_bytes,
        max_total_bytes=max_total_bytes,
        max_changed_paths=max_changed,
    )
    if limits is None:
        limits = legacy_limits
    elif not isinstance(limits, ObservationLimits):
        raise ValueError("Capture requires a validated ObservationLimits value")
    elif legacy_limits != DEFAULT_OBSERVATION_LIMITS:
        raise ValueError("Cannot combine a limits value with nondefault legacy limits")
    target = target.absolute()
    before, after, changes, problems = {}, {}, [], []
    resolved, revision = None, None
    current_modes, modes = {}, {}
    index_digest = None
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
        index_input = _git(target, "ls-files", "--stage", "-v", "-z")
        index_digest = content_digest(index_input)
        index = {}
        for entry in index_input.split(b"\0"):
            if not entry:
                continue
            metadata, name = entry.split(b"\t", 1)
            flag, mode, sha, stage = metadata.split()
            path = name.decode("utf-8")
            safe_relative(path)
            if flag.upper() == b"S" or stage != b"0" or mode not in (b"100644", b"100755"):
                raise ValueError("Sparse, conflicted or nonregular index is unsupported")
            index[path] = (mode, sha)
        names = {
            n.decode("utf-8")
            for n in _git(
                target, "ls-files", "-z", "--cached", "--others", "--exclude-standard"
            ).split(b"\0")
            if n
        }
        for label, count in (
            ("Baseline file", len(entries)),
            ("Index entry", len(index)),
            ("Git-visible path", len(names)),
        ):
            if count > limits.max_files:
                raise _ObservationLimit(f"{label} count {count} exceeds limit {limits.max_files}.")
        for path, _, _, size in entries:
            if size > limits.max_file_bytes:
                raise _ObservationLimit(
                    f"Baseline file {_diagnostic_path(path)} has {size} bytes; "
                    f"exceeds per-file limit of {limits.max_file_bytes} bytes."
                )
        baseline_size = sum(e[3] for e in entries)
        if baseline_size > limits.max_total_bytes:
            raise _ObservationLimit(
                f"Baseline has {baseline_size} bytes; "
                f"exceeds total-content limit of {limits.max_total_bytes} bytes."
            )
        blobs = _git(
            target,
            "cat-file",
            "--batch",
            data=b"".join(e[2] + b"\n" for e in entries),
            limit=limits.max_total_bytes + len(entries) * 128,
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
                content = stream.read(limits.max_file_bytes + 1)
            total += len(content)
            if len(content) > limits.max_file_bytes:
                raise _ObservationLimit(
                    f"Working-tree file {_diagnostic_path(name)} has at least {len(content)} bytes; "
                    f"exceeds per-file limit of {limits.max_file_bytes} bytes."
                )
            if total > limits.max_total_bytes:
                raise _ObservationLimit(
                    f"Working-tree content has at least {total} bytes; "
                    f"exceeds total-content limit of {limits.max_total_bytes} bytes."
                )
            after[name] = content
            current_modes[name] = b"100755" if metadata.st_mode & stat.S_IXUSR else b"100644"
        base_index = {p: (m, sha) for p, m, sha, _ in entries}
        object_format = _git(target, "rev-parse", "--show-object-format").decode().strip()
        if object_format not in {"sha1", "sha256"}:
            raise ValueError("Unsupported Git object format")
        for path in sorted(before.keys() | after.keys() | index.keys()):
            old, new = before.get(path), after.get(path)
            staged = index.get(path) != base_index.get(path)
            work_entry = (
                None
                if new is None
                else (
                    current_modes[path],
                    hashlib.new(object_format, b"blob " + str(len(new)).encode() + b"\0" + new)
                    .hexdigest()
                    .encode(),
                )
            )
            if staged and index.get(path) != work_entry:
                problems.append(
                    f"Staged content differs from the tested working tree: {path}; reconcile the index and retry."
                )
            if not staged and old == new and modes.get(path) == current_modes.get(path):
                continue
            changes.append(
                ChangedPath(
                    path,
                    "added" if old is None else "deleted" if new is None else "modified",
                    content_digest(old) if old is not None else None,
                    content_digest(new) if new is not None else None,
                )
            )
        if len(changes) > limits.max_changed_paths:
            raise _ObservationLimit(
                f"Changed-path count {len(changes)} exceeds limit {limits.max_changed_paths}."
            )
        if _git(target, "rev-parse", "--verify", "HEAD^{commit}").decode().strip() != revision:
            raise ValueError("HEAD changed during observation")
        if _git(target, "ls-files", "--stage", "-v", "-z") != index_input:
            raise ValueError("Index changed during observation")
    except _ObservationLimit as exc:
        problems.append(f"{exc} Scope remains incomplete; review repository bounds and retry.")
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
        {p: m.decode("ascii") for p, m in modes.items()},
        index_digest,
    )
