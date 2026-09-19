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
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from . import baseline_check
from .authority_check import Outcome, PdgUnreachable, verify

COMMITMENTS_DIR = "commitments"
BASELINE_FILE = "baseline.json"
#: The id the decision service assigned, recorded beside the baseline rather
#: than inside it. Inside, it would change the digest — and the digest is what
#: the approval binds, so recording the id an approval returned would break
#: the binding to the baseline that id was issued for.
#:
#: This is increment 11's design, finally built: "the baseline names no
#: decision ... a local pointer names the commitment and the PDG adjudicates
#: it". Until a live run against discovery-engine on 2026-09-19, the gate used
#: `baseline.commitment_key` as the id, and the engine assigns its own
#: (`cmt-<uuid>`) at approval — so every real commitment 404'd and reported as
#: NOT AUTHORIZED. The gate would have failed every approved change.
POINTER_FILE = "commitment.json"


class NoSuchCommitment(RuntimeError):
    """The PDG looked and found nothing.

    Deliberately **not** a `PdgUnreachable`. An earlier version subclassed it
    so a caller that forgot to translate would degrade safely, and the effect
    was to lose the distinction increment 11 exists to make: a 404 is a
    definite answer about this commitment, and laundering it into "the graph
    could not be reached" turns an absence into a maybe.
    """

    def __init__(self, commitment_id: str) -> None:
        super().__init__(f"the PDG has no commitment {commitment_id!r}")
        self.commitment_id = commitment_id


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
        (
            package / BASELINE_FILE
            for package in root.iterdir()
            if package.is_dir() and (package / BASELINE_FILE).is_file()
        ),
        key=lambda p: p.parent.name,
    )


class BaseRefUnreadable(RuntimeError):
    """The base revision could not be listed, so removals cannot be judged."""


