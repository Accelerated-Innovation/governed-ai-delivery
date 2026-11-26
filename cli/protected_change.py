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
"""Whether a change weakened the tests and files that check it.

`definition_change.py` keeps a change from weakening a feature's scenarios and
criteria. This module covers what checks them: existing tests, the support
files and settings they rely on, and other files the project protects, such as
CI workflows. The project declares the paths in accepted policy, which the
change being judged cannot edit.

- `tests`: an existing file may only gain lines. Every line it had at the
  comparison base must still be there, in the same order.
- `files`: an existing file may not change at all. A path under both follows
  this rule.
- `escape_markers`: literal text, such as a skip marker. Its count in the
  declared tests and in feature definitions may fall and may not rise.

A new file passes under either rule. A finding means a person must look.

Known limits. A line inserted inside an existing test, such as an early
return, keeps every base line and is not seen; declare escape markers for the
common forms. Imports are not traced, so a helper outside the declared paths
is not protected.

It is pure: the caller supplies the declaration and both sets of bytes.
Messages name files and markers and hold no file content.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .definition_change import definition_paths

# A public vocabulary: add, never rename.
CODES = (
    "test-altered",
    "test-removed",
    "protected-file-changed",
    "protected-file-removed",
    "escape-marker-added",
)


@dataclass(frozen=True)
class ProtectedFinding:
    code: str  # one of CODES
    path: str
    message: str


@dataclass(frozen=True)
class Assessment:
    checked: tuple[str, ...]  # the changed files a rule applied to
    findings: tuple[ProtectedFinding, ...]


def _covers(prefix: str, path: str) -> bool:
    prefix = prefix.rstrip("/")
    return prefix == "." or path == prefix or path.startswith(prefix + "/")


def _under(prefixes: Iterable[str], path: str) -> bool:
    return any(_covers(prefix, path) for prefix in prefixes)


def _lines(data: bytes) -> list[str] | None:
    """The file's lines with line endings normalised, or None when it is not text."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # A final line ending is not one more, empty, line. Blank lines are kept.
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _only_gained_lines(before: bytes, after: bytes) -> bool:
    """Whether every line of `before` is still in `after`, in the same order."""
    was, now = _lines(before), _lines(after)
    if was is None or now is None:
        return before == after
    remaining = iter(now)
    return all(any(line == candidate for candidate in remaining) for line in was)


def assess(
    declared: Mapping,
    base_files: Mapping[str, bytes],
    files: Mapping[str, bytes],
    changed: Iterable[str],
    *,
    base_modes: Mapping[str, str] | None = None,
    modes: Mapping[str, str] | None = None,
) -> Assessment:
    """Compare each changed protected file with its content at the comparison base.

    `base_modes` and `modes` are Git file modes by path. A changed mode, such
    as a lost executable bit, is a change to an existing file under either rule.
    """
    base_modes, modes = base_modes or {}, modes or {}
    tests = tuple(declared.get("tests", ()))
    fixed = tuple(declared.get("files", ()))
    checked, findings = [], []
    for path in changed:
        strict = _under(fixed, path)
        if not strict and not _under(tests, path):
            continue
        checked.append(path)
        before, after = base_files.get(path), files.get(path)
        if before is None:
            continue  # A new file adds; it cannot weaken what was there.
        if after is None:
            code = "protected-file-removed" if strict else "test-removed"
            what = "was deleted by this change"
        elif base_modes.get(path) != modes.get(path):
            code = "protected-file-changed" if strict else "test-altered"
            what = "had its file mode changed"
        elif strict and before != after:
            code, what = "protected-file-changed", "is protected and was changed"
        elif not strict and not _only_gained_lines(before, after):
            code = "test-altered"
            what = "lost or changed a line it had at the comparison base"
        else:
            continue
        findings.append(ProtectedFinding(code, path, f"{path} {what}"))
    findings += _escapes(tuple(declared.get("escape_markers", ())), tests, base_files, files)
    return Assessment(tuple(checked), tuple(findings))


def _escapes(markers, tests, base_files, files) -> list[ProtectedFinding]:
    """One finding per file whose count of a marker rose, when the total rose."""
    if not markers:
        return []

    def counted(mapping: Mapping[str, bytes]) -> dict[str, bytes]:
        definitions = set(definition_paths(mapping))
        return {
            path: data
            for path, data in mapping.items()
            if _under(tests, path) or (path in definitions and path.endswith(".feature"))
        }

    was, now = counted(base_files), counted(files)
    findings = []
    for marker in markers:
        needle = marker.encode("utf-8")
        before = {path: data.count(needle) for path, data in was.items()}
        after = {path: data.count(needle) for path, data in now.items()}
        if sum(after.values()) <= sum(before.values()):
            continue
        for path in sorted(after):
            if after[path] > before.get(path, 0):
                findings.append(
                    ProtectedFinding(
                        "escape-marker-added",
                        path,
                        f"{path} has more of the escape marker {marker!r} than at the "
                        "comparison base",
                    )
                )
    return findings
