# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Architecture experiment records and preflight outcomes (ADR 0020).

Pure: callers supply parsed records, a digest reader and an optional clock.
Nothing here reads files, prints, exits or uses the wall clock.

An assessment reports three finding classes. `error` means a record is
invalid or contradictory, or a preflight relies on evidence that cannot
support it. `outstanding` means work remains. `unknown` means a digest or
expiry could not be verified. A clean assessment means the supplied records
are consistent and current; it does not show that an experiment ran or that
its evidence is authentic.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime

from .release_metadata import timestamp
from .schema_validation import (
    DocumentError,
    canonical_json,
    content_digest,
    parse_document,
    validate_document,
)

ERROR, OUTSTANDING, UNKNOWN = "error", "outstanding", "unknown"

# Decisions that close an experiment: its files no longer support anything,
# so later changes to them are not reassessment work.
_CLOSING_DECISIONS = {"revise-design", "reject-approach", "narrow-supported-behavior"}
_FENCED_YAML = re.compile(r"^```ya?ml[ \t]*\r?\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)
_OUTCOME_KEY = re.compile(r"^preflight_outcome\s*:", re.MULTILINE)
_FEATURE_RECORD = re.compile(r"^features/([^/]+)/experiments\.yaml$")


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    experiment: str | None = None
    record: str | None = None


@dataclass(frozen=True)
class ExperimentState:
    id: str
    record: str
    declared: str
    effective: str
    result_digest: str | None
    decision: str | None


@dataclass(frozen=True)
class Assessment:
    outcome: dict | None
    experiments: tuple[ExperimentState, ...]
    findings: tuple[Finding, ...]

    def _has(self, severity: str) -> bool:
        return any(f.severity == severity for f in self.findings)

    @property
    def has_errors(self) -> bool:
        return self._has(ERROR)

    @property
    def has_outstanding(self) -> bool:
        return self._has(OUTSTANDING)

    @property
    def has_unknown(self) -> bool:
        return self._has(UNKNOWN)

    @property
    def ready_for_completion(self) -> bool:
        return not self.findings


def _digest(value: object) -> str:
    return content_digest(canonical_json(value).encode())


def result_digest(result: dict) -> str:
    """Identity of one recorded result; a preflight relies on it by value."""
    return _digest(result)


def criteria_digest(criteria: list) -> str:
    return _digest(criteria)


def inputs_digest(depends_on: list) -> str:
    return _digest(depends_on)


def parse_experiment_set(document: dict) -> dict:
    """Validate an experiment set; raise DocumentError when it is unusable."""
    validate_document(document, "experiment-set")
    seen = set()
    for experiment in document["experiments"]:
        if experiment["id"] in seen:
            raise DocumentError(f"Duplicate experiment id: {experiment['id']}")
        seen.add(experiment["id"])
        criteria = [c["id"] for c in experiment["acceptance_criteria"]]
        if len(criteria) != len(set(criteria)):
            raise DocumentError(f"Duplicate acceptance criterion id in {experiment['id']}")
        stamps = [
            experiment.get("result", {}).get("observed_at"),
            experiment.get("decision", {}).get("recorded_at"),
        ]
        for value in filter(None, stamps):
            timestamp(value)
    return document


def parse_preflight_outcome(markdown: str) -> dict | None:
    """Return the preflight_outcome mapping, or None when no block is declared."""
    blocks = [b for b in _FENCED_YAML.findall(markdown) if _OUTCOME_KEY.search(b)]
    if not blocks:
        return None
    if len(blocks) > 1:
        raise DocumentError("Declare exactly one preflight_outcome block")
    document = parse_document(blocks[0])
    if not isinstance(document, dict):
        raise DocumentError("preflight_outcome block must be a mapping")
    validate_document(document, "preflight-outcome")
    return document["preflight_outcome"]


def assess(
    outcome: dict | str | None,
    records: Mapping[str, dict | str],
    *,
    default_record: str,
    read_digest: Callable[[str], str | None],
    now: datetime | None = None,
) -> Assessment:
    """Assess one feature's preflight outcome and experiment records.

    `outcome` and each record value are either parsed documents or a parse
    error message. `records` holds the feature's own record under
    `default_record` plus any other features' records named by `relies_on`;
    only the feature's own record contributes experiment-level findings.
    """
    findings: list[Finding] = []
    states: dict[str, dict[str, tuple[ExperimentState, list[Finding]]]] = {}
    for path, document in sorted(records.items()):
        own = path == default_record
        if isinstance(document, str):
            if own:
                findings.append(Finding("invalid-record", ERROR, document, record=path))
            continue
        try:
            parse_experiment_set(document)
        except DocumentError as exc:
            if own:
                findings.append(Finding("invalid-record", ERROR, str(exc), record=path))
            continue
        folder = _FEATURE_RECORD.match(path)
        if own and folder and document["feature"] != folder[1]:
            findings.append(
                Finding(
                    "feature-mismatch",
                    ERROR,
                    f"Record names feature {document['feature']!r} but lives in {folder[1]!r}",
                    record=path,
                )
            )
        states[path] = {}
        for experiment in document["experiments"]:
            exp_state, exp_findings = _assess_experiment(experiment, path, read_digest, now)
            states[path][experiment["id"]] = (exp_state, exp_findings)
            if own:
                findings.extend(exp_findings)

    parsed_outcome = None
    if isinstance(outcome, str):
        findings.append(Finding("invalid-outcome", ERROR, outcome))
    elif outcome is not None:
        parsed_outcome = outcome
        findings.extend(_assess_outcome(outcome, records, states, default_record))

    own_states = states.get(default_record, {})
    return Assessment(
        outcome=parsed_outcome,
        experiments=tuple(s for s, _ in own_states.values()),
        findings=tuple(findings),
    )


def _assess_experiment(experiment, record, read_digest, now):
    exp_id, declared = experiment["id"], experiment["status"]
    decision = experiment.get("decision")
    decision_outcome = decision["outcome"] if decision else None
    findings: list[Finding] = []

    def add(code, severity, message):
        findings.append(Finding(code, severity, message, experiment=exp_id, record=record))

    result = experiment.get("result")
    if result is None:
        if declared in ("planned", "running"):
            add("experiment-outstanding", OUTSTANDING, f"{exp_id} is {declared}")
        return ExperimentState(exp_id, record, declared, declared, None, decision_outcome), findings

    integrity = _check_criteria(experiment, result, add)
    computed = None if integrity else _computed_outcome(result)
    if computed is not None and result["evidence_class"] != experiment["required_evidence_class"]:
        if result["evidence_class"] == "synthetic-fixture":
            add(
                "insufficient-evidence-class",
                OUTSTANDING,
                f"{exp_id} requires application evidence; the result is a synthetic fixture",
            )
            if computed == "passed":
                computed = "inconclusive"
    if (
        computed is not None
        and declared in ("passed", "failed", "inconclusive")
        and computed != declared
    ):
        add(
            "status-contradiction",
            ERROR,
            f"{exp_id} declares {declared} but its criteria results show {computed}",
        )
    if decision:
        if timestamp(decision["recorded_at"]) < timestamp(result["observed_at"]):
            add(
                "decision-precedes-result",
                ERROR,
                f"{exp_id} decision was recorded before its result was observed",
            )
        if decision_outcome == "adopt" and computed != "passed":
            add("adopt-without-pass", ERROR, f"{exp_id} adopts a result that did not pass")

    closed = decision_outcome in _CLOSING_DECISIONS
    stale = False if closed else _check_currency(experiment, result, read_digest, now, add)

    if declared in ("passed", "failed", "inconclusive") and not closed:
        if decision is None:
            add("decision-required", OUTSTANDING, f"{exp_id} has a result but no decision")
        elif decision_outcome == "rerun":
            add("rerun-pending", OUTSTANDING, f"{exp_id} is waiting for a rerun")
    elif declared in ("planned", "running"):
        add("experiment-outstanding", OUTSTANDING, f"{exp_id} is {declared}")

    if integrity:
        effective = "invalid"
    elif declared in ("planned", "running", "withdrawn"):
        effective = declared
    elif stale:
        effective = "stale"
    else:
        effective = computed
    return (
        ExperimentState(
            exp_id, record, declared, effective, result_digest(result), decision_outcome
        ),
        findings,
    )


def _check_criteria(experiment, result, add) -> bool:
    """Report result rows that do not match the declared criteria."""
    declared = [c["id"] for c in experiment["acceptance_criteria"]]
    reported = [c["id"] for c in result["criteria"]]
    broken = False
    for criterion in sorted(set(reported) - set(declared)):
        add("unknown-criterion", ERROR, f"Result reports undeclared criterion {criterion}")
        broken = True
    for criterion in sorted({c for c in reported if reported.count(c) > 1}):
        add("duplicate-criterion-result", ERROR, f"Criterion {criterion} is reported twice")
        broken = True
    for criterion in [c for c in declared if c not in reported]:
        add("missing-criterion-result", ERROR, f"Criterion {criterion} has no result")
        broken = True
    return broken


def _computed_outcome(result) -> str:
    outcomes = {c["outcome"] for c in result["criteria"]}
    if "fail" in outcomes:
        return "failed"
    if "unknown" in outcomes:
        return "inconclusive"
    return "passed"


def _check_currency(experiment, result, read_digest, now, add) -> bool:
    """Compare recorded digests and expiry with current inputs; True when stale."""
    exp_id = experiment["id"]
    stale = False
    current_criteria = criteria_digest(experiment["acceptance_criteria"])
    if current_criteria != result["criteria_digest"]:
        add(
            "criteria-changed-after-result",
            OUTSTANDING,
            f"{exp_id} acceptance criteria changed after the result was recorded "
            f"(current criteria digest {current_criteria})",
        )
        stale = True
    current_inputs = inputs_digest(experiment["depends_on"])
    if current_inputs != result["inputs_digest"]:
        add(
            "inputs-changed-after-result",
            OUTSTANDING,
            f"{exp_id} dependencies were re-pinned after the result; rerun the experiment "
            f"(current inputs digest {current_inputs})",
        )
        stale = True
    for requirement in experiment["requirements"]:
        current = read_digest(requirement["path"])
        if current is None:
            add(
                "unverifiable-requirement",
                UNKNOWN,
                f"Cannot verify requirement {requirement['path']}",
            )
        elif current != requirement["digest"]:
            add(
                "stale-requirement",
                OUTSTANDING,
                f"Requirement {requirement['path']} changed after {exp_id} ran "
                f"(current digest {current})",
            )
            stale = True
    for dependency in experiment["depends_on"]:
        current = read_digest(dependency["path"])
        if current is None:
            add(
                "unverifiable-dependency",
                UNKNOWN,
                f"Cannot verify {dependency['kind']} dependency {dependency['path']}",
            )
        elif current != dependency["digest"]:
            add(
                "stale-dependency",
                OUTSTANDING,
                f"{dependency['kind']} dependency {dependency['path']} changed after "
                f"{exp_id} ran (current digest {current})",
            )
            stale = True
    for criterion in result["criteria"]:
        for evidence in criterion["evidence"]:
            current = read_digest(evidence["path"])
            if current is None:
                add(
                    "unverifiable-evidence",
                    UNKNOWN,
                    f"Cannot verify evidence {evidence['path']} for {criterion['id']}",
                )
            elif current != evidence["digest"]:
                add(
                    "evidence-digest-mismatch",
                    ERROR,
                    f"Evidence {evidence['path']} no longer matches the recorded result",
                )
    days = experiment["limits"].get("expires_after_days")
    if days is not None:
        observed = timestamp(result["observed_at"])
        if now is None:
            add("expiry-unverifiable", UNKNOWN, f"{exp_id} expires but no clock was supplied")
        elif observed > now:
            add("result-in-future", UNKNOWN, f"{exp_id} result is later than the supplied clock")
        elif (now - observed).total_seconds() > days * 86400:
            add("expired", OUTSTANDING, f"{exp_id} result is older than {days} days")
            stale = True
    return stale


def _assess_outcome(outcome, records, states, default_record):
    findings: list[Finding] = []
    status = outcome["status"]
    own = states.get(default_record, {})
    if status == "experiment-required":
        for exp_id in outcome["experiments"]:
            if exp_id not in own:
                findings.append(
                    Finding(
                        "unknown-experiment",
                        ERROR,
                        f"Preflight requires {exp_id}, which {default_record} does not define",
                        experiment=exp_id,
                        record=default_record,
                    )
                )
        findings.append(
            Finding(
                "experiment-required",
                OUTSTANDING,
                "Preflight requires experiments; reassess it once they resolve",
            )
        )
    elif status == "adr-required":
        findings.append(
            Finding(
                "adr-required", OUTSTANDING, "Preflight requires an ADR before planning continues"
            )
        )
    elif status == "blocked":
        findings.append(Finding("preflight-blocked", OUTSTANDING, "Preflight is blocked"))

    for reliance in outcome.get("relies_on", []):
        path = reliance.get("record", default_record)
        exp_id = reliance["experiment"]

        def add(code, severity, message, path=path, exp_id=exp_id):
            findings.append(Finding(code, severity, message, experiment=exp_id, record=path))

        if path not in records:
            add("missing-record", ERROR, f"Relied-upon record {path} is not present")
            continue
        if path not in states:
            add("invalid-reliance", ERROR, f"Relied-upon record {path} is invalid")
            continue
        if exp_id not in states[path]:
            add("unknown-experiment", ERROR, f"{path} does not define {exp_id}")
            continue
        exp_state, exp_findings = states[path][exp_id]
        if exp_state.result_digest != reliance["result_digest"] or exp_state.effective == "stale":
            add(
                "stale-reliance",
                ERROR,
                f"Preflight relies on {exp_id}, whose evidence changed or is stale; reassess "
                f"(current result digest {exp_state.result_digest})",
            )
        elif exp_state.effective != "passed" or exp_state.decision != "adopt":
            add(
                "invalid-reliance",
                ERROR,
                f"Preflight relies on {exp_id}, which is not a passed and adopted experiment",
            )
        elif any(f.severity == UNKNOWN for f in exp_findings):
            add(
                "reliance-unverifiable",
                UNKNOWN,
                f"Preflight relies on {exp_id}, whose evidence cannot be verified",
            )
    return findings


__all__ = [
    "Assessment",
    "ExperimentState",
    "Finding",
    "assess",
    "criteria_digest",
    "inputs_digest",
    "parse_experiment_set",
    "parse_preflight_outcome",
    "result_digest",
]
