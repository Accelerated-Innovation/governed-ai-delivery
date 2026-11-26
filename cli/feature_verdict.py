# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""One answer for a feature: done, continue or escalate.

`decide` reads a feature evidence report and the results of the checks that ran
beside it, and lists every reason the feature is not done. Each reason says who
can act on it: the agent (`continue`) or a person (`escalate`). The state is the
first that applies:

1. `escalate` when the change altered the definition or a protected file, or
   the evidence is in error. A person is needed now, whatever else is open.
2. `continue` when anything is left that the agent can do.
3. `escalate` when what is left needs a person.
4. `done` when there is no reason at all.

The module is pure. It runs nothing and reads no file. A `done` computed in a
working tree is a stop condition for whoever is doing the work, not a gate: the
run that counts is CI on a clean checkout. See ADR 0028.
"""

from __future__ import annotations

from dataclasses import dataclass

DONE, CONTINUE, ESCALATE = "done", "continue", "escalate"
STATES = (DONE, CONTINUE, ESCALATE)
# 2 is left for an invocation that could not run.
EXIT_CODES = {DONE: 0, CONTINUE: 1, ESCALATE: 3}
EVIDENCE_CHECK = "evidence:feature"

# A public contract: add, never rename. The order is the order of a report.
_NOW = {
    "definition-changed": (
        "the change removed or altered part of the definition it is judged by",
        "A person must confirm the change to the definition, or it must be restored.",
    ),
    "protected-changed": (
        "the change altered an existing test or a protected file",
        "A person must confirm the change to the protected file, or it must be restored.",
    ),
    "result-error": (
        "{count} {items} ended in an error",
        "A person must look at the error; it is not a failed assertion.",
    ),
    "evidence-unreadable": (
        "the evidence could not be read: {detail}",
        "A person must repair the definition or result file that could not be read.",
    ),
    "check-error": (
        "{check} is required and did not complete",
        "A person must find out why {check} could not run to an end.",
    ),
}
_AGENT = {
    "result-failed": ("{count} {items} failed", "Fix the implementation and run the tests again."),
    "result-missing": (
        "{count} {items} have no result",
        "Run the tests and free evaluations, then record the results.",
    ),
    "results-stale": (
        "the results are stale: {detail}",
        "Run the tests again and record the results.",
    ),
    "results-unrecorded": (
        "the results are not recorded: {detail}",
        "Record the results with `govkit evidence --record`.",
    ),
    "record-unusable": (
        "the evidence record cannot be used: {detail}",
        "Run the tests again and record the results.",
    ),
    "check-failed": ("{check} failed", "Resolve the findings of {check} and run again."),
}
_PERSON = {
    "result-skipped": (
        "{count} {items} were skipped",
        "A person must decide what the skipped tests need to run.",
    ),
    "result-owed": (
        "{count} {items} need a paid or human evaluation",
        "A person must arrange the owed evaluations.",
    ),
    "skips-unmarked": (
        "a result file counts skipped tests it does not mark",
        "A person must make the test runner mark skipped tests.",
    ),
    "criteria-not-compared": (
        "the criteria are in a form that is not compared",
        "A person must judge the criteria; GovKit does not compare this form.",
    ),
    "no-scenarios": (
        "the feature has no scenarios to judge it by",
        "A person must supply the feature's scenarios.",
    ),
    "check-not-satisfied": (
        "{check} is required and its state is {state}",
        "A person must supply or accept what {check} needs.",
    ),
    "evidence-inconclusive": (
        "the evidence is not a pass: {detail}",
        "A person must read the evidence report.",
    ),
}
_GROUPS = ((ESCALATE, _NOW), (CONTINUE, _AGENT), (ESCALATE, _PERSON))
CODES = tuple(code for _, group in _GROUPS for code in group)
_CHANGE_CHECKS = {
    "change:definition": "definition-changed",
    "change:protected": "protected-changed",
}
_BY_OUTCOME = {
    "error": "result-error",
    "failed": "result-failed",
    "missing": "result-missing",
    "skipped": "result-skipped",
    "owed": "result-owed",
}
_BY_PROVENANCE = {
    "stale": "results-stale",
    "unrecorded": "results-unrecorded",
    "unavailable": "record-unusable",
}


@dataclass(frozen=True)
class Check:
    """One check that ran beside the evidence: its identifier, whether it is required, its state."""

    id: str
    required: bool
    state: str
    # The check itself did not complete, which is not the same as failing.
    errored: bool = False


def decide(evidence: dict, checks, *, evidence_check: str = EVIDENCE_CHECK) -> dict:
    """The state of the feature `evidence` reports on, with every reason.

    `checks` are `Check` values for the run. The evidence check among them,
    named by `evidence_check`, is read through `evidence`, so a failed scenario
    is reported once.
    """
    found: dict[str, list[dict]] = {code: [] for code in CODES}

    def add(code: str, check: str = evidence_check, requirements=(), **values) -> None:
        count = len(requirements)
        items = "requirement" if count == 1 else "requirements"
        values = {"check": check, "count": count, "items": items, **values}
        message, action = next(group[code] for _, group in _GROUPS if code in group)
        found[code].append(
            {
                "code": code,
                "check": check,
                "requirements": list(requirements),
                "message": message.format(**values),
                "action": action.format(**values),
            }
        )

    outcome, results = evidence["outcome"], evidence["results"]
    for state, code in _BY_OUTCOME.items():
        named = [r["requirement_id"] for r in results if r["outcome"] == state]
        if named:
            add(code, requirements=named)
    # Criteria that are declared and have no result line were never judged:
    # their results file could not be read, whatever a scenario also did.
    unjudged = evidence["summary"].get("criteria", 0) > 0 and not any(
        r["kind"] == "evaluation" for r in results
    )
    if outcome == "ERROR" and (unjudged or not found["result-error"]):
        add("evidence-unreadable", detail=evidence["detail"])
    provenance = evidence["provenance"]
    if provenance["state"] in _BY_PROVENANCE:
        add(_BY_PROVENANCE[provenance["state"]], detail=provenance["detail"])
    if any(source.get("unidentified_skipped") for source in evidence["sources"]):
        add("skips-unmarked")
    if evidence["feature"]["criteria"]["form"] == "data":
        add("criteria-not-compared")
    if evidence["summary"]["scenarios"] == 0 and outcome != "ERROR":
        add("no-scenarios")
    if outcome != "PASS" and not any(found.values()):
        # Whatever a later report adds, anything short of a pass is never done.
        add("evidence-inconclusive", detail=evidence["detail"])

    for check in sorted(checks, key=lambda c: c.id):
        if check.id == evidence_check:
            continue
        if check.state == "fail":
            add(_CHANGE_CHECKS.get(check.id, "check-failed"), check=check.id)
        elif check.required and check.errored:
            add("check-error", check=check.id)
        elif check.required and check.state != "pass":
            add("check-not-satisfied", check=check.id, state=check.state)

    reasons = [
        {"state": state, **reason}
        for state, group in _GROUPS
        for code in group
        for reason in found[code]
    ]
    if any(found[code] for code in _NOW):
        state = ESCALATE
    elif any(found[code] for code in _AGENT):
        state = CONTINUE
    elif reasons:
        state = ESCALATE
    else:
        state = DONE
    return {
        "feature": evidence["feature"]["name"],
        "state": state,
        "exit_code": EXIT_CODES[state],
        "reasons": reasons,
    }


_CLOSING = {
    DONE: "Nothing is left to do for this feature.",
    CONTINUE: "Work is left that does not need a person. Do it and run this again.",
    ESCALATE: "A person is needed. Do not work around what is listed as escalate.",
}
_NOT_A_GATE = (
    "In a working tree this is a stop condition, not a gate: "
    "the run that counts is CI on a clean checkout."
)


def render(answer: dict) -> str:
    """The text form of an answer document."""
    lines = [f"Feature {answer['feature']}: {answer['state'].upper()}"]
    for reason in answer["reasons"]:
        lines.append(
            f"  {reason['state']:8}  {reason['code']} [{reason['check']}]: {reason['message']}"
        )
        lines += [f"            {requirement}" for requirement in reason["requirements"]]
        lines.append(f"            {reason['action']}")
    lines += [_CLOSING[answer["state"]], _NOT_A_GATE]
    return "\n".join(lines)
