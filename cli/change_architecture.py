# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Pure, scoped literal-boundary measurements with baseline exception accounting."""

from __future__ import annotations

from datetime import date, datetime

from .check_models import CheckOutcome, Execution, Finding, State
from .workflows import _covers


def assess_architecture(profile, policy, change, observed_at, evidence):
    if not change.complete:
        return CheckOutcome(
            State.UNKNOWN, Execution.NOT_RUN, "Architecture scope is incomplete", evidence=evidence
        )
    findings, measured, unknown = [], set(), False
    as_of = (
        datetime.fromisoformat(observed_at.replace("Z", "+00:00")).date() if observed_at else None
    )
    transitions = profile.document["policy"].get("transitions", [])
    contracts = [(c, None, "current") for c in profile.document["policy"].get("contracts", [])]
    for transition in transitions:
        contracts.extend((c, transition, "current") for c in transition["current"])
        if transition["mode"] != "retain":
            contracts.extend((c, transition, "target") for c in transition["target"])
    if not contracts:
        return CheckOutcome(
            State.UNKNOWN,
            Execution.NOT_RUN,
            "No accepted architecture constraints are measurable",
            evidence=evidence,
        )
    statuses = {c.path: c.status for c in change.changes}
    for contract, transition, role in contracts:
        rules = [r for r in policy["constraints"] if r["source"] == contract["source"]["reference"]]
        if not rules:
            unknown = True
            findings.append(
                Finding(
                    "unmeasured-contract",
                    "warning",
                    "architecture",
                    f"No configured measurement for {contract['source']['reference']}",
                    "Configure a trusted constraint/provider; prose alone is not execution.",
                    contract["source"]["reference"],
                    evidence,
                )
            )
            continue
        for path, content in sorted(change.files.items()):
            if not any(_covers(s, path) for s in contract["scope"]):
                continue
            if transition and not any(_covers(s, path) for s in transition["scope"]):
                continue
            if role == "target" and transition["applies_to"] != "all":
                if path not in statuses or (
                    transition["applies_to"] == "new" and statuses[path] != "added"
                ):
                    continue
            applicable = [r for r in rules if any(_covers(s, path) for s in r["paths"])]
            if not applicable:
                unknown = True
                findings.append(
                    Finding(
                        "unmeasured-file",
                        "warning",
                        "architecture",
                        "Accepted contract scope lacks a configured measurement",
                        "Extend the trusted constraint coverage.",
                        path,
                        evidence,
                    )
                )
                continue
            try:
                text = content.decode("utf-8")
                baseline = change.base_files.get(path, b"").decode("utf-8")
            except UnicodeError:
                unknown = True
                findings.append(
                    Finding(
                        "unmeasured-file",
                        "warning",
                        "architecture",
                        "Configured scope contains non-text content",
                        "Provide an appropriate trusted check.",
                        path,
                        evidence,
                    )
                )
                continue
            for rule in applicable:
                identity = (rule["id"], path, role)
                if identity in measured:
                    continue
                measured.add(identity)
                for forbidden in rule["forbidden_text"]:
                    count, old_count = text.count(forbidden), baseline.count(forbidden)
                    if not count:
                        continue
                    exception_candidates = (
                        [
                            e
                            for t in transitions
                            if any(_covers(s, path) for s in t["scope"])
                            and any(
                                c["source"] == contract["source"]
                                and any(_covers(s, path) for s in c["scope"])
                                for c in t["current"]
                            )
                            for e in t.get("exceptions", [])
                            if any(_covers(s, path) for s in e["scope"])
                        ]
                        if role == "current"
                        else []
                    )
                    valid = [
                        e
                        for e in exception_candidates
                        if as_of
                        and e["expires_at"]
                        and date.fromisoformat(e["expires_at"]) >= as_of
                    ]
                    existing = min(count, old_count)
                    if count > old_count:
                        findings.append(
                            Finding(
                                "new-violation",
                                "error",
                                "architecture",
                                f"New occurrence violates {rule['id']} ({role})",
                                "Remove the new violation; existing exceptions cannot excuse it.",
                                path,
                                evidence,
                            )
                        )
                    if existing:
                        if valid:
                            code, severity = "existing-exception", "info"
                        elif exception_candidates and (
                            not as_of or any(not e["expires_at"] for e in exception_candidates)
                        ):
                            code, severity, unknown = "unverified-exception-expiry", "warning", True
                        elif exception_candidates:
                            code, severity = "expired-exception", "error"
                        else:
                            code, severity = "existing-violation", "error"
                        findings.append(
                            Finding(
                                code,
                                severity,
                                "architecture",
                                f"Existing occurrence of {rule['id']} ({role}); exceptions: {', '.join(e['id'] for e in exception_candidates) or 'none'}",
                                "Retain bounded exception evidence or reconcile the violation.",
                                path,
                                evidence,
                            )
                        )
    state = (
        State.FAIL
        if any(f.severity == "error" for f in findings)
        else State.UNKNOWN
        if unknown
        else State.PASS
    )
    return CheckOutcome(
        state,
        Execution.EXECUTED,
        "Measured configured literal constraints; semantic architecture and approval are unmeasured",
        tuple(findings),
        evidence,
    )
