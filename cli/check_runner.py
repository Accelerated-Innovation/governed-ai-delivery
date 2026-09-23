# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Isolated check dispatch, honest aggregation and versioned raw result replay."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from . import version
from .check_models import (
    Check,
    CheckContext,
    CheckOutcome,
    CheckResult,
    CheckSpec,
    Evidence,
    Execution,
    Finding,
    Identity,
    State,
)
from .schema_validation import (
    DocumentError,
    canonical_json,
    content_digest,
    read_document,
    validate_document,
)


class CheckRegistry:
    """Explicit in-process registration; never import check code from a result file."""

    def __init__(self):
        self._checks: dict[str, Check] = {}

    def register(self, identifier: str, check: Check) -> None:
        if identifier in self._checks:
            raise ValueError(f"Duplicate check: {identifier}")
        self._checks[identifier] = check

    def get(self, identifier: str) -> Check | None:
        return self._checks.get(identifier)


def normalize(outcome: CheckOutcome) -> CheckOutcome:
    if (
        not isinstance(outcome, CheckOutcome)
        or not isinstance(outcome.state, State)
        or not isinstance(outcome.execution, Execution)
    ):
        raise ValueError("Invalid check outcome")
    if outcome.state is State.PASS:
        independent = bool(outcome.evidence) and all(
            e.origin in ("local-check", "tool-execution") for e in outcome.evidence
        )
        if outcome.execution is not Execution.EXECUTED or not independent:
            outcome = replace(
                outcome,
                state=State.UNKNOWN,
                summary="Pass is unverified: executed independent evidence is required. "
                + outcome.summary,
            )
    if outcome.execution is Execution.ERROR:
        outcome = replace(outcome, state=State.UNKNOWN)
    elif any(f.severity == "error" for f in outcome.findings):
        outcome = replace(outcome, state=State.FAIL)
    elif outcome.state is State.PASS and any(f.severity == "warning" for f in outcome.findings):
        outcome = replace(outcome, state=State.WARN)
    if not outcome.findings:
        severity = (
            "error"
            if outcome.state is State.FAIL
            else "info"
            if outcome.state is State.PASS
            else "warning"
        )
        outcome = replace(
            outcome,
            findings=(
                Finding(
                    outcome.state.value,
                    severity,
                    "check",
                    outcome.summary,
                    "Review the declared scope and evidence."
                    if outcome.state is State.PASS
                    else "Resolve the finding and rerun the check.",
                    evidence=outcome.evidence,
                ),
            ),
        )
    return outcome


@dataclass(frozen=True)
class CheckReport:
    identity: Identity
    results: tuple[CheckResult, ...]
    govkit_version: str

    @property
    def summary(self) -> dict[str, int]:
        counts = {
            state.value: sum(r.outcome.state is state for r in self.results) for state in State
        }
        counts.update(
            required=sum(r.spec.required for r in self.results),
            required_satisfied=sum(
                r.spec.required and r.outcome.state is State.PASS for r in self.results
            ),
            executed=sum(r.outcome.execution is Execution.EXECUTED for r in self.results),
        )
        return counts

    @property
    def exit_code(self) -> int:
        if not self.results or not any(r.outcome.state is State.PASS for r in self.results):
            return 1
        return int(
            any(
                r.outcome.state is State.FAIL
                or (r.spec.required and r.outcome.state is not State.PASS)
                for r in self.results
            )
        )

    @property
    def state(self) -> State:
        if any(r.outcome.state is State.FAIL for r in self.results):
            return State.FAIL
        if self.exit_code:
            return State.UNKNOWN
        if any(r.outcome.state not in (State.PASS, State.NOT_APPLICABLE) for r in self.results):
            return State.WARN
        return State.PASS

    def to_document(self) -> dict:
        results = []
        for result in self.results:
            spec, outcome = result.spec, result.outcome
            findings = []
            for finding in sorted(
                outcome.findings, key=lambda f: (f.code, f.location or "", f.message)
            ):
                identity = (spec.id, finding.code, finding.location, spec.scope, finding.message)
                findings.append(
                    {
                        **asdict(finding),
                        "id": "finding:" + content_digest(canonical_json(identity).encode()),
                        "check_id": spec.id,
                        "applicability_reason": spec.reason,
                        "source_policy": spec.source_policy,
                        "scope": list(spec.scope),
                    }
                )
            results.append(
                {
                    **asdict(spec),
                    "state": outcome.state.value,
                    "execution": outcome.execution.value,
                    "summary": outcome.summary,
                    "evidence": [asdict(e) for e in outcome.evidence],
                    "findings": findings,
                }
            )
        return json.loads(
            canonical_json(
                {
                    "schema_version": 1,
                    "kind": "check-results",
                    "govkit_version": self.govkit_version,
                    "identity": asdict(self.identity),
                    "results": results,
                    "summary": self.summary,
                    "state": self.state.value,
                    "exit_code": self.exit_code,
                    "limitations": [
                        "Result consistency does not authenticate policy or evidence origin.",
                        "Only the named checks and scopes were assessed; change routing and maintenance assessment are not performed.",
                    ],
                }
            )
        )

    def to_json(self) -> str:
        return canonical_json(self.to_document())


