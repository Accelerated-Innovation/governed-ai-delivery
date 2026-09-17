#!/usr/bin/env python3
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
"""Behavioral baseline — the portable contract half.

A baseline records exactly which behavior a product commitment approved,
bound to immutable source revisions. This module owns two things about it
that have to be identical in every consumer, or the contract is not shared:

1. **Canonical form and digest.** Two consumers handed the same baseline must
   compute the same digest, and a consumer handed a re-indented or re-ordered
   copy must compute the *same* digest as for the original. Formatting is not
   part of what was approved; content is.
2. **The checks JSON Schema cannot express.** Reference integrity, duplicate
   and contradictory refs, derived identifiers, and version support are
   relationships between fields, which a schema does not see.

**What this module cannot do, by construction.** It cannot tell you whether a
baseline is approved. Nothing here reads authority, and nothing in the schema
can assert it — that answer comes from the decision service, freshly, at the
boundary that needs it. This module proves a baseline is *well-formed and
internally consistent*, which is the same split `cli/approval.py` draws
between what the working tree can prove and what only CI can.

Read-only by construction: nothing here writes, normalizes-in-place, or
repairs a baseline. A validator that fixes its input cannot be used to detect
drift, because it would erase the drift it exists to find.

The `(issues, warnings)` return shape follows `cli/fixes.py` and
`cli/approval.py`, so the eventual `validate` integration (increment 10) plugs
in without a new ABI.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any

# Versions this build of govkit understands. An unsupported version is a
# named error, never a pile of schema violations: a baseline from the future
# is not malformed, it is newer than this tool.
SUPPORTED_VERSIONS: tuple[int, ...] = (1,)

# The one key excluded from the digest. Advisory material — prototype shots,
# AI analyses, generated reports — is non-normative by definition, so revising
# it must not read as a change to approved behavior.
NON_NORMATIVE_KEYS: frozenset[str] = frozenset({"advisory"})

DIGEST_PREFIX = "sha256:"

# Reference kinds that carry behavior, and the kinds that carry constraints.
# Kept as one table rather than two branches so a new kind is added in exactly
# one place.
_REF_KINDS: frozenset[str] = frozenset(
    {"rule", "scenario", "nfr", "evaluation", "design", "agent-authority"}
)

# Which kinds each field may carry. Scope is behavior; constraints are the
# properties that behavior must hold to. Mixing them would let a Rule be
# recorded where no scope check looks for it.
_FIELD_KINDS: dict[str, frozenset[str]] = {
    "selected_behavior": frozenset({"rule", "scenario"}),
    "constraints": frozenset({"nfr", "evaluation", "design", "agent-authority"}),
}


def _normalize(value: Any) -> Any:
    """Recursively put a decoded JSON value into canonical form.

    Three normalizations, each covering a way two honest copies of the same
    baseline can differ on disk:

    - **Whole numbers → int.** `1` and `1.0` are the same number and both pass
      `"type": "integer"`, but they serialize differently. Booleans are
      excluded explicitly because `bool` subclasses `int`.
    - **Strings → Unicode NFC.** A macOS checkout can hand you NFD where Linux
      hands you NFC for the same characters. Without this, the same baseline
      digests differently on two developers' machines, which is exactly the
      cross-consumer disagreement the digest exists to rule out.
    - **Objects → key order dropped.** Handled at serialization by `sort_keys`.
    - **Arrays → sorted by canonical content.** Every array in a baseline is a
      *set*: the order someone listed two scenarios in is not part of what was
      approved. Sorting by each element's own canonical serialization gives a
      total order without special-casing per field.

    Numbers and booleans pass through. `advisory` is dropped by the caller,
    not here, because it is only non-normative at the top level.
    """
    if isinstance(value, bool):
        # Before the int branch: bool subclasses int in Python, and True must
        # stay `true`, never `1`.
        return value
    if isinstance(value, float) and value.is_integer():
        # `1` and `1.0` are the same number and both satisfy JSON Schema's
        # `"type": "integer"`, but json.dumps writes them as "1" and "1.0".
        # Without this, two baselines that differ only in how a producer
        # spelled a whole number digest differently — the exact cross-consumer
        # disagreement the digest exists to rule out.
        return int(value)
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        normalized = [_normalize(v) for v in value]
        return sorted(normalized, key=_stable_key)
    return value


def _stable_key(value: Any) -> str:
    """Total order over already-normalized values, by canonical serialization.

    Sorting mixed-type arrays by value would raise; sorting by their JSON text
    never does and is deterministic across runs and platforms.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_form(baseline: dict) -> dict:
    """The normative content of `baseline`, canonicalized.

    Drops the non-normative keys, then normalizes. The input is not mutated.
    """
    normative = {k: v for k, v in baseline.items() if k not in NON_NORMATIVE_KEYS}
    return _normalize(normative)


