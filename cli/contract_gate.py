#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Every commitment in a repository, checked the same way — increment 13A.

The gate that shipped with increment 11's placement asks one question about
one hand-configured baseline. At a protected boundary that is three problems:

- **It checks one path.** A repository with four commitments gates one of
  them, and which one depends on a template variable somebody edited once.
- **It never checks drift.** Authority is about the approval. The working
  tree can say something else entirely and the answer is still "authorized".
- **Each provider hand-wires its own shell.** The acceptance criterion is
  that GitHub and Azure produce *equivalent outcomes for the same cases*,
  and equivalence between two copies of a shell snippet is a hope.

So the checking lives here, and both providers call it. Discovery follows
`commitments/<key>/baseline.json` — the layout `behavioral_baseline.schema
.json` already defines — which also settles the case the plan calls out
directly: a code change whose contract files were untouched is still checked
against every commitment in the repository, because a pull request author's
declaration that a change is internal is not evidence.

**The two questions stay separate.** Drift is local and deterministic;
authority is remote and current. Both are necessary and neither substitutes
for the other, so both are reported for every package rather than
short-circuiting on the first failure — one fix-and-rerun cycle instead of
four.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from . import baseline_check
from .authority_check import Outcome, PdgUnreachable, verify

COMMITMENTS_DIR = "commitments"
BASELINE_FILE = "baseline.json"


@dataclass
class PackageResult:
    """One commitment package, and what each check said about it.

    `authorized` is deliberately three-valued and not a bool: True, False,
    and None for *could not determine*. Collapsing None into False would
    report an outage as a withdrawn approval; collapsing it into True would
    be worse.
    """

    key: str
    baseline_path: Path
    drift: baseline_check.Report | None = None
    authorized: bool | None = None
    authority_detail: str = ""
    error: str | None = None

    @property
    def ok(self) -> bool:
        if self.error is not None:
            return False
        if self.drift is None or not self.drift.ok:
            return False
        return self.authorized is True


@dataclass
class GateReport:
    packages: list[PackageResult] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems and all(p.ok for p in self.packages)


def discover(target: Path) -> list[Path]:
    """Every `commitments/<key>/baseline.json`, in a stable order.

    Sorted because a gate whose output reorders between runs makes a diff of
    two runs useless, which is exactly how a new failure hides among
    reordered lines.
    """
    root = Path(target) / COMMITMENTS_DIR
    if not root.is_dir():
        return []
    return sorted(
        (package / BASELINE_FILE
         for package in root.iterdir()
         if package.is_dir() and (package / BASELINE_FILE).is_file()),
        key=lambda p: p.parent.name,
    )


def _load(path: Path) -> tuple[dict | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as unreadable:
        return None, f"could not read {path.name}: {unreadable}"
    except ValueError as malformed:
        return None, f"{path.name} is not valid JSON: {malformed}"
    if not isinstance(data, dict):
        return None, f"{path.name} does not contain a baseline object"
    return data, None


def _roots_for(baseline: dict, target: Path) -> dict[str, Path]:
    """Where each declared source is checked out.

    A single-source baseline is the repository being gated. Anything more
    needs a checkout per source and the gate cannot invent one — those come
    back as refusals from `baseline_check`, which is the honest answer: not
    "no differences", but "I could not look".
    """
    sources = baseline.get("sources")
    if isinstance(sources, list) and len(sources) == 1:
        key = sources[0].get("source_key") if isinstance(sources[0], dict) else None
        if isinstance(key, str) and key:
            return {key: target}
    return {}


def run(
    target: Path,
    *,
    fetch: Callable[[str], dict],
    require_commitments: bool = False,
    roots: dict[str, Path] | None = None,
) -> GateReport:
    """Check every commitment package in `target`.

    `fetch` is the same bounded client seam `authority_check.verify` uses, so
    the interesting cases — a withdrawn approval, an outage, a replayed
    revision — are testable without a server.
    """
    target = Path(target)
    report = GateReport()
    baselines = discover(target)

    if not baselines:
        if require_commitments:
            # "Nothing to check" passing is the failure this gate exists to
            # prevent: green because it was never configured is
            # indistinguishable from green because the behavior was approved.
            report.problems.append(
                f"no commitment packages found under {COMMITMENTS_DIR}/, but this "
                "project is configured to verify against a PDG"
            )
        return report

    for path in baselines:
        result = PackageResult(key=path.parent.name, baseline_path=path)
        report.packages.append(result)

        baseline, error = _load(path)
        if baseline is None:
            result.error = error
            # No baseline means no digest, so any answer about authority
            # would be about a commitment id and nothing else. Claiming it
            # authorized is the forgery path increment 11 closed.
            result.authority_detail = "not checked: the baseline could not be read"
            continue

        result.drift = baseline_check.check(baseline, roots or _roots_for(baseline, target))

        commitment_id = baseline.get("commitment_key")
        outcome = verify(baseline, commitment_id=commitment_id, fetch=fetch)
        result.authority_detail = outcome.detail
        if outcome.outcome is Outcome.AUTHORIZED:
            result.authorized = True
        elif outcome.outcome is Outcome.NOT_AUTHORIZED:
            result.authorized = False
        else:
            result.authorized = None

    return report


def exit_status(report: GateReport, *, enforced: bool) -> int:
    """Enforcement is a property of the call site, not of configuration.

    Advisory at the start of work informs; enforced at merge blocks. The
    difference is which caller ran it — never a field a pull request can
    flip, which would be a gate disabled by the thing it gates.
    """
    if not enforced:
        return 0
    return 0 if report.ok else 1


__all__ = [
    "GateReport",
    "PackageResult",
    "PdgUnreachable",
    "discover",
    "exit_status",
    "run",
]
