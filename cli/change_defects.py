# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Existing defect eligibility plus explicitly executed baseline/current tests."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import replace
from pathlib import Path

from .check_models import CheckOutcome, Evidence, Execution, State
from .fixes import FixRecord, validate_fix_record
from .pack_loading import contained_file
from .schema_validation import content_digest, read_document, validate_document
from .workflows import _covers


def _schema(record, target):
    validate_document(record.data, "fix_record")
    return [], []


def _materialize(directory, files, modes):
    for name, content in files.items():
        destination = directory / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        destination.chmod(0o755 if modes.get(name) == "100755" else 0o644)


def defect_check(request, change, references, command, selected, run_command):
    def check(context):
        if len(references) != 1:
            return CheckOutcome(
                State.UNKNOWN,
                Execution.NOT_RUN,
                "Configure exactly one existing fix-record reference",
            )
        reference = references[0]
        try:
            path = contained_file(context.target, reference)
            if path.name != "fix.yaml" or path.parent.parent.name != "fixes":
                raise ValueError("Unexpected fix-record location")
            record = FixRecord(path.parent.name, path.parent, path, read_document(path))
            validate_document(record.data, "fix_record")
            sources = [
                record.data["expectation"]["source"],
                record.data["reproduction"]["test"],
                *record.data["surface"]["paths"],
            ]
            for source in sources:
                contained_file(context.target, source)
            issues, warnings = validate_fix_record(record, context.target, schema_validator=_schema)
            established = {
                r["reference"]
                for r in request.document["references"]
                if r["kind"] == "established-behavior" and r["authority"] == "accepted"
            }
            tests = {
                r["reference"]
                for r in request.document["references"]
                if r["kind"] == "regression-test"
            }
            if (
                record.data["expectation"]["source"] not in established
                or record.data["reproduction"]["test"] not in tests
            ):
                issues.append("Fix references differ from accepted normalized intent")
            if any(
                p != reference and not any(_covers(s, p) for s in record.data["surface"]["paths"])
                for p in change.paths
            ):
                issues.append("Actual changed scope exceeds the fix surface")
            proof = Evidence(
                reference,
                tuple(record.data["surface"]["paths"]),
                "existing-defect-contract",
                "local-check",
                content_digest(path.read_bytes()),
                ("Record validation is not by itself red/green execution.",),
            )
            if issues:
                return CheckOutcome(
                    State.FAIL,
                    Execution.EXECUTED,
                    "Existing defect eligibility failed: " + "; ".join(issues),
                    evidence=(proof,),
                )
            if warnings or not change.complete:
                return CheckOutcome(
                    State.UNKNOWN,
                    Execution.NOT_RUN,
                    "Defect scope or eligibility is incomplete",
                    evidence=(proof,),
                )
            if "defect:eligibility" not in selected or not command:
                return CheckOutcome(
                    State.SKIPPED,
                    Execution.NOT_RUN,
                    "Red/green verification needs a configured project test command and explicit defect:eligibility execution",
                    evidence=(proof,),
                )
            green = run_command(command, {command["id"]})(context)
            if green.state is not State.PASS:
                return CheckOutcome(
                    green.state,
                    green.execution,
                    "Current project tests must pass before a defect can be verified",
                    evidence=(proof, *green.evidence),
                )
            if not tests <= change.files.keys():
                return CheckOutcome(
                    State.UNKNOWN,
                    Execution.NOT_RUN,
                    "Regression test inputs must be included in the captured Git scope",
                    evidence=(proof,),
                )
            # Both snapshots use the current declared regression tests. A missing
            # or obsolete test in the base is not evidence of a production defect.
            baseline_files = dict(change.base_files)
            baseline_modes = dict(change.base_file_modes)
            for name in tests:
                baseline_files[name] = change.files[name]
                baseline_modes[name] = change.file_modes[name]
            with tempfile.TemporaryDirectory(prefix="govkit-defect-") as directory:
                checkout = Path(directory) / "checkout"
                isolated_context = replace(context, target=checkout)
                _materialize(checkout, change.files, change.file_modes)
                isolated_green = run_command(command, {command["id"]})(isolated_context)
                if isolated_green.state is not State.PASS:
                    return CheckOutcome(
                        State.UNKNOWN,
                        Execution.EXECUTED,
                        "Current tests do not pass in snapshot isolation; missing Git metadata or dependencies cannot prove a defect",
                        evidence=(proof, *green.evidence, *isolated_green.evidence),
                    )
                shutil.rmtree(checkout)
                _materialize(checkout, baseline_files, baseline_modes)
                red = run_command(command, {command["id"]})(isolated_context)
            state = (
                State.PASS
                if red.state is State.FAIL and green.state is State.PASS
                else State.UNKNOWN
                if red.state in {State.UNKNOWN, State.SKIPPED}
                or green.state in {State.UNKNOWN, State.SKIPPED}
                else State.FAIL
            )
            return CheckOutcome(
                state,
                Execution.EXECUTED,
                "The same current regression tests must fail on base code and pass on isolated current code and the current target; this measures only the selected tests",
                evidence=(proof, *red.evidence, *isolated_green.evidence, *green.evidence),
            )
        except (OSError, ValueError):
            return CheckOutcome(
                State.FAIL,
                Execution.EXECUTED,
                "Fix record or referenced sources are missing, unsafe or invalid",
            )

    return check
