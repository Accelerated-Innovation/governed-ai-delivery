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
from .evidence import _JUNIT_GLOBS, _find, is_junit
from .schema_validation import DocumentError, validate_document

NAME = "govkit-evidence-record.json"
SCHEMA = "evidence-record"
MAX_RESULTS = 5000  # the schema's maxItems; a test keeps the two equal
MAX_PATTERNS, MAX_PATTERN_LENGTH = 32, 512  # likewise
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


def check_patterns(patterns) -> tuple[str, ...]:
    """The `--junit` patterns, if each can only match inside the target. Raises `RecordError`.

    A pattern is relative, uses forward slashes and never climbs with `..`, so
    the same record means the same place on every platform.
    """
    patterns = tuple(patterns)
    if len(patterns) > MAX_PATTERNS:
        raise RecordError(f"--junit was given {len(patterns)} times; the limit is {MAX_PATTERNS}")
    for pattern in patterns:
        if not isinstance(pattern, str) or not 0 < len(pattern) <= MAX_PATTERN_LENGTH:
            reason = f"must be 1 to {MAX_PATTERN_LENGTH} characters"
        elif "\\" in pattern:
            reason = "must use forward slashes"
        elif pattern.startswith("/") or ":" in pattern.split("/")[0]:
            reason = "must be relative to the target"
        elif ".." in pattern.split("/"):
            reason = "must not contain `..`"
        elif any("**" in part and part != "**" for part in pattern.split("/")):
            reason = "may use `**` only as a whole folder name"
        else:
            continue
        shown = pattern if isinstance(pattern, str) else repr(pattern)
        raise RecordError(f"--junit {shown[:80]!r} {reason}")
    return patterns


def _stated(target: Path, patterns: tuple[str, ...]) -> list[Path]:
    """The files the stated patterns match. Each pattern must match JUnit XML only.

    A recorded result file is left out of the working tree digest. So a pattern
    that matched a source file would hide that file's edits from the freshness
    check; anything that is not a JUnit report is refused.
    """
    inside = target.resolve()
    found: list[Path] = []
    for pattern in patterns:
        try:
            matched = _find(target, (pattern,))
        except (OSError, ValueError, NotImplementedError):
            raise RecordError(f"--junit {pattern!r} could not be searched for") from None
        if not matched:
            raise RecordError(
                f"--junit {pattern!r} matched no file under the target. "
                "Run the tests first, and check the pattern."
            )
        for path in matched:
            relative = path.relative_to(target).as_posix()
            try:
                contained = path.resolve().is_relative_to(inside)
                usable = contained and path.is_file() and not path.is_symlink()
                junit = usable and is_junit(path.read_bytes())
            except OSError as exc:
                raise RecordError(f"{relative} could not be read: {type(exc).__name__}") from None
            if not contained:
                raise RecordError(f"{relative} is outside the target and was not recorded")
            if usable and not junit:
                raise RecordError(
                    f"{relative} is not JUnit XML and was not recorded; "
                    "--junit must match test result files only"
                )
            if path not in found:
                found.append(path)
    return found


def discover(target: Path, patterns=None) -> list[dict]:
    """Every result file under `target`, with its digest. Raises `RecordError`.

    `patterns` are where the project said its test results are. They replace
    the name rule for test results; evaluation results keep their GovKit name.
    """
    if patterns:
        junit = _stated(target, check_patterns(patterns))
    else:
        junit = _find(target, _JUNIT_GLOBS)
    found = [("junit", path) for path in junit]
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


def write_record(target: Path, *, junit=(), observe=None, now: datetime | None = None) -> dict:
    """Observe the tree and the result files, and write the record. Raises `RecordError`.

    `junit` are patterns for where the test results are, kept in the record so
    the report searches the same place.
    """
    patterns = check_patterns(junit)
    results = discover(target, patterns)
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
    if patterns:
        record["junit_patterns"] = list(patterns)
    # Refuse now what the reader would refuse later, so a record that was
    # reported as written can always be read back.
    try:
        validate_document(record, SCHEMA)
    except DocumentError as exc:
        raise RecordError(f"the record would not be usable: {exc}") from None
    # Bytes, not text: the size checked here is the size written, on every platform.
    data = (json.dumps(record, indent=2) + "\n").encode("utf-8")
    if len(data) > evaluation_results.MAX_BYTES:
        raise RecordError(
            "the record would be larger than 5 MiB, which the reader refuses. "
            "Point the target at the project, or remove old result files."
        )
    _replace(target / NAME, data)
    return record