def canonical_bytes(baseline: dict) -> bytes:
    """The exact byte sequence the digest is taken over.

    Separate from `compute_digest` so a consumer in another language can be
    tested against these bytes directly — a digest mismatch tells you two
    implementations disagree, but not where, and the bytes do.
    """
    canonical = canonical_form(baseline)
    text = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return text.encode("utf-8")


def compute_digest(baseline: dict) -> str:
    """`sha256:<hex>` over the canonical bytes.

    Stable across key order, array order, indentation, trailing whitespace,
    line endings and Unicode composition — none of which is behavior. NOT
    stable across a changed scenario, Examples row, Background, constraint,
    exclusion or source revision, all of which are.
    """
    return DIGEST_PREFIX + hashlib.sha256(canonical_bytes(baseline)).hexdigest()


def _ref_kind(ref: str) -> str | None:
    """The kind segment of a qualified ref, or None when it is unparseable."""
    _, _, tail = ref.partition("#")
    kind, sep, _slug = tail.partition(":")
    return kind if sep and kind in _REF_KINDS else None


def _ref_source(ref: str) -> str:
    """The source_key segment of a qualified ref (text before the first '/')."""
    return ref.partition("/")[0]


def _all_behavior_entries(baseline: dict) -> list[tuple[str, dict]]:
    """Every behaviorRef in the document, tagged with the field it came from."""
    entries: list[tuple[str, dict]] = []
    for field in ("selected_behavior", "constraints"):
        for entry in baseline.get(field, []) or []:
            if isinstance(entry, dict):
                entries.append((field, entry))
    return entries


def check_version(baseline: dict) -> list[str]:
    """Version support, as its own named check.

    Split out so callers can refuse an unsupported baseline *before* running
    reference checks whose messages would be meaningless against a shape this
    build does not understand.
    """
    version = baseline.get("version")
    if version in SUPPORTED_VERSIONS:
        return []
    supported = ", ".join(str(v) for v in SUPPORTED_VERSIONS)
    return [
        f"Unsupported baseline version {version!r}: this govkit understands "
        f"version(s) {supported}. A newer baseline needs a newer govkit — it is "
        f"not malformed."
    ]


def check_sources(baseline: dict) -> list[str]:
    """Source declarations must be unambiguous and must stay inside themselves.

    Two checks the schema cannot make. It can require each field's shape, but
    it cannot see that two entries claim the same `source_key`, and while it
    can pattern-match a path it cannot explain *why* a traversal was refused.
    """
    issues: list[str] = []
    seen: set[str] = set()

    for source in baseline.get("sources", []) or []:
        if not isinstance(source, dict):
            continue
        key = source.get("source_key", "")

        if key in seen:
            issues.append(
                f"sources: duplicate source_key {key!r}. Two declarations of one key make "
                f"every reference through it ambiguous — a consumer cannot tell which "
                f"revision the approved content came from."
            )
        seen.add(key)

        path = source.get("path")
        if isinstance(path, str) and _escapes_source(path):
            issues.append(
                f"sources: source {key!r} has path {path!r}, which leaves the source tree. "
                f"Resolution outside the bound revision would read content the digest was "
                f"never taken against."
            )

    return issues


def _escapes_source(path: str) -> bool:
    """True when `path` is not a plain relative prefix inside the source.

    Rejects absolute paths, Windows separators and drive letters, and any `.`
    or `..` segment. Checked here as well as in the schema so the refusal
    carries a reason rather than a pattern mismatch.
    """
    if not path or path.startswith("/") or "\\" in path:
        return True
    if len(path) > 1 and path[1] == ":":
        return True
    return any(segment in ("", ".", "..") for segment in path.split("/"))


