"""Check a working tree against an approved baseline — increment 10.

Supplies the two sides the classifier compares. The **approved** side comes
from the immutable revision `sources[].revision` pins; the **current** side
from the working tree. That pin is what makes classification possible at all:
a recorded digest can say *different*, never *which clause moved*, and the
response in this system is tiered by exactly that.

**Consistency, not authority.** This answers *the working tree still says what
the baseline recorded*. Whether that baseline **currently carries authority**
is the engine's question (increment 11). Conflating them would let a locally
consistent tree read as authorized, which is the same error as inferring a
commitment from a card state.

**Read-only, and it must be unable to be otherwise.** No rewriting a spec to
make it pass, no adding a missing `@scenario:` tag during enforcement, no
silent manifest upgrade. A validator that can edit what it validates is a
formatter.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from cli import spec_closure, spec_diff
from cli.baseline import validate_baseline

SUPPORTED_VERSIONS = (1,)

_REF = re.compile(r"^(?P<source>[^/]+)/(?P<feature>.+)#(?P<kind>[a-z-]+):(?P<slug>[a-z0-9][a-z0-9-]*)$")


@dataclass(frozen=True)
class RefDifference:
    """A clause that moved, carrying the reference it moved in."""

    ref: str
    role: str
    detail: str
    tier: str = "semantic"
    actor_shaped: bool = False


@dataclass
class Report:
    """What changed, what could not be checked, and what that voids.

    `refusals` are not a softer kind of difference. They are the cases where
    the check could not be performed — an unresolvable reference, an
    unreachable revision, a scenario emptied to nothing — and each one means
    *this approval cannot currently be confirmed*, which is a stronger
    statement than "something changed".
    """

    differences: list[RefDifference] = field(default_factory=list)
    refusals: list[str] = field(default_factory=list)
    voided: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.differences and not self.refusals


def _feature_file(root: Path, source_path: str, feature_key: str) -> Path | None:
    """Where a feature key resolves, without leaving its source.

    Traversal is refused by resolving and comparing against the base rather
    than by inspecting the string: `..` is the obvious attempt and not the
    only one, and a symlink out of the tree reads as innocent text.
    """
    base = (root / (source_path or "")).resolve()
    for candidate in (base / f"{feature_key}.feature", base / feature_key):
        try:
            resolved = candidate.resolve()
        except OSError:  # pragma: no cover - unreadable path
            continue
        if not resolved.is_relative_to(base):
            return None
        if resolved.is_file():
            return resolved
        if resolved.is_dir():
            for feature in sorted(resolved.glob("*.feature")):
                # Resolved *again*, because the directory being inside the
                # source says nothing about a symlink within it. Without this
                # the current closure could come from outside the source while
                # the approved side loaded from the same lexical path in git.
                inner = feature.resolve()
                if not inner.is_relative_to(base):
                    return None
                return inner
    return base / f"{feature_key}.feature"  # for the "missing" message


def _at_revision(root: Path, revision: str, relative: str) -> str | None:
    """The file's content at the pinned revision, or None if unreachable."""
    try:
        done = subprocess.run(
            ["git", "-C", str(root), "show", f"{revision}:{relative}"],
            capture_output=True, text=True, check=False,
        )
    except OSError:  # pragma: no cover - git absent
        return None
    return done.stdout if done.returncode == 0 else None


def _closure(text: str, kind: str, slug: str) -> tuple[spec_closure.Closure | None, str | None]:
    try:
        doc = spec_closure.parse_feature(text)
    except spec_closure.ParserUnavailable as missing:
        # The module promises a refusal rather than a shallow parse. Letting
        # this escape gave a standard install a traceback where the contract
        # said controlled non-zero.
        return None, str(missing)
    except spec_closure.SpecParseError as broken:
        return None, f"does not parse: {broken}"
    try:
        element = spec_closure.resolve(doc, kind, slug)
    except spec_closure.AmbiguousReference as ambiguous:
        return None, str(ambiguous)
    if element is None:
        return None, (
            f"unresolvable: no element carries @{kind}:{slug}. Approved behavior does not "
            f"disappear by deleting a tag — the reference simply stops resolving."
        )
    return spec_closure.closure(doc, element), None


def approved_digest(baseline: dict, entry: dict, roots: dict[str, Path]) -> str | None:
    """The digest of an entry's closure at the revision the baseline pins.

    Exposed so a baseline can be issued with digests that mean something,
    rather than hand-authored ones that mean nothing — which is what the
    fixtures carried before this existed.
    """
    resolved = _resolve_entry(baseline, entry, roots)
    return None if resolved.closure_then is None else spec_closure.content_digest(
        resolved.closure_then
    )


@dataclass
class _Resolved:
    closure_then: spec_closure.Closure | None = None
    closure_now: spec_closure.Closure | None = None
    refusals: list[str] = field(default_factory=list)


