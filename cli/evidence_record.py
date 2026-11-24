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
"""The evidence record: which commit and working tree a set of results came from.

`govkit evidence --record`, run straight after the tests, writes one file in
the target. It holds the commit, a digest of the working tree and the digest
of each result file. `govkit evidence --feature` then counts results only
while the record still describes the repository, so a result left over from
an earlier run, or from before an edit, is reported as stale.

The record is the one file this command family writes. It is an observation,
not proof: it can be written again without running the tests, and it does not
authenticate the result files. A local result stays a stop condition. The
run that counts is CI on a clean checkout.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path

from . import evaluation_results, tree_identity
from .evaluation_results import Refused, load_document
from .evidence import _JUNIT_GLOBS, _find
from .schema_validation import DocumentError, validate_document

NAME = "govkit-evidence-record.json"
SCHEMA = "evidence-record"
MAX_RESULTS = 5000  # the schema's maxItems; a test keeps the two equal
KIND = "govkit.evidence-record"
CURRENT, STALE, UNRECORDED, UNAVAILABLE, NOT_CHECKED = (
    "current",
    "stale",
    "unrecorded",
    "unavailable",
    "not-checked",
)
STATES = (CURRENT, STALE, UNRECORDED, UNAVAILABLE, NOT_CHECKED)
_AGAIN = "run the tests and `govkit evidence --record` again"


class RecordError(Exception):
    """The record cannot be written or used. The message is safe to print."""


def discover(target: Path) -> list[dict]:
    """Every result file under `target`, with its digest. Raises `RecordError`."""
    found = [("junit", path) for path in _find(target, _JUNIT_GLOBS)]
    found += [("evaluation-results", path) for path in evaluation_results.find(target)]
    results = []
    for tool, path in found:
        relative = path.relative_to(target).as_posix()
        try:
            status = path.lstat()
            if not stat.S_ISREG(status.st_mode):
                raise RecordError(f"{relative} is not a regular file and was not recorded")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise RecordError(f"{relative} could not be read: {type(exc).__name__}") from None
        results.append({"tool": tool, "path": relative, "content_digest": digest})
    return sorted(results, key=lambda result: (result["path"], result["tool"]))


def _observe(target: Path, results: list[dict], observe) -> tree_identity.Identity:
    """The tree without the result files and the record, which a test run rewrites."""
    exclude = tuple(sorted({result["path"] for result in results} | {NAME}))
    return (observe or tree_identity.observe)(target, exclude)


def write_record(target: Path, *, observe=None, now: datetime | None = None) -> dict:
    """Observe the tree and the result files, and write the record. Raises `RecordError`."""
    results = discover(target)
    if not results:
        raise RecordError(
            "no result files were found, so there is nothing to record. "
            "Run the tests first, writing JUnit XML under the target."
        )
    if len(results) > MAX_RESULTS:
        raise RecordError(
            f"too many result files ({len(results)}); a record holds at most {MAX_RESULTS}. "
            "Point the target at the project, or remove old result files."
        )
    try:
        identity = _observe(target, results, observe)
    except tree_identity.Unavailable as exc:
        raise RecordError(f"the working tree cannot be identified: {exc}") from None
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    record = {
        "schema_version": 1,
        "kind": KIND,
        "commit": identity.commit,
        "tree_digest": identity.tree_digest,
        "clean": identity.clean,
        "recorded_at": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "results": results,
    }
    # Refuse now what the reader would refuse later, so a record that was
    # reported as written can always be read back.
    try:
        validate_document(record, SCHEMA)
    except DocumentError as exc:
        raise RecordError(f"the record would not be usable: {exc}") from None
    text = json.dumps(record, indent=2) + "\n"
    if len(text.encode("utf-8")) > evaluation_results.MAX_BYTES:
        raise RecordError(
            "the record would be larger than 5 MiB, which the reader refuses. "
            "Point the target at the project, or remove old result files."
        )
    _replace(target / NAME, text)
    return record


def _replace(path: Path, text: str) -> None:
    """Write `text` to `path`, leaving what was there untouched if anything fails.

    The text goes to a new file beside the destination, which then takes its
    place in one step. A link in the destination's place is refused.
    """
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise RecordError(f"{NAME} exists and is not a regular file; it was not replaced")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(temporary, flags, 0o644), "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temporary, path)
    except OSError as exc:
        _discard(temporary)
        raise RecordError(f"{NAME} could not be written: {type(exc).__name__}") from None


def _discard(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def read_record(target: Path) -> dict | None:
    """The record in `target`, or None when there is none. Raises `RecordError`."""
    path = target / NAME
    if not path.is_symlink() and not path.exists():
        return None
    try:
        document, _ = load_document(path, NAME, SCHEMA, "evidence record")
    except Refused as refused:
        raise RecordError(str(refused)) from None
    return document


def provenance(target: Path, sources: list[dict], *, observe=None) -> dict:
    """Whether the result files in `sources` belong to the repository as it is now.

    `sources` are the result files a report read, each with `path` and
    `content_digest`. The answer is a dictionary for the report; its `state` is
    one of `STATES`. Never raises.
    """
    answer = {
        "state": NOT_CHECKED,
        "detail": "no result file was read",
        "commit": None,
        "tree_digest": None,
        "recorded_at": None,
    }
    if not sources:
        return answer

    def settle(state: str, detail: str) -> dict:
        answer["state"], answer["detail"] = state, detail
        return answer

    try:
        record = read_record(target)
    except RecordError as exc:
        return settle(UNAVAILABLE, str(exc))
    if record is None:
        return settle(
            UNRECORDED,
            f"there is no {NAME}, so the results cannot be shown to belong to this "
            f"commit and working tree; {_AGAIN}",
        )
    answer.update({key: record[key] for key in ("commit", "tree_digest", "recorded_at")})
    recorded = {result["path"]: result["content_digest"] for result in record["results"]}
    for source in sources:
        if source["path"] not in recorded:
            return settle(STALE, f"{source['path']} was written after the record; {_AGAIN}")
        if recorded[source["path"]] != source["content_digest"]:
            return settle(STALE, f"{source['path']} changed after it was recorded; {_AGAIN}")
    try:
        now = _observe(target, record["results"], observe)
    except tree_identity.Unavailable as exc:
        return settle(UNAVAILABLE, f"the working tree cannot be identified: {exc}")
    if now.commit != record["commit"]:
        return settle(STALE, f"the commit changed after the results were recorded; {_AGAIN}")
    if now.tree_digest != record["tree_digest"]:
        return settle(STALE, f"the working tree changed after the results were recorded; {_AGAIN}")
    return settle(CURRENT, "the commit and the working tree are as they were recorded")