def check_references(baseline: dict) -> tuple[list[str], list[str]]:
    """Reference integrity and identity rules. Returns `(issues, warnings)`.

    These are the relationships a JSON Schema cannot see: whether a reference
    resolves to a declared source, whether the same element was both selected
    and excluded, and whether an identifier is stable enough to approve.
    """
    issues: list[str] = []
    warnings: list[str] = []

    declared = {
        s.get("source_key") for s in baseline.get("sources", []) or [] if isinstance(s, dict)
    }

    seen: dict[str, str] = {}
    for field, entry in _all_behavior_entries(baseline):
        ref = entry.get("ref", "")

        source = _ref_source(ref)
        if source not in declared:
            issues.append(
                f"{field}: reference {ref!r} names source {source!r}, which is not "
                f"declared in `sources`. An unresolvable reference cannot be approved."
            )

        kind = _ref_kind(ref)
        allowed = _FIELD_KINDS[field]
        if entry.get("kind") not in allowed:
            issues.append(
                f"{field}: {ref!r} is declared as {entry.get('kind')!r}, which belongs in "
                f"{'constraints' if field == 'selected_behavior' else 'selected_behavior'}. "
                f"{field} carries {' or '.join(sorted(allowed))}. Behavior recorded as a "
                f"constraint is invisible to every scope check."
            )
        if kind is not None and entry.get("kind") != kind:
            issues.append(
                f"{field}: reference {ref!r} is a {kind!r} but is declared as "
                f"{entry.get('kind')!r}. The declared kind and the reference must agree."
            )

        if entry.get("id_source") == "derived":
            issues.append(
                f"{field}: reference {ref!r} has id_source 'derived'. A derived "
                f"identifier is slugified from an element's name and changes when the "
                f"name does, so it cannot bind an approval. Add an explicit "
                f"@{kind or 'rule'}:<slug> tag to the source and reference that."
            )

        if ref in seen:
            issues.append(
                f"Duplicate reference {ref!r} appears in both {seen[ref]} and {field}. "
                f"One element, one entry."
            )
        else:
            seen[ref] = field

    excluded_refs: set[str] = set()
    for excluded in baseline.get("exclusions", []) or []:
        if not isinstance(excluded, dict):
            continue
        ref = excluded.get("ref", "")

        if ref in seen:
            issues.append(
                f"Reference {ref!r} is both selected in {seen[ref]} and listed as an "
                f"exclusion. It is either in scope or out of it, not both."
            )

        if ref in excluded_refs:
            issues.append(
                f"exclusions: duplicate reference {ref!r}. Canonicalization treats every "
                f"array as a set, so a repeated exclusion is silently collapsed — record it "
                f"once."
            )
        excluded_refs.add(ref)

        source = _ref_source(ref)
        if source not in declared:
            issues.append(
                f"exclusions: reference {ref!r} names source {source!r}, which is not "
                f"declared in `sources`. An exclusion is a record of what was considered "
                f"and refused; one that cannot be resolved records nothing."
            )

    return issues, warnings


def check_commitment_readiness(baseline: dict) -> list[str]:
    """Blocking unresolved questions. Returns issues.

    Separate from reference integrity because it answers a different question:
    not 'is this baseline well-formed' but 'is it finished enough to put in
    front of a human for a decision'. A baseline can be perfectly well-formed
    and still not ready.
    """
    blocking = [
        q.get("question", "<unstated>")
        for q in baseline.get("unresolved_questions", []) or []
        if isinstance(q, dict) and q.get("blocks_commitment")
    ]
    return [f"Unresolved question blocks commitment: {question}" for question in blocking]


def validate_baseline(baseline: dict) -> tuple[list[str], list[str]]:
    """Every non-schema check, in one call. Returns `(issues, warnings)`.

    Version is checked first and short-circuits: running reference checks
    against a shape this build does not understand produces confident,
    misleading messages about fields that may mean something else entirely in
    that version.

    Schema conformance is the caller's job — this takes an already-parsed
    document and never reads a file, so it can be run against a baseline that
    arrived over an API just as easily as one on disk.
    """
    version_issues = check_version(baseline)
    if version_issues:
        return version_issues, []

    issues, warnings = check_references(baseline)
    issues.extend(check_sources(baseline))
    issues.extend(check_commitment_readiness(baseline))
    return issues, warnings
