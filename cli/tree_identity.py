# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""The identity of a working tree: its commit and a digest of what Git sees in it.

A test result counts only for the tree that produced it. Two observations of
the same repository are equal when the commit, the index and the content of
every modified, deleted or untracked file are the same. Files Git ignores are
outside the observation, and so are the paths the caller excludes, which is
how writing a result file avoids making its own results stale.

The whole repository is observed, also when the target is a directory below
its root, so a change in shared code outside the target is still seen.

It asks Git which files differ instead of reading every file, so the cost
follows the size of the change. It is read-only: no index refresh, no object
is written, and no hook, filter or network operation runs. An identity is an
observation, not proof of origin.
"""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .schema_validation import canonical_json

_TIMEOUT_SECONDS = 60


class Unavailable(Exception):
    """The tree cannot be identified. The message says why, without file content."""


@dataclass(frozen=True)
class Identity:
    commit: str
    tree_digest: str
    clean: bool  # nothing differs from the commit, apart from excluded paths


def _git(directory: Path, *args: str) -> bytes:
    environment = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    try:
        result = subprocess.run(
            ["git", "-c", "core.fsmonitor=false", "-C", str(directory), *args],
            capture_output=True,
            timeout=_TIMEOUT_SECONDS,
            env=environment,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise Unavailable(f"Git could not be run: {type(exc).__name__}") from None
    if result.returncode:
        raise Unavailable(f"`git {args[0]}` failed")
    return result.stdout


def _names(output: bytes) -> list[str]:
    return [name.decode("utf-8", "surrogateescape") for name in output.split(b"\0") if name]


def _state(path: Path) -> list[str]:
    """What is at `path` now: its kind and a digest of its content, never the content."""
    try:
        status = path.lstat()
    except FileNotFoundError:
        return ["absent", ""]
    try:
        if stat.S_ISLNK(status.st_mode):
            return [
                "link",
                hashlib.sha256(os.readlink(path).encode("utf-8", "replace")).hexdigest(),
            ]
        if not stat.S_ISREG(status.st_mode):
            return ["other", ""]
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise Unavailable(f"a changed file could not be read: {type(exc).__name__}") from None
    executable = "x" if status.st_mode & stat.S_IXUSR else "-"
    return [f"file{executable}", digest.hexdigest()]


def observe(target: Path, exclude: tuple[str, ...] = ()) -> Identity:
    """Identify the repository that holds `target`. Raises `Unavailable`.

    `exclude` lists paths relative to `target`, with forward slashes, that are
    left out of the observation.
    """
    target = Path(target).resolve()
    root = Path(_git(target, "rev-parse", "--show-toplevel").decode("utf-8", "replace").strip())
    commit = _git(root, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    try:
        prefix = target.relative_to(root.resolve()).as_posix()
    except ValueError:
        raise Unavailable("the target is not inside the repository Git reported") from None
    excluded = {f"{prefix}/{path}" if prefix != "." else path for path in exclude}

    index = sorted(
        entry
        for entry in _git(root, "ls-files", "--stage", "-z").split(b"\0")
        if entry and entry.split(b"\t", 1)[1].decode("utf-8", "surrogateescape") not in excluded
    )
    staged = _names(_git(root, "diff", "--cached", "--name-only", "-z", "--no-renames", "HEAD"))
    listed = _git(
        root, "ls-files", "-z", "--modified", "--deleted", "--others", "--exclude-standard"
    )
    changed = sorted(set(_names(listed)) - excluded)
    document = {
        "commit": commit,
        "index": hashlib.sha256(b"\0".join(index)).hexdigest(),
        # Names as bytes in hex: a file name need not be valid text.
        "changed": [[os.fsencode(name).hex(), *_state(root / name)] for name in changed],
    }
    return Identity(
        commit=commit,
        tree_digest=hashlib.sha256(canonical_json(document).encode()).hexdigest(),
        clean=not changed and not (set(staged) - excluded),
    )
