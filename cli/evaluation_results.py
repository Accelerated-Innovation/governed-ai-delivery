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


def read_results(target: Path) -> tuple[list[ResultsFile] | None, str | None]:
    """Every evaluation results file under `target`. Returns (files, error). Never raises."""
    files = []
    seen: set[Path] = set()
    for pattern in _GLOBS:
        for path in sorted(target.glob(pattern)):
            if path in seen or path.is_dir():
                continue
            seen.add(path)
            relative = path.relative_to(target).as_posix()
            if path.is_symlink():
                return None, f"{relative} is a symbolic link and was not read"
            try:
                if path.stat().st_size > MAX_BYTES:
                    return None, f"{relative} is larger than 5 MiB and was not read"
                data = path.read_bytes()
                document = json.loads(data, parse_constant=_refuse_constant)
                if not isinstance(document, dict):
                    raise ValueError("the document is not an object")
                validate_document(document, SCHEMA)
            except (OSError, ValueError, RecursionError, DocumentError) as exc:
                return None, f"{relative} is not a usable evaluation results file: {exc}"
            files.append(
                ResultsFile(
                    path=relative,
                    content_digest=hashlib.sha256(data).hexdigest(),
                    results=tuple(
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
                    ),
                )
            )
    return files, None