def run_checks(
    context: CheckContext, specifications: tuple[CheckSpec, ...], registry: CheckRegistry
) -> CheckReport:
    """Keep every required check, isolate failures, and leave output to the CLI.

    Execution is deliberately sequential: output guards isolate legacy warnings
    and protocol violations. Concurrent callers should use separate processes.
    """
    merged = {}
    for spec in specifications:
        prior = merged.get(spec.id)
        if prior:
            selected = prior if prior.required else spec
            spec = replace(
                selected,
                required=prior.required or spec.required,
                scope=tuple(sorted(set(prior.scope + spec.scope))),
            )
        merged[spec.id] = spec
    results = []
    for identifier, spec in sorted(merged.items()):
        check = registry.get(identifier)
        if check is None:
            outcome = CheckOutcome(
                State.UNKNOWN, Execution.NOT_RUN, f"Required provider is unconfigured: {identifier}"
            )
        else:
            output = io.StringIO()
            try:
                with redirect_stdout(output), redirect_stderr(output):
                    outcome = normalize(check(context))
                    validate_document(
                        CheckReport(
                            context.identity, (CheckResult(spec, outcome),), version.GOVKIT_VERSION
                        ).to_document(),
                        "check-results",
                    )
                if output.getvalue():
                    outcome = CheckOutcome(
                        State.UNKNOWN,
                        Execution.ERROR,
                        "Check emitted output instead of returning complete findings",
                    )
            except (Exception, SystemExit) as exc:
                # Do not publish exception payloads that may contain credentials.
                outcome = CheckOutcome(
                    State.UNKNOWN,
                    Execution.ERROR,
                    f"Check could not complete ({type(exc).__name__}); inspect its input/dependency and rerun",
                )
        results.append(CheckResult(spec, normalize(outcome)))
    report = CheckReport(context.identity, tuple(results), version.GOVKIT_VERSION)
    validate_document(report.to_document(), "check-results")
    return report


def _evidence(data):
    return Evidence(
        data["source"],
        tuple(data["scope"]),
        data["method"],
        data["origin"],
        data["digest"],
        tuple(data["limitations"]),
    )


def load_report(path: Path) -> CheckReport:
    """Validate a raw report for inspection, not as authenticated gate input."""
    return parse_report(read_document(path))


def parse_report(data: dict) -> CheckReport:
    """Validate serialized facts without treating their origin as authenticated."""
    validate_document(data, "check-results")
    results = []
    for item in data["results"]:
        spec = CheckSpec(
            item["id"],
            item["required"],
            item["reason"],
            item["source_policy"],
            tuple(item["scope"]),
        )
        findings = tuple(
            Finding(
                f["code"],
                f["severity"],
                f["category"],
                f["message"],
                f["suggested_action"],
                f["location"],
                tuple(_evidence(e) for e in f["evidence"]),
            )
            for f in item["findings"]
        )
        outcome = CheckOutcome(
            State(item["state"]),
            Execution(item["execution"]),
            item["summary"],
            findings,
            tuple(_evidence(e) for e in item["evidence"]),
        )
        results.append(CheckResult(spec, normalize(outcome)))
    report = CheckReport(Identity(**data["identity"]), tuple(results), data["govkit_version"])
    if len({r.spec.id for r in results}) != len(results) or report.to_json() != canonical_json(
        data
    ):
        raise DocumentError(
            "Result states, stable finding identities or summary do not match their evidence"
        )
    return report
