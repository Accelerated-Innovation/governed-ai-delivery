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
"""The known-failures record read by `govkit validate --known-failures`.

A record is an explicit, caller-reviewed list of validate failures accepted as
already existing. GovKit reads and renders records; it never writes one to
disk and never treats a rendered record as accepted. A valid record is
well-formed, not reviewed: its digest lets a caller pin the reviewed bytes.
See ADR 0021.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .schema_validation import DocumentError, content_digest, parse_document, validate_document
from .validate import FEATURE_CHECK_IDS

SCHEMA = "known-failures"
MAX_RECORD_BYTES = 1024 * 1024
MAX_ENTRIES = 5000  # the schema's maxItems; a test keeps the two equal

CHECK_EXTENSION = "extension-manifest"
CHECK_FIX = "fix-record"
CHECK_APPROVAL = "approval-policy"

# Which check identifiers each scope kind may name. An identifier outside this
# table makes a record invalid, so a mistyped entry cannot look reviewed.
CHECKS_BY_SCOPE = {
    "feature": frozenset(FEATURE_CHECK_IDS),
    "extension": frozenset({CHECK_EXTENSION}),
    "fix": frozenset({CHECK_FIX}),
    "approval": frozenset({CHECK_APPROVAL}),
}

# (scope kind, scope name or None, check identifier, finding code or None)
Key = tuple[str, str | None, str, str | None]


class RecordError(ValueError):
    """The record is missing, unreadable, malformed or invalid."""


@dataclass(frozen=True)
class Record:
    path: Path
    digest: str
    entries: frozenset[Key]


def load(path: Path) -> Record:
    """Read and validate one record. Never returns an empty stand-in."""
    try:
        with path.open("rb") as stream:
            content = stream.read(MAX_RECORD_BYTES + 1)
    except OSError as exc:
        raise RecordError(f"cannot be read: {exc.strerror or exc}") from exc
    if len(content) > MAX_RECORD_BYTES:
        raise RecordError(f"exceeds the {MAX_RECORD_BYTES}-byte limit")
    try:
        document = parse_document(content)
        validate_document(document, SCHEMA)
    except DocumentError as exc:
        raise RecordError(str(exc)) from exc

    keys: list[Key] = []
    for item in document["known_failures"]:
        scope = item["scope"]
        key = (scope["kind"], scope.get("name"), item["check"], item.get("finding"))
        if key[2] not in CHECKS_BY_SCOPE[key[0]]:
            raise RecordError(
                f"unknown check identifier {key[2]!r} for scope kind {key[0]!r}; "
                f"expected one of: {', '.join(sorted(CHECKS_BY_SCOPE[key[0]]))}"
            )
        if key in keys:
            raise RecordError(f"duplicate entry: {describe(key)}")
        keys.append(key)
    return Record(path, content_digest(content), frozenset(keys))


def render(keys) -> str:
    """The record text for `keys`: sorted and free of run-specific data, so the
    same failures always produce the same bytes and digest.

    Raises RecordError when the text could not be loaded back.
    """
    entries = []
    for kind, name, check, finding in sorted(set(keys), key=lambda k: tuple(p or "" for p in k)):
        scope = {"kind": kind} if name is None else {"kind": kind, "name": name}
        entry = {"scope": scope, "check": check}
        if finding is not None:
            entry["finding"] = finding
        entries.append(entry)
    if len(entries) > MAX_ENTRIES:
        raise RecordError(f"{len(entries)} failures exceed the {MAX_ENTRIES}-entry limit")
    document = {"schema_version": 1, "kind": SCHEMA, "known_failures": entries}
    text = json.dumps(document, indent=2) + "\n"
    if len(text.encode("utf-8")) > MAX_RECORD_BYTES:
        raise RecordError(f"the record would exceed the {MAX_RECORD_BYTES}-byte limit")
    return text


def identifier(check: str, finding: str | None) -> str:
    return check if finding is None else f"{check}/{finding}"


def describe(key: Key) -> str:
    kind, name, check, finding = key
    if kind == "feature":
        where = f"features/{name}"
    elif kind == "extension":
        where = f"extension {name}"
    elif kind == "fix":
        where = str(name)
    else:
        where = "ADR approval policy"
    return f"{where} [{identifier(check, finding)}]"