def _resolve_entry(baseline: dict, entry: dict, roots: dict[str, Path]) -> _Resolved:
    """Both sides of one reference, or the reasons neither could be had."""
    out = _Resolved()
    ref = entry.get("ref", "")
    match = _REF.match(ref)
    if match is None:
        out.refusals.append(f"{ref}: not a qualified reference")
        return out
    source_key, feature_key = match["source"], match["feature"]
    kind, slug = match["kind"], match["slug"]

    sources = {s.get("source_key"): s for s in baseline.get("sources") or ()}
    source = sources.get(source_key)
    if source is None:
        out.refusals.append(
            f"{ref}: names source {source_key!r}, which the baseline does not declare"
        )
        return out

    if (source.get("kind") or "repository") != "repository":
        # `git show` cannot read a released package, and answering "revision
        # not reachable" would send the reader hunting for a commit that was
        # never meant to exist.
        out.refusals.append(
            f"{ref}: source {source_key!r} is a {source.get('kind')} source, and this "
            f"checker reads approved content from a repository revision. A package "
            f"source needs its own resolution and does not have one yet."
        )
        return out

    root = roots.get(source_key)
    if root is None:
        out.refusals.append(
            f"{ref}: no local checkout supplied for source {source_key!r}, so the "
            f"approved revision cannot be read"
        )
        return out

    path = _feature_file(Path(root), source.get("path") or "", feature_key)
    if path is None:
        out.refusals.append(
            f"{ref}: feature key resolves outside its source — traversal refused"
        )
        return out
    if not path.is_file():
        out.refusals.append(f"{ref}: {path.name} is not present in the working tree")
        return out

    now, problem = _closure(path.read_text(encoding="utf-8"), kind, slug)
    if problem:
        out.refusals.append(f"{ref}: {problem}")
        return out
    assert now is not None
    structural = spec_closure.structural_problems(now)
    if structural:
        out.refusals.extend(f"{ref}: {p}" for p in structural)
        return out
    out.closure_now = now

    relative = str(path.relative_to(Path(root).resolve()))
    approved_text = _at_revision(Path(root), source.get("revision", ""), relative)
    if approved_text is None:
        out.refusals.append(
            f"{ref}: the approved revision {source.get('revision', '')[:12]}… is not "
            f"reachable in this checkout, so nothing can be compared against it"
        )
        return out

    then, problem = _closure(approved_text, kind, slug)
    if problem:
        out.refusals.append(f"{ref}: at the approved revision, {problem}")
        return out
    out.closure_then = then
    return out


def check(baseline: dict, roots: dict[str, Path]) -> Report:
    """Compare every selected behavior against the revision it was approved at.

    `roots` maps a source key to a local checkout. Nothing is fetched: a
    source this caller cannot reach is refused rather than skipped, because
    "no differences" and "I could not look" are answers a protected boundary
    must never confuse.
    """
    report = Report()

    version = baseline.get("version")
    if version not in SUPPORTED_VERSIONS:
        report.refusals.append(
            f"unsupported baseline version {version!r}; this checker understands "
            f"{list(SUPPORTED_VERSIONS)}"
        )
        return report

    # Increment 01 built this and nothing called it, so a document with no
    # sources and no selection exited zero — success reported for a baseline
    # with no approved scope at all. Moving revisions and duplicate source
    # declarations went the same way.
    errors, _warnings = validate_baseline(baseline)
    if errors:
        report.refusals.extend(f"baseline is not valid: {e}" for e in errors)
        return report

    # Constraints are approved scope too. Iterating only selected_behavior
    # meant a changed NFR, evaluation, design or agent-authority obligation
    # reported clean.
    entries = list(baseline.get("selected_behavior") or ())
    entries += list(baseline.get("constraints") or ())
    if not entries:
        # "Nothing to check" must not report as "nothing wrong". A baseline
        # with no approved scope exited zero, which is the most confident
        # possible way to say nothing at all.
        #
        # `validate_baseline` does not catch this: the emptiness rule lives in
        # the JSON Schema, and jsonschema is a test dependency rather than a
        # runtime one. So the refusal belongs here too.
        report.refusals.append(
            "the baseline selects no behavior and declares no constraints, so there is "
            "no approved scope to check against"
        )
        return report

    for entry in entries:
        ref = entry.get("ref", "")
        resolved = _resolve_entry(baseline, entry, roots)
        if resolved.refusals:
            report.refusals.extend(resolved.refusals)
            continue
        assert resolved.closure_then is not None and resolved.closure_now is not None

        recorded = entry.get("content_digest")
        if recorded:
            # What the digest is *for*. Comparing it against the closure at
            # the pinned revision is what makes a manifest edited to hide an
            # altered scenario detectable — the module said so and did not do
            # it, so a tampered digest reported clean whenever the revision
            # and the working tree agreed.
            actual = spec_closure.content_digest(resolved.closure_then)
            if actual != recorded:
                report.refusals.append(
                    f"{ref}: the recorded content_digest does not match the closure at "
                    f"the approved revision. The baseline's own record of what it covers "
                    f"cannot be trusted."
                )
                continue

        for difference in spec_diff.classify(resolved.closure_then, resolved.closure_now):
            report.differences.append(
                RefDifference(
                    ref=ref,
                    role=difference.role,
                    detail=difference.detail,
                    tier=difference.tier,
                    actor_shaped=difference.actor_shaped,
                )
            )

    report.voided = spec_diff.voided_by(
        [
            spec_diff.Difference(
                role=d.role, detail=d.detail, tier=d.tier, actor_shaped=d.actor_shaped
            )
            for d in report.differences
        ]
    )
    return report
