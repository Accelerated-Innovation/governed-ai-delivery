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
"""Whether a change weakened the definition it is judged by.

A feature is done when its scenarios pass and its criteria are met. A change
that deletes a failing scenario, loosens a step or lowers a threshold reaches
that state without doing the work. This module compares each changed
`features/<name>/acceptance.feature` and `eval_criteria.yaml` with what it was
at the comparison base.

A change may add scenarios and criteria. What existed at the base must still be
there, unchanged, and so must the `Background` steps that run before it. A
finding means a person must look. It is not a judgement that the edit made the
definition worse: GovKit cannot tell a correction from a weakening.

It is pure: the caller supplies both sets of bytes. Messages name files,
scenarios and criteria, and hold no step text or values.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from . import scenario_identity
from .criterion_identity import criterion_id
from .schema_validation import DocumentError, parse_document

MAX_BYTES = 1024 * 1024
# A public vocabulary: add, never rename.
CODES = (
    "scenario-removed",
    "scenario-altered",
    "shared-steps-changed",
    "criterion-removed",
    "criterion-altered",
    "criteria-changed",
    "definition-removed",
    "definition-unreadable",
)
_DEFINITION = re.compile(r"^features/([^/]+)/(acceptance\.feature|eval_criteria\.yaml)$")
_LISTS = ("llm_evaluation", "criteria")  # where `criterion_identity` reads criteria, in order


@dataclass(frozen=True)
class DefinitionFinding:
    code: str  # one of CODES
    path: str
    requirement: str | None  # the scenario or criterion identifier, when there is one
    message: str


@dataclass(frozen=True)
class Assessment:
    checked: tuple[str, ...]  # the definition files that were compared
    findings: tuple[DefinitionFinding, ...]
    unknown: tuple[str, ...]  # why a file could not be compared; never a pass


class _Unreadable(Exception):
    """A definition file cannot be identified. The message says why, without content."""


def definition_paths(paths: Iterable[str]) -> tuple[str, ...]:
    """The feature definition files among `paths`, which are relative to the repository root."""
    return tuple(path for path in paths if _DEFINITION.match(path))


def assess(
    base_files: Mapping[str, bytes], files: Mapping[str, bytes], changed: Iterable[str]
) -> Assessment:
    """Compare each changed definition file with its content at the comparison base."""
    checked, findings, unknown = [], [], []
    for path in definition_paths(changed):
        before, after = base_files.get(path), files.get(path)
        if before is None:
            continue  # A new file can only add.
        checked.append(path)
        package, name = _DEFINITION.match(path).groups()
        read = _scenarios if name == "acceptance.feature" else _criteria
        try:
            was = read(package, before)
        except _Unreadable as exc:
            unknown.append(
                f"{path} at the comparison base {exc}, so the change to it cannot be compared"
            )
            continue
        if after is None:
            findings.append(
                DefinitionFinding(
                    "definition-removed", path, None, f"{path} was deleted by this change"
                )
            )
            continue
        try:
            now = read(package, after)
        except _Unreadable as exc:
            findings.append(
                DefinitionFinding("definition-unreadable", path, None, f"{path} now {exc}")
            )
            continue
        compare = _compare_scenarios if name == "acceptance.feature" else _compare_criteria
        findings += compare(path, was, now)
    return Assessment(tuple(checked), tuple(findings), tuple(unknown))


def _bounded(data: bytes) -> bytes:
    if len(data) > MAX_BYTES:
        raise _Unreadable("is larger than 1 MiB")
    return data


# --- scenarios ---------------------------------------------------------------


def _scenarios(package: str, data: bytes) -> dict[str, tuple[str, str]]:
    """Scenario identifier -> (revision digest, digest of the shared steps that cover it)."""
    try:
        scenarios = scenario_identity.read_scenarios(package, _bounded(data))
        scan = scenario_identity._scan(data)
    except scenario_identity.IdentityError as refused:
        raise _Unreadable(f"cannot be identified ({refused.reason})") from None
    # A `Background` covers every scenario in its scope: the whole feature, or
    # one `Rule`. Scope 0 is the feature; each `Rule` opens the next.
    scope, shared, placed = 0, {0: []}, []
    for block in scan.blocks:
        if block.kind == "rule":
            scope += 1
            shared[scope] = []
        elif block.kind == "background":
            kept = [
                scan.lines[n].rstrip()
                for n in range(block.start, block.end)
                if n not in scan.comments
            ]
            shared[scope].append(hashlib.sha256("\n".join(kept).rstrip().encode()).hexdigest())
        elif block.kind == "scenario":
            placed.append(scope)
    found = {}
    for scenario, where in zip(scenarios, placed, strict=True):
        covering = shared[0] + (shared[where] if where else [])
        context = hashlib.sha256("\n".join(covering).encode()).hexdigest()
        found[scenario.id] = (scenario.revision_digest, context)
    return found


def _compare_scenarios(path: str, was: dict, now: dict) -> list[DefinitionFinding]:
    findings = []
    for identifier, (revision, context) in was.items():
        if identifier not in now:
            code, what = "scenario-removed", "was removed"
        elif now[identifier][0] != revision:
            code, what = "scenario-altered", "was altered"
        elif now[identifier][1] != context:
            code, what = "shared-steps-changed", "has different Background steps before it"
        else:
            continue
        findings.append(
            DefinitionFinding(code, path, identifier, f"{path}: scenario {identifier} {what}")
        )
    return findings


# --- criteria ----------------------------------------------------------------


def _criteria(package: str, data: bytes) -> dict:
    """{"named": bool, "items": {(list, identifier): item}, "rest": everything else}."""
    try:
        document = parse_document(_bounded(data))
    except (DocumentError, ValueError, RecursionError):
        raise _Unreadable("cannot be read") from None
    if not isinstance(document, dict):
        raise _Unreadable("is not a mapping")
    llm = document.get("llm_evaluation", {})
    if not isinstance(llm, dict):
        raise _Unreadable("cannot be identified (parse_error)")
    sources = {"llm_evaluation": llm.get("criteria", []), "criteria": document.get("criteria", [])}
    items, named, seen = {}, True, set()
    for source in _LISTS:
        listed = sources[source]
        if not isinstance(listed, list):
            raise _Unreadable("cannot be identified (parse_error)")
        for item in listed:
            name = item.get("name") if isinstance(item, dict) else None
            if not isinstance(name, str) or not name:
                named = False
                continue
            if name in seen:
                raise _Unreadable("cannot be identified (slug_collision)")
            seen.add(name)
            items[(source, criterion_id(package, name))] = item
    rest = {key: value for key, value in document.items() if key != "criteria"}
    if "llm_evaluation" in document:
        rest["llm_evaluation"] = {key: value for key, value in llm.items() if key != "criteria"}
    return {"named": named, "items": items, "rest": rest, "document": document}


def _compare_criteria(path: str, was: dict, now: dict) -> list[DefinitionFinding]:
    if not was["named"] or not now["named"]:
        if was["document"] == now["document"]:
            return []
        return [
            DefinitionFinding(
                "criteria-changed",
                path,
                None,
                f"{path} changed, and its criteria are not all named, "
                "so they cannot be compared item by item",
            )
        ]
    findings = []
    for (source, identifier), item in was["items"].items():
        if (source, identifier) not in now["items"]:
            code, what = "criterion-removed", "was removed"
        elif now["items"][(source, identifier)] != item:
            code, what = "criterion-altered", "was altered"
        else:
            continue
        findings.append(
            DefinitionFinding(code, path, identifier, f"{path}: criterion {identifier} {what}")
        )
    if was["rest"] != now["rest"]:
        findings.append(
            DefinitionFinding(
                "criteria-changed", path, None, f"{path} changed outside its list of criteria"
            )
        )
    return findings
