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
"""Evaluation results files: measured scores for criteria.

A project's evaluation run writes `govkit-eval-results*.json` (schema
`evaluation-results`). GovKit reads those files, bounded and without
following symbolic links, and never writes one or starts an evaluation.

A file that cannot be trusted stops the report. It is never read as empty,
because an unreadable result that reads as "no result" would turn a failed
evaluation into a missing one. A valid file is well-formed; that does not
authenticate where its values came from.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from .schema_validation import DocumentError, validate_document

SCHEMA = "evaluation-results"
KIND = "govkit.evaluation-results"
MAX_BYTES = 5 * 1024 * 1024
# Named for GovKit so another tool's `results.json` is never mistaken for one.
_GLOBS = ("govkit-eval-results*.json", "**/govkit-eval-results*.json")


@dataclass(frozen=True)
class Measurement:
    requirement_id: str
    value: float | None
    unit: str | None
    metric: str | None
    n: int | None
    errored: bool  # the evaluation ran and produced no value
    source: str


@dataclass(frozen=True)
class ResultsFile:
    path: str  # relative to the target, with forward slashes
    content_digest: str
    results: tuple[Measurement, ...]


def _refuse_constant(name: str):
    raise ValueError(f"{name} is not a finite number")


def _refuse_duplicates(pairs: list) -> dict:
    """`json.loads` keeps the last of two equal keys, which would drop a result."""
    found: dict = {}
    for key, value in pairs:
        if key in found:
            raise ValueError(f"duplicate key {key!r}")
        found[key] = value
    return found


def _read_checked(path: Path, relative: str) -> bytes:
    """The bytes of the file that was checked, and no more than the limit.

    The path could be replaced between the examination above and a read by
    name. So the file is opened once without following a link where the
    platform allows, the open handle is what gets checked and is compared with
    the path, and the read stops one byte past the limit so a file that grows
    meanwhile is still refused.
    """
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags | getattr(os, "O_BINARY", 0))
    with os.fdopen(descriptor, "rb") as handle:
        status = os.fstat(handle.fileno())
        if not stat.S_ISREG(status.st_mode):
            raise _Refused(f"{relative} is not a regular file and was not read")
        # Not every platform can refuse a link at open. So the path is looked
        # at again: it must still be a plain file, and the same one as the
        # handle. Anything else means it was replaced, and the read is refused.
        named = path.lstat()
        if stat.S_ISLNK(named.st_mode) or not os.path.samestat(status, named):
            raise _Refused(f"{relative} changed while it was being read and was not used")
        data = handle.read(MAX_BYTES + 1)
    if status.st_size > MAX_BYTES or len(data) > MAX_BYTES:
        raise _Refused(f"{relative} is larger than 5 MiB and was not read")
    return data


def _read_file(path: Path, relative: str) -> ResultsFile:
    """One results file. Raises `_Refused` with the reason it cannot be used."""
    try:
        # The link check comes first, so a link is refused whatever it points
        # at. `lstat` does not follow it, and a file that is not regular (a
        # pipe would block on open) is refused without being opened.
        status = path.lstat()
        if stat.S_ISLNK(status.st_mode):
            raise _Refused(f"{relative} is a symbolic link and was not read")
        if not stat.S_ISREG(status.st_mode):
            raise _Refused(f"{relative} is not a regular file and was not read")
        if status.st_size > MAX_BYTES:
            raise _Refused(f"{relative} is larger than 5 MiB and was not read")
        data = _read_checked(path, relative)
        document = json.loads(
            data, parse_constant=_refuse_constant, object_pairs_hook=_refuse_duplicates
        )
        if not isinstance(document, dict):
            raise ValueError("the document is not an object")
        validate_document(document, SCHEMA)
        results = tuple(
            Measurement(
                requirement_id=item["requirement_id"],
                value=float(item["value"]) if "value" in item else None,
                unit=item.get("unit"),
                metric=item.get("metric"),
                n=item.get("n"),
                errored="error" in item,
                source=relative,
            )
            for item in document["results"]
        )
    except (OSError, ValueError, OverflowError, RecursionError, DocumentError) as exc:
        raise _Refused(f"{relative} is not a usable evaluation results file: {exc}") from None
    return ResultsFile(relative, hashlib.sha256(data).hexdigest(), results)


class _Refused(Exception):
    """A results file cannot be used. The message is the report's detail."""


def read_results(target: Path) -> tuple[list[ResultsFile] | None, str | None]:
    """Every evaluation results file under `target`. Returns (files, error). Never raises."""
    files = []
    seen: set[Path] = set()
    try:
        for pattern in _GLOBS:
            for path in sorted(target.glob(pattern)):
                if path in seen:
                    continue
                seen.add(path)
                files.append(_read_file(path, path.relative_to(target).as_posix()))
    except _Refused as refused:
        return None, str(refused)
    except OSError as exc:
        return None, f"evaluation results could not be searched for: {exc}"
    return files, None
