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
"""Scenario identity and revision digests, as the Product Definition Graph computes them.

A scenario's identifier and revision digest must equal the ones the graph
indexed, or the graph refuses a whole verification run. This module therefore
mirrors two rules it does not own, and copied fixtures pin it to both:

- The identifier format and the slug rule belong to `aipos-plugins`
  (`references/spec-identifiers.md`, `repo_ingest.slugify`).
- The reader and the revision digest belong to `discovery-engine`
  (`requirements_gherkin.py`, ADR-AIG-035).

Do not improve either rule here. A change that makes this reader more
forgiving or more correct than the engine's makes its digests wrong.

It is pure: bytes in, scenarios out. It holds no step text; a revision is
hashed and discarded. A `Background` ends a scenario's span and is in no
scenario's digest, as in the engine.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

TITLE_MAX = 200
# Why the engine would refuse the feature file. A public vocabulary: add, never rename.
REASONS = ("parse_error", "slug_collision", "invalid_identifier", "title_too_long")

_AUTHORED_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_LANGUAGE = re.compile(r"^#\s*language\s*:\s*(\S+)")
_DOC_STRING_DELIMITERS = ('"""', "```")
_OUTLINES = frozenset({"Scenario Outline", "Scenario Template"})
# Keyword (the text before the line's first colon) -> block kind.
_KEYWORDS = {
    "Feature": "feature",
    "Rule": "rule",
    "Background": "background",
    "Scenario Outline": "scenario",
    "Scenario Template": "scenario",
    "Scenario": "scenario",
    "Example": "scenario",
    "Examples": "examples",
    "Scenarios": "examples",
}
# A scenario's revision span ends where one of these blocks (or its tags) begins.
_SPAN_ENDS = frozenset({"feature", "rule", "background", "scenario"})


class IdentityError(ValueError):
    """The feature file cannot be identified. `reason` is one of `REASONS`."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Scenario:
    id: str
    slug: str
    title: str
    tags: tuple[str, ...]
    id_source: str  # "tag" when authored as @scenario:<slug>, "derived" from the title
    revision_digest: str
    outline: bool


@dataclass
class _Block:
    kind: str
    keyword: str
    title: str
    tags: tuple[str, ...]
    start: int  # first line of the block's tags, or its keyword line when it has none
    end: int = 0  # one past its revision span; meaningful for scenarios only


@dataclass
class _Scan:
    lines: list[str]
    blocks: list[_Block] = field(default_factory=list)
    comments: set[int] = field(default_factory=set)


def slugify(name: str) -> str:
    """The skill pack's derived slug: non-alphanumeric ASCII runs to `-`, trimmed, lowercased."""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name.strip()).strip("-").lower()
    return slug or "unnamed"


def scenario_id(package: str, slug: str) -> str:
    return f"{package}#scenario:{slug}"


def read_scenarios(package: str, data: bytes) -> tuple[Scenario, ...]:
    """The scenarios of one feature file, in source order. Raises `IdentityError`."""
    scan = _scan(data)
    features = [block for block in scan.blocks if block.kind == "feature"]
    if len(features) != 1 or scan.blocks[0] is not features[0]:
        raise IdentityError("parse_error")
    _check_title(features[0].title)
    seen: set[str] = set()
    rules: set[str] = set()
    scenarios = []
    for block in scan.blocks:
        if block.kind == "rule":
            # A rule is not reported, but a rule the engine refuses makes it
            # refuse the whole file, so its identity is checked the same way.
            _identity(block, "@rule:", rules)
        if block.kind != "scenario":
            continue
        _check_title(block.title)
        slug, source = _identity(block, "@scenario:", seen)
        scenarios.append(
            Scenario(
                id=scenario_id(package, slug),
                slug=slug,
                title=block.title,
                tags=block.tags,
                id_source=source,
                revision_digest=_revision_digest(scan, block),
                outline=block.keyword in _OUTLINES,
            )
        )
    return tuple(scenarios)


def _scan(data: bytes) -> _Scan:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise IdentityError("parse_error") from None
    scan = _Scan(text.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
    tags: list[str] = []
    tags_start: int | None = None
    doc_string: str | None = None
    for number, line in enumerate(scan.lines):
        stripped = line.strip()
        if doc_string is not None:
            if stripped.startswith(doc_string):
                doc_string = None
            continue
        if stripped.startswith(_DOC_STRING_DELIMITERS):
            doc_string = stripped[:3]
        elif stripped.startswith("#"):
            scan.comments.add(number)
            language = _LANGUAGE.match(stripped)
            if language and language.group(1) != "en":
                raise IdentityError("parse_error")
        elif stripped.startswith("@"):
            tags_start = number if tags_start is None else tags_start
            tags.extend(_tags(stripped))
        elif found := _keyword(stripped):
            keyword, title = found
            start = number if tags_start is None else tags_start
            scan.blocks.append(_Block(_KEYWORDS[keyword], keyword, title, tuple(tags), start))
            tags, tags_start = [], None
    if doc_string is not None:
        raise IdentityError("parse_error")
    end = len(scan.lines)
    for block in reversed(scan.blocks):
        block.end = end
        if block.kind in _SPAN_ENDS:
            end = block.start
    return scan


def _tags(line: str) -> list[str]:
    found: list[str] = []
    for token in line.split():
        if token.startswith("#"):
            break
        found.append(token)
    return found


def _keyword(line: str) -> tuple[str, str] | None:
    keyword, colon, title = line.partition(":")
    if colon and keyword.strip() in _KEYWORDS:
        return keyword.strip(), title.strip()
    return None


def _check_title(title: str) -> None:
    if len(title) > TITLE_MAX:
        raise IdentityError("title_too_long")


def _identity(block: _Block, prefix: str, seen: set[str]) -> tuple[str, str]:
    authored = [tag[len(prefix) :] for tag in block.tags if tag.startswith(prefix)]
    if len(authored) > 1 or (authored and not _AUTHORED_SLUG.match(authored[0])):
        raise IdentityError("invalid_identifier")
    slug = authored[0] if authored else slugify(block.title)
    if slug in seen:
        raise IdentityError("slug_collision")
    seen.add(slug)
    return slug, "tag" if authored else "derived"


def _revision_digest(scan: _Scan, block: _Block) -> str:
    kept = [scan.lines[n].rstrip() for n in range(block.start, block.end) if n not in scan.comments]
    return hashlib.sha256("\n".join(kept).rstrip().encode()).hexdigest()
