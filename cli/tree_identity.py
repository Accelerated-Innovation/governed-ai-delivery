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
every modified, deleted or untracked file are the same, in the repository
and in each submodule checked out inside it. Files Git ignores are outside
the observation, and so are the paths the caller excludes, which is
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


# Variables Git sets for hooks and that a shell may export. Left in place they
# would point every command below at another repository or index, whatever
# directory `-C` names.
_LOCATION_VARIABLES = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_NAMESPACE",
    "GIT_PREFIX",
)
_MAX_SUBMODULE_DEPTH = 16


def _git(directory: Path, *args: str) -> bytes:
    environment = {
        name: value for name, value in os.environ.items() if name not in _LOCATION_VARIABLES
    }
    environment.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
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


def _describe(root: Path, excluded: set[str], depth: int = 0) -> tuple[dict, bool]:
    """What one repository holds now, and whether it differs from its commit.

    A submodule is a repository checked out inside this one. The parent only
    says whether it is at the commit the parent recorded, so each submodule is
    described in its own right: its commit and its own changes.
    """
    if depth > _MAX_SUBMODULE_DEPTH:
        raise Unavailable("submodules are nested too deeply to identify")
    commit = _git(root, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    staged_index = _git(root, "ls-files", "--stage", "-z")
    index, links = [], {}
    for entry in staged_index.split(b"\0"):
        if not entry:
            continue
        fields, _, raw_name = entry.partition(b"\t")
        name = raw_name.decode("utf-8", "surrogateescape")
        if name in excluded:
            continue
        index.append(entry)
        mode, recorded_commit = fields.split()[:2]
        if mode == b"160000":
            links[name] = recorded_commit.decode()
    staged = _names(_git(root, "diff", "--cached", "--name-only", "-z", "--no-renames", "HEAD"))
    listed = _git(
        root, "ls-files", "-z", "--modified", "--deleted", "--others", "--exclude-standard"
    )
    changed = sorted(set(_names(listed)) - excluded - set(links))
    dirty = bool(changed) or bool(set(staged) - excluded)
    submodules = []
    for name in sorted(links):
        if not (root / name / ".git").exists():
            # Not checked out: nothing of it can have been tested or edited.
            submodules.append([os.fsencode(name).hex(), "absent", ""])
            continue
        inner, inner_dirty = _describe(root / name, set(), depth + 1)
        dirty = dirty or inner_dirty or inner["commit"] != links[name]
        digest = hashlib.sha256(canonical_json(inner).encode()).hexdigest()
        submodules.append([os.fsencode(name).hex(), inner["commit"], digest])
    # The calls above are separate. If something was staged between them, the
    # index read first no longer describes the files listed after it.
    if _git(root, "ls-files", "--stage", "-z") != staged_index:
        raise Unavailable("the index changed while the working tree was being observed")
    document = {
        "commit": commit,
        "index": hashlib.sha256(b"\0".join(sorted(index))).hexdigest(),
        # Names as bytes in hex: a file name need not be valid text.
        "changed": [[os.fsencode(name).hex(), *_state(root / name)] for name in changed],
        "submodules": submodules,
    }
    return document, dirty


def observe(target: Path, exclude: tuple[str, ...] = ()) -> Identity:
    """Identify the repository that holds `target`. Raises `Unavailable`.

    `exclude` lists paths relative to `target`, with forward slashes, that are
    left out of the observation.
    """
    target = Path(target).resolve()
    root = Path(_git(target, "rev-parse", "--show-toplevel").decode("utf-8", "replace").strip())
    try:
        prefix = target.relative_to(root.resolve()).as_posix()
    except ValueError:
        raise Unavailable("the target is not inside the repository Git reported") from None
    excluded = {f"{prefix}/{path}" if prefix != "." else path for path in exclude}
    document, dirty = _describe(root, excluded)
    return Identity(
        commit=document["commit"],
        tree_digest=hashlib.sha256(canonical_json(document).encode()).hexdigest(),
        clean=not dirty,
    )
