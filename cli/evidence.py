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
"""Measured evidence — read what CI produced, and report what it did not.

See `docs/<area>/evaluation/EVIDENCE_CONTRACT.md`. The rule this implements:

    A producer self-check is advisory. The task owner never commits its own
    final gate.

A FIRST/Virtue score in `plan.md` is written by the agent that did the work, so
it is a forecast. This module reports only what an executed tool observed.

`INCONCLUSIVE` is the load-bearing outcome. An unmeasured dimension that reports
green is indistinguishable from a verified one, which is how a fabricated score
survives review — so every dimension is reported every run, and the ones without
evidence say so.
"""

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# The rubrics' own dimensions — 5 FIRST + 7 Virtues. A test pins these against
# docs/backend/evaluation/*_SCORING_RUBRIC.md so this cannot measure something
# govkit never asked for. Accessibility is not a rubric dimension but is gated
# for UI, so it is reported alongside.
FIRST_DIMENSIONS = ("Fast", "Isolated", "Repeatable", "Self-Verifying", "Timely")
VIRTUE_DIMENSIONS = ("Working", "Unique", "Simple", "Clear", "Easy", "Developed", "Brief")
DIMENSIONS = (*FIRST_DIMENSIONS, *VIRTUE_DIMENSIONS, "Accessibility")

# axe impacts that block. The UI rubric bands minor violations at 3 and a single
# critical/serious at 2, so only the latter two are merge blockers.
_BLOCKING_IMPACTS = ("critical", "serious")

_JUNIT_GLOBS = ("junit*.xml", "**/junit*.xml", "**/*junit*.xml", "**/test-results*.xml")
_AXE_GLOBS = ("axe*.json", "**/axe*.json", "**/*axe-results*.json")

# Dimensions with no instrument today. The reason is carried into the report so
# a reader learns what to wire up rather than just seeing a blank.
_NOT_INSTRUMENTED = {
    "Isolated": "no randomised-order or run-alone execution recorded",
    "Repeatable": "no repeated-run flake rate recorded",
    "Self-Verifying": "no assertion-shape analysis recorded",
    "Timely": "no test-versus-source commit ordering recorded",
    "Unique": "no duplication report recorded",
    "Simple": "no complexity or nesting-depth report recorded",
    "Easy": "no boundary-gate result recorded",
    "Developed": "no coverage report recorded",
    "Brief": "no unused-import or dead-code report recorded",
}

# Not an instrumentation gap — a category error. Its measurable proxies
# (identifier length, comment density) reward verbosity over clarity, so it must
# never report PASS. See EVIDENCE_CONTRACT.md.
_JUDGEMENT_ONLY = {
    "Clear": (
        "a matter of judgement, not measurement — scoreable only by an "
        "independent identified evaluator, never by a metric or by the "
        "agent that produced the work"
    ),
}


class Outcome(Enum):
    """From EVALUATION_EVIDENCE_AND_COMPLETION_CONTRACT.md. INCONCLUSIVE is not
    a pass: no evidence, insufficient evidence, or evidence out of scope."""

    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    ERROR = "ERROR"


@dataclass
class Verdict:
    dimension: str
    outcome: Outcome
    detail: str


