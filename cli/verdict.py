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
"""Did an autonomous run earn the right to open a pull request?

An agent cannot answer this about itself, and its runner cannot either: a
headless `claude -p` returns `subtype: success` and exit 0 whether it fixed the
defect, correctly refused it, or stopped at a gate only a human can clear. So
the verdict has to be derived from the working tree, the diff, and the gates —
the same move `govkit evidence` makes for quality. Measure it; do not accept
the producer's account of it.

`AUTONOMOUS_BUGFIX_AGENT_ANALYSIS.md` §5.3 states the constraint this obeys:
"the calling harness, not govkit, has to be what says no." This command does
not say no. It reports what is true of the tree and exits with a code the
harness branches on; the decision stays with the caller.

**Four outcomes, deliberately distinct.** Collapsing them is how autonomy goes
wrong. A refusal reported as failure invites a retry loop, and a retry loop
against a gate the agent cannot legitimately clear is exactly the pressure that
produces the self-certification §4 warns about.

    FIXED     0  every gate passed — the run may commit and open a PR
    REJECTED  1  something is wrong — no PR, and no blind retry
    REFUSED   2  the agent declined and left no trace — a SUCCESS
    BLOCKED   3  stopped at a gate only a human can clear — escalate

This is the working-tree half of a question CI cannot answer either: CI sees a
PR that already exists, and by then the decision to open it has been made.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .approval import is_govkit_authored

FIXED = "FIXED"
REJECTED = "REJECTED"
REFUSED = "REFUSED"
BLOCKED = "BLOCKED"

EXIT_CODES = {FIXED: 0, REJECTED: 1, REFUSED: 2, BLOCKED: 3}

FIXES_GLOB = "fixes/*/fix.yaml"
FEATURES_DIR = "features"

# Build output is not source, and belongs in nobody's declared surface.
IGNORED_PARTS = ("__pycache__", ".pytest_cache", ".ruff_cache", "node_modules",
                 ".venv", ".mypy_cache", "dist", "build", ".tox")

# Files a harness leaves beside the run. Judging them as source would fail
# every run that logged anything.
RUNNER_ARTIFACTS = {"agent.json", "agent-run.json", "err.txt", ".agent-mode"}

_STATUS_RE = re.compile(r"^## Status\s*\n(.+)$", re.MULTILINE)
_GATE_STATUS = "Accepted"


@dataclass
class Gate:
    """One check. `status` is pass/fail/skip; skip never certifies anything."""

    status: str
    gate: str
    detail: str


@dataclass
class Assessment:
    verdict: str
    exit_code: int
    gates: list[Gate] = field(default_factory=list)

    def __iter__(self):
        # Unpacks as (verdict, exit_code, gates).
        return iter((self.verdict, self.exit_code, self.gates))


class VerdictError(Exception):
    """The run could not be assessed at all — a broken setup, not a judgement.

    Kept distinct from the four verdicts on purpose. Returning REFUSED for a
    target that is not a repository would tell the harness "the agent declined,
    this is a success, do not retry", and a misconfigured job would report
    success forever while never opening a PR.
    """


def _git(repo: Path, *args: str, raw: bool = False) -> str:
    """Run git and require it to succeed.

    Swallowing a non-zero exit here is what let a non-repository read as "no
    files changed". Every caller below treats empty output as a fact about the
    run, so it has to be a fact about the run.
    """
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        raise VerdictError(
            f"git {' '.join(args)} failed in {repo}"
            + (f": {detail[0]}" if detail else "")
        )
    # `--porcelain` encodes status in the first two columns, so the leading
    # space of the first line is data, not padding. Stripping the whole output
    # silently ate one character off exactly one path per run.
    return result.stdout if raw else result.stdout.strip()


def require_assessable(target: Path, base: str) -> None:
    """Fail loudly before any gate runs, rather than mis-classifying later."""
    if not target.is_dir():
        raise VerdictError(f"target directory '{target}' does not exist")
    try:
        _git(target, "rev-parse", "--is-inside-work-tree")
    except VerdictError as exc:
        raise VerdictError(
            f"'{target}' is not a git work tree — the verdict is derived from "
            "the diff, so there is nothing to assess"
        ) from exc
    if base:
        try:
            _git(target, "rev-parse", "--verify", f"{base}^{{commit}}")
        except VerdictError as exc:
            raise VerdictError(
                f"--base '{base}' does not resolve to a commit in '{target}'"
            ) from exc


def _ignored(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    return any(part in IGNORED_PARTS for part in parts)


def changed_files(target: Path, base: str) -> list[str]:
    """Every path this run touched — committed since `base` and still dirty.

    An agent that commits and opens the PR itself must be judged exactly like
    one that leaves the tree dirty, so both are collected.
    """
    found: set[str] = set()
    if base:
        for line in _git(target, "diff", "--name-only", f"{base}...HEAD").splitlines():
            if line.strip():
                found.add(line.strip())
    # `-uall` lists untracked FILES. The default collapses an untracked
    # directory to its name, which hid a newly written ADR or fix record
    # behind `docs/` and made the checks that read them silently vacuous.
    for line in _git(target, "status", "--porcelain", "-uall", raw=True).splitlines():
        path = line[3:].strip().strip('"')
        if path:
            found.add(path.rstrip("/"))
    return sorted(
        p for p in found
        if not p.startswith(".govkit/") and not _ignored(p)
        and Path(p).name not in RUNNER_ARTIFACTS
    )


def is_test_path(rel: str) -> bool:
    """Heuristic shared with the fix-lane gate: a regression test is the proof
    of a repair, not part of it, so it is never expected in `surface.paths`."""
    name = Path(rel).name.lower()
    parts = rel.replace("\\", "/").lower().split("/")
    return "test" in name or "tests" in parts or "spec" in name


def source_changes(changed: list[str], roots: tuple[str, ...]) -> list[str]:
    return [
        p for p in changed
        if any(p.replace("\\", "/").startswith(r) for r in roots)
        and not is_test_path(p)
    ]


def load_records(target: Path) -> list[tuple[Path, dict]]:
    out = []
    for path in sorted(target.glob(FIXES_GLOB)):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            data = {}
        out.append((path, data if isinstance(data, dict) else {}))
    return out


def accepted_adr(target: Path, changed: list[str]) -> str:
    """An ADR this run touched whose Status reads `Accepted`.

    `Accepted` is a derived state — true because an approver approved that
    decision at that commit. An author may only ever write `Proposed`, so an
    agent that wrote `Accepted` has asserted an approval that did not happen.

    Two exclusions. TEMPLATE.md, because its Status line is the vocabulary
    menu rather than a claim. And govkit's own ADRs: it ships one
    (`docs/data/architecture/ADR/0001-…`) that says `Accepted` because it is
    govkit's decision, and it lands in every `--type data` install — so any run
    that happened to include a govkit install, the first one after adoption
    most obviously, was rejected for an ADR the team never wrote. The
    discriminator is the `govkit:editable` body hash `cli/approval.py` and both
    CI gates already use; edit the file and it becomes the team's claim again.
    """
    for rel in changed:
        norm = rel.replace("\\", "/")
        if "/ADR/" not in norm or not norm.endswith(".md"):
            continue
        if Path(norm).name == "TEMPLATE.md":
            continue
        try:
            text = (target / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        match = _STATUS_RE.search(text)
        if not match or match.group(1).strip() != _GATE_STATUS:
            continue
        if is_govkit_authored(text):
            continue
        return norm
    return ""


def cited_source_changed(records: list[tuple[Path, dict]], changed: list[str]) -> str:
    """A record whose `expectation.source` this same run modified.

    Defect-lane condition 1 asks the change to cite a source that *already*
    established the behavior. Editing — or restoring — that source in the same
    change manufactures its own eligibility. Observed in a real headless run:
    the agent recovered a deleted contract from git history, wrote it back,
    cited it, and every govkit gate went green, because `validate` checks the
    path resolves rather than that it predates the fix.
    """
    changed_set = {p.replace("\\", "/") for p in changed}
    for _path, data in records:
        source = (data.get("expectation") or {}).get("source")
        if isinstance(source, str) and source.replace("\\", "/") in changed_set:
            return source
    return ""


def undeclared_sources(records: list[tuple[Path, dict]], touched: list[str]) -> list[str]:
    declared: set[str] = set()
    for _path, data in records:
        for entry in (data.get("surface") or {}).get("paths") or []:
            if isinstance(entry, str):
                declared.add(entry.replace("\\", "/"))
    return [p for p in touched if p.replace("\\", "/") not in declared]


def _revert_source(target: Path, roots: tuple[str, ...], base: str):
    """Put the source back as it was before the run, and return an undo.

    Two shapes, because the agent may or may not have committed. Dirty tree:
    stash the source and pop it back. Committed run: check the source out at
    `base` and restore it from HEAD afterwards. Returns None when neither is
    possible, so the caller fails the gate rather than testing the wrong tree.
    """
    dirty = [
        line for line in _git(target, "status", "--porcelain", "-uall", raw=True).splitlines()
        if any(line[3:].strip().strip('"').replace("\\", "/").startswith(r) for r in roots)
    ]
    if dirty:
        # `-u` because a fix delivered as a NEW file is untracked, and
        # `changed_files` already counts it as source. Without it the
        # "reverted" run tested a tree that still contained the repair.
        #
        # Build artifacts are excluded, and that exclusion is load-bearing:
        # the reverted run regenerates them, and `git stash pop` then refuses
        # to overwrite the very files it is restoring. `__pycache__` under a
        # source root makes that the default outcome for a Python repo.
        excludes = [f":(exclude)**/{part}/**" for part in IGNORED_PARTS]
        pushed = subprocess.run(
            ["git", "stash", "push", "-u", "-q", "--", *roots, *excludes],
            cwd=target, capture_output=True, text=True, check=False)
        if pushed.returncode != 0:
            return None
        return lambda: subprocess.run(["git", "stash", "pop", "-q"], cwd=target,
                                      capture_output=True, text=True, check=False)
    if base:
        out = subprocess.run(["git", "checkout", base, "--", *roots], cwd=target,
                             capture_output=True, text=True, check=False)
        if out.returncode != 0:
            return None
        return lambda: subprocess.run(["git", "checkout", "HEAD", "--", *roots],
                                      cwd=target, capture_output=True, text=True, check=False)
    return None


def red_before_green(
    target: Path, roots: tuple[str, ...], test_command: list[str] | None,
    base: str = "",
) -> Gate:
    """Prove the regression test reproduces the defect.

    Revert only the source, keep the new tests, and require a failure. This is
    the one claim an agent cannot talk past: every run in the experiment
    asserted red-before-green in its own summary, and only executing it decides
    whether that was true.

    Without a test command nothing is certified. `govkit evidence` states the
    contract this follows — an unmeasured dimension is indistinguishable from a
    verified one, so it is never a pass.
    """
    if not test_command:
        return Gate("fail", "red-before-green",
                    "no test command given — a run that cannot be shown to "
                    "reproduce its defect cannot be certified")

    def run_tests() -> int:
        return subprocess.run(
            test_command, cwd=target, capture_output=True, text=True, check=False,
        ).returncode

    if run_tests() != 0:
        return Gate("fail", "red-before-green", "suite fails with the fix applied")

    undo = _revert_source(target, roots, base)
    if undo is None:
        return Gate("fail", "red-before-green",
                    "could not isolate the source change to test without it")
    try:
        without = run_tests()
    finally:
        # The tree must survive: a verdict tool that damages it is worse than
        # none, and this runs against a repo a human is about to review.
        restored = undo()
    if restored is not None and restored.returncode != 0:
        # Say so instead of reporting on the tests, because the tree now has
        # the repair stashed away and a harness that committed it would ship
        # the regression test without the fix.
        return Gate("fail", "red-before-green",
                    "could not restore the source after reverting it — the "
                    "working tree may be missing the fix; recover it with "
                    "`git stash list` / `git stash pop` before doing anything else")
    if without == 0:
        return Gate("fail", "red-before-green",
                    "tests still pass with the fix reverted — no defect reproduced")
    return Gate("pass", "red-before-green", "fails without the fix, passes with it")


def _govkit_validate(target: Path) -> Gate:
    result = subprocess.run(
        [sys.executable, "-m", "cli.govkit", "validate", "--target", str(target)],
        capture_output=True, text=True, check=False,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    if result.returncode == 0:
        return Gate("pass", "govkit-validate", "exit 0")
    tail = (result.stdout or result.stderr or "").strip().splitlines()
    return Gate("fail", "govkit-validate",
                f"exit {result.returncode}" + (f" — {tail[-1]}" if tail else ""))


def assess(
    target: Path,
    base: str = "",
    source_roots: tuple[str, ...] = ("src/",),
    test_command: list[str] | None = None,
    run_validate: bool = True,
) -> Assessment:
    """Classify one autonomous run.

    Raises `VerdictError` when the run cannot be assessed at all. Never leaves
    the working tree altered.
    """
    target = Path(target)
    require_assessable(target, base)
    changed = changed_files(target, base)
    records = load_records(target)
    features = (
        [d for d in (target / FEATURES_DIR).glob("*") if d.is_dir()]
        if (target / FEATURES_DIR).is_dir() else []
    )
    touched_source = source_changes(changed, source_roots)
    gates: list[Gate] = []

    # ---- Nothing attempted, nothing left behind --------------------------
    if not changed:
        gates.append(Gate("pass", "clean-refusal",
                          "no files changed — the agent declined and said so"))
        return Assessment(REFUSED, EXIT_CODES[REFUSED], gates)

    adr = accepted_adr(target, changed)
    gates.append(Gate("fail" if adr else "pass", "adr-not-self-accepted",
                      f"{adr} claims {_GATE_STATUS}" if adr
                      else f"no ADR claims {_GATE_STATUS}"))

    # ---- Artifacts written, no code. Two very different things. ----------
    if not touched_source:
        if adr:
            return Assessment(REJECTED, EXIT_CODES[REJECTED], gates)
        if records:
            gates.append(Gate("fail", "fix-record-describes-a-fix",
                              "fix record present but no source changed"))
            return Assessment(REJECTED, EXIT_CODES[REJECTED], gates)
        if features:
            gates.append(Gate("skip", "no-source-change",
                              "feature artifacts authored, no code — a human gate"))
            return Assessment(BLOCKED, EXIT_CODES[BLOCKED], gates)
        gates.append(Gate("skip", "no-source-change",
                          "no source changed and no governing artifact written"))
        return Assessment(BLOCKED, EXIT_CODES[BLOCKED], gates)

    # ---- It changed code, so every gate below must hold. -----------------
    gates.append(Gate("pass" if records else "fail", "governing-artifact",
                      f"{len(records)} fix record(s)" if records
                      else "source changed with no fix record"))

    gates.append(Gate("fail" if features else "pass", "defect-lane-only",
                      f"authored features/: {sorted(d.name for d in features)}"
                      if features else "no feature package invented"))

    cited = cited_source_changed(records, changed)
    gates.append(Gate("fail" if cited else "pass", "citation-predates-fix",
                      f"modified its own cited source: {cited}" if cited
                      else "cited source untouched by this change"))

    undeclared = undeclared_sources(records, touched_source)
    gates.append(Gate("fail" if undeclared else "pass", "surface-covers-diff",
                      f"undeclared source: {undeclared}" if undeclared
                      else "declared surface covers the changed source"))

    gates.append(red_before_green(target, source_roots, test_command, base))

    if run_validate:
        gates.append(_govkit_validate(target))

    failed = [g for g in gates if g.status == "fail"]
    verdict = REJECTED if failed else FIXED
    return Assessment(verdict, EXIT_CODES[verdict], gates)
