#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Inspect an existing feature package and draft a baseline from it.

WHAT THE PLAN ASKS FOR
    "An explicit conversion/inspection path for existing packages: preserve
    IDs where authored; flag derived identities; retain history and require
    a real decision for the new baseline" — and, in the same breath, "never
    convert an old 'Committed' label into a new approval automatically".

    There is no 'Committed' label in govkit to convert, so that lands as
    something simpler and stronger: **this path is incapable of producing an
    approval.** What it emits is a draft that deliberately does not validate
    until a person supplies the parts only a person can.

WHY UNTAGGED ELEMENTS ARE FLAGGED RATHER THAN CONVERTED
    Increment 01 made a baseline reject `id_source: derived`: a slug taken
    from an element's name changes when the name does, so it cannot bind an
    approval. Inventing derived identities here would produce drafts refused
    later — or, worse, accepted and unstable. So the useful output is
    naming exactly which elements need an authored tag before they can be
    part of a commitment.

WHY A DIRTY TREE IS REFUSED
    The draft pins a commit. If the file on disk differs from that commit,
    the draft describes text nobody can retrieve at the revision it names,
    and the digest binds something that was never committed.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from . import spec_closure

FEATURE_FILE = "acceptance.feature"

#: What a person has to supply before the draft is a proposal anyone can act
#: on. Both are decisions or judgements, not facts readable from the tree —
#: which is why the draft is emitted invalid rather than filled with
#: plausible placeholders.
STILL_REQUIRED = (
    "opportunity: the opportunity_ref this commitment serves, and its outcome. "
    "It lives in the decision service and is a decision, not a fact about the "
    "repository.",
    "selected_behavior: confirm this is the scope being committed to. Everything "
    "authored was included; that is a starting point, not a selection.",
    "constraints and exclusions: what is deliberately out of scope. An absent "
    "exclusion list reads as 'nothing was excluded', which is rarely true.",
    "a decision: nothing here is an approval, and submitting this draft is not one either.",
)


class NotInspectable(RuntimeError):
    """The package cannot be converted, and why."""


@dataclass
class Report:
    draft: dict | None = None
    needs_identity: list = field(default_factory=list)
    still_required: list = field(default_factory=list)


def _run(target: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(target), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as failed:
        raise NotInspectable(f"git {' '.join(args)} failed: {failed}") from failed


def _name(node: dict) -> str:
    return (node.get("name") or "").strip() or "(unnamed)"


def inspect(target: Path, feature_key: str, *, source_key: str) -> Report:
    """Read one package and draft what could be committed from it."""
    target = Path(target)
    path = target / "features" / feature_key / FEATURE_FILE
    if not path.is_file():
        raise NotInspectable(f"no {FEATURE_FILE} at features/{feature_key}/")

    relative = path.relative_to(target).as_posix()
    dirty = _run(target, "status", "--porcelain", "--", relative)
    if dirty:
        raise NotInspectable(
            f"{relative} has uncommitted changes. The draft pins a commit, and a "
            "baseline that names a revision the text was never in binds something "
            "nobody can retrieve."
        )
    revision = _run(target, "rev-parse", "HEAD")

    doc = spec_closure.parse_feature(path.read_text(encoding="utf-8"))

    selected, needs_identity = [], []
    for kind, node, _rule in spec_closure._walk(doc):
        authored = [
            (found_kind, slug)
            for found_kind, slug in spec_closure._authored(node.get("tags") or [])
            if found_kind == kind
        ]
        if not authored:
            needs_identity.append(
                f"{kind}: {_name(node)!r} has no authored identity. Add "
                f"@{kind}:<slug> to the source and re-run; a derived identifier "
                f"changes when the name does and a baseline refuses it."
            )
            continue
        for _found_kind, slug in authored:
            selected.append(
                {
                    "ref": f"{source_key}/{feature_key}#{kind}:{slug}",
                    "kind": kind,
                    "id_source": "tag",
                }
            )

    report = Report(needs_identity=needs_identity)
    if not selected:
        # A draft here would be the most misleading possible output: nothing
        # in this package can bind an approval.
        return report

    report.draft = {
        "version": 1,
        "commitment_key": feature_key,
        "sources": [
            {
                "source_key": source_key,
                "repository": _origin(target),
                "revision": revision,
                "path": "features",
                "kind": "repository",
            }
        ],
        "selected_behavior": selected,
    }
    report.still_required = list(STILL_REQUIRED)
    return report


def _origin(target: Path) -> str:
    try:
        return _run(target, "remote", "get-url", "origin")
    except NotInspectable:
        # A local-only checkout is a normal state, and guessing a URL would
        # put a wrong one into something an approver reads.
        return ""


def main(argv: list | None = None) -> int:
    import argparse
    import json
    import sys

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", required=True, type=Path)
    ap.add_argument("--feature", required=True)
    ap.add_argument(
        "--source-key", required=True, help="the source_key every reference is qualified with"
    )
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)

    try:
        report = inspect(a.target.resolve(), a.feature, source_key=a.source_key)
    except NotInspectable as refused:
        print(f"  {refused}", file=sys.stderr)
        return 2

    for flag in report.needs_identity:
        print(f"  NEEDS IDENTITY  {flag}")

    if report.draft is None:
        print(
            "  nothing in this package can bind an approval yet; no draft written", file=sys.stderr
        )
        return 1

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report.draft, indent=2) + "\n", encoding="utf-8")
    print(f"  {len(report.draft['selected_behavior'])} authored reference(s) -> {a.out}")
    print("  This draft is NOT an approval and does not validate yet. Still required:")
    for item in report.still_required:
        print(f"    - {item}")
    return 0


def register(subparsers) -> None:
    """Register the `inspect-package` subcommand."""
    from . import paths

    p = subparsers.add_parser(
        "inspect-package",
        help="Draft a behavioral baseline from an existing feature package",
    )
    p.add_argument("--target", required=True, type=Path, help=paths.TARGET_HELP)
    p.add_argument("--feature", required=True, help="the feature key under features/")
    p.add_argument(
        "--source-key", required=True, help="the source_key every reference is qualified with"
    )
    p.add_argument("--out", required=True, type=Path)
    p.set_defaults(func=lambda args: _dispatch(args))


def _dispatch(args) -> None:
    import sys

    sys.exit(
        main(
            [
                "--target",
                str(args.target),
                "--feature",
                args.feature,
                "--source-key",
                args.source_key,
                "--out",
                str(args.out),
            ]
        )
    )


if __name__ == "__main__":
    import sys

    sys.exit(main())