def _find(target: Path, globs) -> list[Path]:
    seen, found = set(), []
    for pattern in globs:
        for path in sorted(target.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                found.append(path)
    return found


def _read_junit(paths: list[Path]) -> tuple[dict | None, str | None]:
    """Aggregate JUnit XML. Returns (totals, error). Never raises."""
    totals = {"tests": 0, "failures": 0, "errors": 0, "durations": [], "slowest_name": None}
    slowest = -1.0
    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as exc:
            return None, f"{path.name} could not be parsed: {exc}"
        suites = [root] if root.tag == "testsuite" else root.iter("testsuite")
        for suite in suites:
            totals["tests"] += int(suite.get("tests") or 0)
            totals["failures"] += int(suite.get("failures") or 0)
            totals["errors"] += int(suite.get("errors") or 0)
        for case in root.iter("testcase"):
            try:
                seconds = float(case.get("time") or 0.0)
            except ValueError:
                continue
            totals["durations"].append(seconds)
            if seconds > slowest:
                slowest = seconds
                totals["slowest_name"] = case.get("name")
    return totals, None


def _assess_working(totals: dict | None, error: str | None, found: bool) -> Verdict:
    if error:
        return Verdict("Working", Outcome.ERROR, error)
    if not found:
        return Verdict("Working", Outcome.INCONCLUSIVE, "no test-run report found")
    if not totals or totals["tests"] == 0:
        return Verdict(
            "Working", Outcome.INCONCLUSIVE,
            "test-run report contains no tests — an empty analysis, not a clean one",
        )
    broken = totals["failures"] + totals["errors"]
    if broken:
        return Verdict(
            "Working", Outcome.FAIL,
            f"{broken} of {totals['tests']} tests failed or errored",
        )
    return Verdict("Working", Outcome.PASS, f"{totals['tests']} tests passed")


def _assess_fast(
    totals: dict | None, found: bool, max_seconds: float | None,
    slowest_name: str | None,
) -> Verdict:
    """Observed always; judged only against a threshold the team declared.

    JUnit carries per-test durations, so the measurement is free. Turning the
    rubric's 1-5 bands into a pass/fail threshold is a calibration decision,
    and ADR-0001 warns that inventing a rubric nobody has calibrated recreates
    the ceremony this work removes. So govkit reports the number and leaves the
    policy — until a team sets `--fast-max-seconds`, at which point their
    calibration, not govkit's guess, makes it blocking.
    """
    if not found or not totals or not totals["durations"]:
        return Verdict("Fast", Outcome.INCONCLUSIVE, "no per-test durations recorded")
    durations = sorted(totals["durations"])
    slowest = durations[-1]
    if max_seconds is None:
        over_200ms = sum(1 for d in durations if d > 0.2)
        return Verdict(
            "Fast", Outcome.INCONCLUSIVE,
            f"observed: slowest test {slowest:g}s, {over_200ms} of {len(durations)} over 200ms "
            "— set --fast-max-seconds to make this blocking",
        )
    over = [d for d in durations if d > max_seconds]
    if over:
        name = f" (slowest: {slowest_name})" if slowest_name else ""
        return Verdict(
            "Fast", Outcome.FAIL,
            f"{len(over)} of {len(durations)} tests exceed {max_seconds:g}s; "
            f"slowest {slowest:g}s{name}",
        )
    return Verdict(
        "Fast", Outcome.PASS,
        f"all {len(durations)} tests under {max_seconds:g}s (slowest {slowest:g}s)",
    )


def _read_axe(paths: list[Path]) -> tuple[list[dict] | None, str | None]:
    violations = []
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            return None, f"{path.name} could not be parsed: {exc}"
        for result in data if isinstance(data, list) else [data]:
            if isinstance(result, dict):
                violations.extend(v for v in (result.get("violations") or []) if isinstance(v, dict))
    return violations, None


def _assess_accessibility(violations: list[dict] | None, error: str | None, found: bool) -> Verdict:
    if error:
        return Verdict("Accessibility", Outcome.ERROR, error)
    if not found:
        return Verdict("Accessibility", Outcome.INCONCLUSIVE, "no axe report found")
    counts: dict[str, int] = {}
    for violation in violations or []:
        impact = str(violation.get("impact") or "unknown")
        counts[impact] = counts.get(impact, 0) + 1
    blocking = {k: v for k, v in counts.items() if k in _BLOCKING_IMPACTS}
    seen = ", ".join(f"{n} {impact}" for impact, n in sorted(counts.items())) or "none"
    if blocking:
        return Verdict("Accessibility", Outcome.FAIL, f"axe violations: {seen}")
    return Verdict("Accessibility", Outcome.PASS, f"no critical or serious axe violations ({seen})")


def collect_evidence(target: Path, fast_max_seconds: float | None = None) -> list[Verdict]:
    """Report a verdict for every dimension, every run.

    Reporting all of them is the point: a dimension left out of the output is
    indistinguishable from one that passed.
    """
    junit_paths = _find(target, _JUNIT_GLOBS)
    totals, junit_error = _read_junit(junit_paths)
    axe_paths = _find(target, _AXE_GLOBS)
    violations, axe_error = _read_axe(axe_paths)

    measured = {
        "Working": _assess_working(totals, junit_error, bool(junit_paths)),
        "Fast": _assess_fast(
            totals, bool(junit_paths), fast_max_seconds,
            (totals or {}).get("slowest_name"),
        ),
        "Accessibility": _assess_accessibility(violations, axe_error, bool(axe_paths)),
    }
    verdicts = []
    for dimension in DIMENSIONS:
        if dimension in measured:
            verdicts.append(measured[dimension])
        elif dimension in _JUDGEMENT_ONLY:
            verdicts.append(Verdict(dimension, Outcome.INCONCLUSIVE, _JUDGEMENT_ONLY[dimension]))
        else:
            verdicts.append(
                Verdict(dimension, Outcome.INCONCLUSIVE, _NOT_INSTRUMENTED[dimension])
            )
    return verdicts


def summarize(verdicts: list[Verdict]) -> tuple[int, str]:
    """Return (exit_code, summary).

    Fails on a real failure, and on an empty analysis. The second half matters
    as much as the first: `ci/README.md` warns that every boundary tool "reports
    success on an empty analysis, so a misconfigured contract looks exactly like
    a clean repo". A gate that measured nothing has not passed.

    Partial coverage is not a blocker — it reports how much went unmeasured, so
    adoption is possible without pretending the gaps are closed.
    """
    blocking = [v for v in verdicts if v.outcome in (Outcome.FAIL, Outcome.ERROR)]
    measured = [v for v in verdicts if v.outcome in (Outcome.PASS, Outcome.FAIL)]
    unmeasured = [v for v in verdicts if v.outcome is Outcome.INCONCLUSIVE]

    if not measured and not blocking:
        return 1, (
            "The evidence gate analysed nothing — 0 of "
            f"{len(verdicts)} dimensions have evidence.\n"
            "This is a failure, not a pass: an unmeasured dimension is "
            "indistinguishable from a verified one."
        )
    if blocking:
        return 1, (
            f"{len(blocking)} dimension(s) failed; "
            f"{len(measured)} measured, {len(unmeasured)} unmeasured."
        )
    return 0, (
        f"{len(measured)} measured, {len(unmeasured)} unmeasured. "
        "Unmeasured dimensions have not passed — they were not assessed."
    )