def discover_at(target: Path, ref: str) -> list[str]:
    """The commitment keys that exist at `ref`, read from git rather than disk.

    Needed because `discover` reads the tree the pull request *proposes*, and
    that is exactly what the pull request controls. Deleting
    `commitments/foo/` removes foo from the gate entirely, and while any
    other package survives, a check for "at least one commitment" is
    satisfied. Enforcement you can switch off by deleting a file is not
    enforcement.
    """
    try:
        listing = subprocess.run(
            [
                "git",
                "-C",
                str(target),
                "ls-tree",
                "-r",
                "--name-only",
                ref,
                "--",
                f"{COMMITMENTS_DIR}/",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as unreadable:
        # Not a repository, or a ref this checkout does not have — a shallow
        # clone, a renamed branch, a typo in the pipeline. Returning "nothing
        # was removed" would disable the one check that stops a deletion
        # switching off enforcement, and it would do it silently, with a
        # green tick. So it is raised and the caller fails closed.
        raise BaseRefUnreadable(
            f"could not list {COMMITMENTS_DIR}/ at {ref!r}: {unreadable}"
        ) from unreadable
    keys = set()
    for line in listing.splitlines():
        parts = line.strip().split("/")
        if len(parts) == 3 and parts[0] == COMMITMENTS_DIR and parts[2] == BASELINE_FILE:
            keys.add(parts[1])
    return sorted(keys)


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


def _pointer(package: Path) -> tuple[str | None, str | None]:
    """The commitment id recorded for this package, or why it cannot be read.

    Absent is not an error: a baseline with no pointer is a well-formed
    proposal nobody has approved, and `verify` already reports that as a
    definite *not authorized*. Unreadable is different — the package's state
    cannot be established — and collapsing the two would report a verdict
    the gate has not earned.
    """
    path = package / POINTER_FILE
    if not path.is_file():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as unreadable:
        return None, f"could not read {POINTER_FILE}: {unreadable}"
    except ValueError as malformed:
        return None, f"{POINTER_FILE} is not valid JSON: {malformed}"
    if not isinstance(data, dict):
        return None, f"{POINTER_FILE} does not contain an object"
    commitment_id = data.get("commitment_id")
    if not isinstance(commitment_id, str) or not commitment_id:
        return None, f"{POINTER_FILE} records no commitment_id"
    return commitment_id, None


def _roots_for(baseline: dict, target: Path, supplied: dict[str, Path]) -> dict[str, Path]:
    """Where each declared source is checked out.

    A single-source baseline is the repository being gated, so the common
    case needs no argument. Anything more needs a checkout per source, and
    those are supplied by the caller — the gate cannot invent one, and a
    source it cannot reach comes back as a refusal from `baseline_check`,
    which is the honest answer: not "no differences", but "I could not look".

    Supplying checkouts is what makes a cross-repository contract checkable
    at all. Without it every schema-valid multi-source baseline failed an
    enforced gate for want of an argument, which is the gate rejecting valid
    contracts rather than catching bad ones.
    """
    sources = baseline.get("sources")
    if not isinstance(sources, list) or not sources:
        return {}
    keys = [
        source.get("source_key")
        for source in sources
        if isinstance(source, dict) and isinstance(source.get("source_key"), str)
    ]
    roots = {key: supplied[key] for key in keys if key in supplied}
    if len(keys) == 1 and keys[0] not in roots:
        roots[keys[0]] = target
    return roots


def run(
    target: Path,
    *,
    fetch: Callable[[str], dict],
    require_commitments: bool = False,
    roots: dict[str, Path] | None = None,
    base_ref: str | None = None,
) -> GateReport:
    """Check every commitment package in `target`.

    `fetch` is the same bounded client seam `authority_check.verify` uses, so
    the interesting cases — a withdrawn approval, an outage, a replayed
    revision — are testable without a server.
    """
    target = Path(target)
    supplied = roots or {}
    report = GateReport()
    baselines = discover(target)
    present = {path.parent.name for path in baselines}

    if base_ref:
        _check_removals(target, base_ref, present, fetch, report)

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

        # Contained per package. `_load` accepts any JSON object and the
        # checks below assume shapes under it, so one structurally invalid
        # baseline used to raise out of the whole run — every later package
        # then went unchecked *and unreported*, which at a gate is the worst
        # of both: no answer, and no sign that an answer is missing.
        try:
            result.drift = baseline_check.check(baseline, _roots_for(baseline, target, supplied))
        except Exception as broken:  # noqa: BLE001 - one bad file must not end the run
            result.error = f"the baseline could not be checked: {broken}"
            result.authority_detail = "not checked: the baseline could not be checked"
            continue

        commitment_id, pointer_error = _pointer(path.parent)
        if pointer_error:
            result.error = pointer_error
            result.authority_detail = f"not checked: {pointer_error}"
            continue

        try:
            outcome = verify(baseline, commitment_id=commitment_id, fetch=fetch)
        except NoSuchCommitment as absent:
            result.authorized = False
            result.authority_detail = str(absent)
            continue
        except Exception as broken:  # noqa: BLE001 - same reasoning as above
            result.authorized = None
            result.authority_detail = f"authority could not be established: {broken}"
            continue

        result.authority_detail = outcome.detail
        if outcome.outcome is Outcome.AUTHORIZED:
            result.authorized = True
        elif outcome.outcome is Outcome.NOT_AUTHORIZED:
            result.authorized = False
        else:
            result.authorized = None

    return report


def _check_removals(
    target: Path,
    base_ref: str,
    present: set[str],
    fetch: Callable[[str], dict],
    report: GateReport,
) -> None:
    """Refuse a deletion the PDG has not been told about.

    Retirement has a designed path — invalidate the commitment in the graph,
    and then the file may go. Refusing every removal would make the
    repository a place commitments accumulate forever; allowing every removal
    makes the gate optional. So the graph decides, and an outage during a
    deletion fails closed, because that is the moment guessing costs most.
    """
    try:
        at_base = discover_at(target, base_ref)
    except BaseRefUnreadable as unreadable:
        report.problems.append(
            f"{unreadable}. The gate cannot tell whether a commitment was "
            f"removed, so it refuses rather than assuming none was."
        )
        return

    for key in at_base:
        if key in present:
            continue
        commitment_id, pointer_error = _pointer_at(target, base_ref, key)
        if pointer_error:
            report.problems.append(
                f"{key} was removed from {COMMITMENTS_DIR}/ and its recorded "
                f"commitment id could not be read at {base_ref!r}: {pointer_error}"
            )
            continue
        if commitment_id is None:
            # Nothing ever named a decision for it, so nothing is being
            # removed from enforcement.
            continue
        try:
            status = fetch(commitment_id)
        except NoSuchCommitment:
            # The graph never knew about it either. Nothing is being removed
            # from enforcement that was ever under it.
            continue
        except Exception as unreachable:  # noqa: BLE001 - fail closed
            report.problems.append(
                f"{key} was removed from {COMMITMENTS_DIR}/ and the PDG could not be "
                f"asked whether it still authorizes work: {unreachable}"
            )
            continue
        if status.get("authorizes_work") is not False:
            report.problems.append(
                f"{key} was removed from {COMMITMENTS_DIR}/ but still authorizes work. "
                "Invalidate the commitment in the PDG first; deleting the file "
                "removes it from this gate without removing the commitment."
            )


def _pointer_at(target: Path, ref: str, key: str) -> tuple[str | None, str | None]:
    """The pointer as it stood at `ref`, since the package is gone from disk."""
    try:
        # Bytes, not text. Asked for decoded output, a blob that is not UTF-8
        # raises inside subprocess itself — before any of the handling below
        # — and took the whole run down during the removal check, which is
        # the one path where a crash and a pass are hard to tell apart.
        blob = subprocess.run(
            ["git", "-C", str(target), "show",
             f"{ref}:{COMMITMENTS_DIR}/{key}/{POINTER_FILE}"],
            check=True, capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None, None
    try:
        data = json.loads(blob.decode("utf-8"))
    except UnicodeDecodeError as undecodable:
        return None, f"{POINTER_FILE} is not valid UTF-8: {undecodable}"
    except ValueError as malformed:
        return None, f"{POINTER_FILE} is not valid JSON: {malformed}"
    if not isinstance(data, dict):
        return None, f"{POINTER_FILE} does not contain an object"
    commitment_id = data.get("commitment_id")
    if not isinstance(commitment_id, str) or not commitment_id:
        return None, f"{POINTER_FILE} records no commitment_id"
    return commitment_id, None


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
    "BaseRefUnreadable",
    "GateReport",
    "NoSuchCommitment",
    "POINTER_FILE",
    "PackageResult",
    "PdgUnreachable",
    "discover",
    "discover_at",
    "exit_status",
    "run",
]
