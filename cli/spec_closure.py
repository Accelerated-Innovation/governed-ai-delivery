"""Resolve a Gherkin element, build its closure, and digest it — increment 10.

What "changed" means here is the owner's materiality test, and every choice in
this module serves it:

    A Gherkin edit makes it a different feature when it changes what a passing
    implementation would do, for whom, or under what conditions — rather than
    how the same behavior is described. The tell: if any step definition,
    test, or previously passing implementation could now fail, the contract
    changed, and the contract is the feature.

So the digest covers the **closure**, not the body: a scenario's effective
steps after `Background` inheritance, its `Examples` rows, its docstrings and
tables, its `Rule`'s text, and its inherited tags. Digesting the body alone
would let a changed `Background` alter approved behavior silently
(BEHAVIORAL_BASELINE_CONTRACT §5), and would flag extracting a shared `Given`
into a `Background` — a refactor the test explicitly calls editorial.

**The digest says *different*, never *why*.** Classification by clause role
lives in the differ, because the response is tiered and a hash cannot tell a
reworded `Then` from a changed one.

Parsing is `gherkin-official`, the Cucumber team's own parser. Hand-rolling is
not an option: it cannot preserve `Background` scoping, `Examples` tables,
step data tables, docstrings or tag inheritance, and every one of those is
part of the closure.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

#: Only authored identity resolves. `id_source: derived` is rejected by the
#: contract (§4.1) because a slugified name is stable only as long as the name
#: is, so binding an approval to one binds it to a rename.
_TAG = re.compile(r"^@(rule|scenario|nfr|evaluation|design|agent-authority):([a-z0-9][a-z0-9-]*)$")

_OUTLINE_KEYWORDS = {"Scenario Outline", "Scenario Template"}


class SpecParseError(RuntimeError):
    """The feature text could not be parsed at all."""


class AmbiguousReference(RuntimeError):
    """One slug matched more than one element.

    There is no single right answer, and picking the first would bind an
    approval to file order.
    """


class ParserUnavailable(RuntimeError):
    """`gherkin-official` is not installed.

    Raised rather than degrading to a shallow parse. A shallow parse would
    mis-compute the closure — wrong `Background` scoping, missing tag
    inheritance — and answer confidently with the wrong verdict about whether
    an approval still holds. Refusing is the only honest failure here.
    """


@dataclass(frozen=True)
class Element:
    """A resolved, authored-identity element and where it sits."""

    kind: str
    slug: str
    node: dict[str, Any]
    rule: dict[str, Any] | None = None


@dataclass(frozen=True)
class Closure:
    """Everything a selected element's approval depends on.

    `steps` are **effective**: `Background` steps, then any `Rule`-level
    `Background`, then the element's own — which is what makes extracting a
    shared `Given` into a `Background` invisible, as the test requires.
    """

    kind: str
    slug: str
    name: str
    steps: tuple[tuple[str, str, str], ...] = ()   # (keyword, text, payload)
    examples: tuple[tuple[str, ...], ...] = ()
    tags: tuple[str, ...] = ()
    rule_text: str = ""
    rule_description: str = ""
    problems: tuple[str, ...] = field(default=(), compare=False)


# --- parsing -----------------------------------------------------------------

def parse_feature(text: str) -> dict[str, Any]:
    try:
        from gherkin.parser import Parser
    except ImportError as missing:  # pragma: no cover - environment, not logic
        raise ParserUnavailable(
            "gherkin-official is required to validate a baseline against a working tree. "
            "Install it (pip install 'gherkin-official>=32,<40'); this check refuses rather "
            "than falling back to a shallow parse, which would answer with the wrong closure."
        ) from missing
    try:
        return Parser().parse(_normalize_source(text))
    except Exception as broken:
        raise SpecParseError(str(broken)) from broken


def _normalize_source(text: str) -> str:
    """Line endings and Unicode form, before anything reads the text.

    A Windows checkout and a macOS checkout are not behavior changes; NFD from
    one filesystem and NFC from another are the same characters.
    """
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


# --- resolution ---------------------------------------------------------------

def _authored(tags: list[dict[str, Any]]) -> list[tuple[str, str]]:
    found = []
    for tag in tags or ():
        match = _TAG.match((tag.get("name") or "").strip())
        if match:
            found.append((match.group(1), match.group(2)))
    return found


def _walk(doc: dict[str, Any]):
    """Every scenario and rule, carrying the rule each scenario sits under."""
    feature = (doc or {}).get("feature") or {}
    for child in feature.get("children") or ():
        if "rule" in child:
            rule = child["rule"]
            yield "rule", rule, rule
            for inner in rule.get("children") or ():
                if "scenario" in inner:
                    yield "scenario", inner["scenario"], rule
        elif "scenario" in child:
            yield "scenario", child["scenario"], None


def resolve(doc: dict[str, Any], kind: str, slug: str) -> Element | None:
    """The single element carrying `@<kind>:<slug>`, or None.

    Raises `AmbiguousReference` when two carry it — see that exception.
    """
    # `rule` and `scenario` name a Gherkin element; `nfr`, `evaluation`,
    # `design` and `agent-authority` are obligations *tagged onto* one, and
    # there is no Gherkin node of those kinds. Constraining the node type for
    # them made every constraint reference unresolvable — reported as approved
    # behaviour having disappeared, when it had simply never been looked for
    # in the right place.
    structural = kind in {"rule", "scenario"}
    matches = [
        Element(kind=kind, slug=slug, node=node, rule=rule)
        for node_kind, node, rule in _walk(doc)
        if (node_kind == kind if structural else True)
        and (kind, slug) in _authored(node.get("tags"))
    ]
    if len(matches) > 1:
        raise AmbiguousReference(
            f"{kind}:{slug} matches {len(matches)} elements; an approval cannot bind to "
            f"whichever the parser reached first."
        )
    return matches[0] if matches else None


# --- closure -------------------------------------------------------------------

def _payload(step: dict[str, Any]) -> str:
    """A step's data table or docstring, as text.

    Docstring indentation is **preserved**. A docstring is payload, and a YAML
    or JSON body means something different reindented — unlike Gherkin's own
    indentation, which is presentational.
    """
    doc = step.get("docString")
    if doc:
        # The media type is part of the payload: the same bytes marked json
        # and marked yaml are read differently by whatever consumes them.
        return "doc:" + json.dumps(
            [doc.get("mediaType") or "", doc.get("content") or ""], ensure_ascii=False
        )
    table = step.get("dataTable")
    if table:
        # JSON-encoded, not pipe-joined. A cell containing a literal pipe
        # serialized exactly like two cells, so `| a|b | c |` and `| a | b | c |`
        # — materially different step inputs — shared a digest.
        rows = [
            [(c.get("value") or "").strip() for c in (r.get("cells") or ())]
            for r in (table.get("rows") or ())
        ]
        return "table:" + json.dumps(rows, ensure_ascii=False)
    return ""


#: `And`, `But` and `*` continue the preceding keyword rather than naming one.
_CONTINUATIONS = {"And", "But", "*"}


def _steps(node: dict[str, Any], carried: str = "") -> list[tuple[str, str, str]]:
    """Steps with continuations resolved to the keyword they continue.

    `And a drafted response` and `Given a drafted response` bind to the same
    step definition — step definitions match on text, not keyword — so under
    the materiality test the difference cannot make an implementation fail.

    Resolving them is also what makes extracting a shared `Given` into a
    `Background` invisible: the extracted step arrives as `Given` in the
    background and as `And` inline, and only the resolved form is the same
    behavior either way. Keeping the literal keyword would have flagged the
    one refactor the test explicitly calls editorial.
    """
    out = []
    previous = carried
    for step in node.get("steps") or ():
        keyword = (step.get("keyword") or "").strip()
        if keyword in _CONTINUATIONS and previous:
            keyword = previous
        else:
            previous = keyword
        text = " ".join((step.get("text") or "").split())
        out.append((keyword, text, _payload(step)))
    return out


def _backgrounds(doc: dict[str, Any], rule: dict[str, Any] | None) -> list[tuple[str, str, str]]:
    steps: list[tuple[str, str, str]] = []
    feature = (doc or {}).get("feature") or {}
    for child in feature.get("children") or ():
        if "background" in child:
            steps += _steps(child["background"])
    for child in (rule or {}).get("children") or ():
        if "background" in child:
            steps += _steps(child["background"])
    return steps


def _examples(node: dict[str, Any]) -> list[tuple[str, ...]]:
    """Rows as a **set** — deduplicated, then sorted.

    A reorder changes neither the input domain the contract covers nor whether
    any implementation passes. Adding or removing a *distinct* row does, and
    still registers. A duplicate row runs the scenario twice on identical
    inputs and covers nothing new, so sorting without deduplicating made an
    unchanged input domain read as a semantic change.

    A block's own tags travel with its rows: Gherkin allows tagging an
    `Examples` block, and such a tag can bind those generated cases to a gate.
    Discarding them let a gate change pass with an unchanged digest.
    """
    rows = set()
    for block in node.get("examples") or ():
        block_tags = tuple(sorted(
            (t.get("name") or "").strip() for t in (block.get("tags") or ()) if t.get("name")
        ))
        header = tuple(
            (c.get("value") or "").strip()
            for c in ((block.get("tableHeader") or {}).get("cells") or ())
        )
        for row in block.get("tableBody") or ():
            values = tuple((c.get("value") or "").strip() for c in (row.get("cells") or ()))
            rows.add(block_tags + ("@",) + header + ("=",) + values)
    return sorted(rows)


def _empty_example_blocks(node: dict[str, Any]) -> list[str]:
    """Header-only blocks, checked per block rather than in aggregate.

    An outline with one populated block and one header-only block has a
    non-empty aggregate, so the empty block sailed straight through the
    refusal it was supposed to trip.
    """
    empty = []
    for index, block in enumerate(node.get("examples") or (), start=1):
        if not (block.get("tableBody") or ()):
            empty.append((block.get("name") or "").strip() or f"#{index}")
    return empty


def _inherited_tags(doc: dict[str, Any], element: Element) -> list[str]:
    feature = (doc or {}).get("feature") or {}
    names = [t.get("name", "") for t in (feature.get("tags") or ())]
    names += [t.get("name", "") for t in ((element.rule or {}).get("tags") or ())]
    names += [t.get("name", "") for t in (element.node.get("tags") or ())]
    return sorted({n.strip() for n in names if n.strip()})


def closure(doc: dict[str, Any], element: Element) -> Closure:
    node = element.node
    background = _backgrounds(doc, element.rule)
    # The scenario's first step may be a continuation of the background's last,
    # so the carried keyword crosses that boundary exactly as a runner sees it.
    own = _steps(node, carried=background[-1][0] if background else "")
    effective = tuple(background + own) if element.kind == "scenario" else ()

    problems: list[str] = []
    if element.kind == "scenario" and not own:
        # Not a digest question: an empty closure hashes perfectly stably, so a
        # scenario that silently lost its steps would re-approve cleanly the
        # moment someone accepted the diff. The likeliest cause is a lowercase
        # keyword, which the parser accepts without complaint.
        problems.append(f"scenario:{element.slug} has no steps of its own")
    keyword = (node.get("keyword") or "").strip()
    if keyword in _OUTLINE_KEYWORDS and not _examples(node):
        problems.append(f"scenario:{element.slug} is an outline with no Examples rows")
    for name in _empty_example_blocks(node):
        problems.append(f"scenario:{element.slug} has an Examples block with no rows ({name})")
    if element.kind == "rule" and not (node.get("children") or ()):
        problems.append(f"rule:{element.slug} has no body")

    return Closure(
        kind=element.kind,
        slug=element.slug,
        name=(node.get("name") or "").strip(),
        steps=effective,
        examples=tuple(_examples(node)),
        tags=tuple(_inherited_tags(doc, element)),
        rule_text=((element.rule or {}).get("name") or "").strip(),
        rule_description=" ".join(((element.rule or {}).get("description") or "").split()),
        problems=tuple(problems),
    )


def structural_problems(c: Closure) -> list[str]:
    """Conditions a digest cannot express, because emptiness hashes stably."""
    return list(c.problems)


# --- digest ---------------------------------------------------------------------

def content_digest(c: Closure) -> str:
    """Tamper evidence for the recorded selection — not a classifier.

    What it is *for*: making "a manifest edited to hide an altered scenario"
    detectable, so the baseline's claim about its own coverage can be checked
    rather than trusted. What decides the tiered response is the differ.

    The element's **name is excluded**. Renaming a scenario changes no step
    definition and no assertion, and the contract already refuses derived
    identity precisely so a rename cannot move an approval.
    """
    payload = {
        "kind": c.kind,
        "slug": c.slug,
        "steps": [list(s) for s in c.steps],
        "examples": [list(r) for r in c.examples],
        "tags": list(c.tags),
        "rule_text": c.rule_text,
        "rule_description": c.rule_description,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