def _replace(path: Path, data: bytes) -> None:
    """Write `data` to `path`, leaving what was there untouched if anything fails.

    The bytes go to a new file beside the destination, which then takes its
    place in one step. A link in the destination's place is refused.
    """
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise RecordError(f"{NAME} exists and is not a regular file; it was not replaced")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        flags |= getattr(os, "O_BINARY", 0)
        with os.fdopen(os.open(temporary, flags, 0o644), "wb") as handle:
            handle.write(data)
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
    try:
        check_patterns(document.get("junit_patterns", ()))
    except RecordError as exc:
        raise RecordError(f"{NAME} is not a usable evidence record: {exc}") from None
    return document


def load(target: Path) -> tuple[dict | None, str | None]:
    """One reading of the record: (record, error). Both None when there is none.

    A report selects its files and judges them against the same reading, so a
    record written meanwhile cannot vouch for files it did not select.
    """
    try:
        return read_record(target), None
    except RecordError as exc:
        return None, str(exc)


def junit_patterns(target: Path, loaded=None) -> tuple[str, ...] | None:
    """Where the record says the test results are, or None for the name rule.

    None also when there is no usable record: `provenance` reports that, and
    the results do not count either way.
    """
    record, _ = loaded or load(target)
    return tuple(record["junit_patterns"]) if record and "junit_patterns" in record else None


def _lost(target: Path, record: dict) -> str | None:
    """Why a recorded result file no longer counts as present, or None.

    A report reads what is there. Without this, deleting the one file that
    holds a failure would leave the rest current.
    """
    for result in record["results"]:
        path = result["path"]
        try:
            status = (target / path).lstat()
        except OSError:
            return f"{path} was removed after it was recorded; {_AGAIN}"
        if not stat.S_ISREG(status.st_mode):
            return f"{path} is no longer a regular file; {_AGAIN}"
    return None


def provenance(target: Path, sources: list[dict], *, observe=None, loaded=None) -> dict:
    """Whether the result files in `sources` belong to the repository as it is now.

    `sources` are the result files a report read, each with `path` and
    `content_digest`. The answer is a dictionary for the report; its `state` is
    one of `STATES`. Never raises. `loaded` is a reading of the record from
    `load`; without it the record is read now.
    """
    answer = {
        "state": NOT_CHECKED,
        "detail": "no result file was read",
        "commit": None,
        "tree_digest": None,
        "recorded_at": None,
    }

    def settle(state: str, detail: str) -> dict:
        answer["state"], answer["detail"] = state, detail
        return answer

    record, error = loaded or load(target)
    if not sources:
        # Nothing was read. That is only "not checked" when no recorded file
        # was lost; deleting every result file is still a removal.
        lost = _lost(target, record) if record else None
        if lost:
            answer.update({key: record[key] for key in ("commit", "tree_digest", "recorded_at")})
            return settle(STALE, lost)
        return answer
    if error:
        return settle(UNAVAILABLE, error)
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
    lost = _lost(target, record)
    if lost:
        return settle(STALE, lost)
    try:
        now = _observe(target, record["results"], observe)
    except tree_identity.Unavailable as exc:
        return settle(UNAVAILABLE, f"the working tree cannot be identified: {exc}")
    if now.commit != record["commit"]:
        return settle(STALE, f"the commit changed after the results were recorded; {_AGAIN}")
    if now.tree_digest != record["tree_digest"]:
        return settle(STALE, f"the working tree changed after the results were recorded; {_AGAIN}")
    return settle(CURRENT, "the commit and the working tree are as they were recorded")
