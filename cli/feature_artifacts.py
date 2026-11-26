# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""The feature artifact checks of `govkit validate`, for an installation without a level.

`govkit validate` chooses its feature checks from a legacy level. An installation
made from a profile has none, so `govkit conform --feature` chooses them from the
accepted profile instead: `gherkin-delivery` selects the level 4 checks and
`llm-evaluation` adds the level 5 checks. The check functions and their
identifiers are `validate`'s own, unchanged.

Each check becomes one conformance check, `feature:<identifier>`, for the
selected feature only. A failure is work for whoever is making the change. A
warning is reported as unknown, which is never a pass. The agent's own forecast
in `plan.md` is advisory and never fails. See ADR 0029.
"""

from __future__ import annotations

from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from . import paths, validate
from .check_models import CheckOutcome, Evidence, Execution, Finding, State
from .marker import TYPE_AREA
from .schema_validation import DocumentError, read_document

PREFIX = "feature:"
SELECTS = "gherkin-delivery"
ADDS_LLM = "llm-evaluation"
# The agent's own forecast. It is reported and can never count for or against.
FORECAST = "eval-prediction"
CRITERIA = "eval-criteria"
# Stands for "the schema bundled with GovKit"; `_instance_check` resolves the real file.
_BUNDLED = Path("eval_criteria.schema.json")
_LIMITATION = (
    "Artifact consistency only. It does not run tests or evaluations, and a "
    "forecast in plan.md is the producer's own assertion."
)
_STATE = {
    validate.CheckStatus.PASS: State.PASS,
    validate.CheckStatus.FAIL: State.FAIL,
    validate.CheckStatus.WARN: State.UNKNOWN,
}
_ACTION = "Bring the feature's artifacts in line with the finding and run again."
_NO_TYPE = (
    "eval_criteria.yaml structure OK; the accepted profile sets no repository.project_type, "
    "so no schema was chosen and instance validation is unknown"
)


def selected(capabilities) -> bool:
    """Whether the accepted profile's capabilities select the feature artifact checks."""
    return SELECTS in capabilities


def _instance_check(project_type: str | None):
    """Validate against the schema bundled with GovKit, never a copy in the inspected tree."""
    area = TYPE_AREA.get(project_type)

    def check(_schema: Path, instance: Path):
        if project_type is None:
            return validate.CheckStatus.WARN, _NO_TYPE
        if area is None:
            return (
                validate.CheckStatus.WARN,
                f"eval_criteria.yaml structure OK; project type {project_type!r} has no "
                "eval_criteria schema, so instance validation is unknown",
            )
        schema = paths.GOVERNANCE_DIR / area / "schemas" / "eval_criteria.schema.json"
        try:
            contract = read_document(schema)
        except (OSError, DocumentError):
            return (
                validate.CheckStatus.WARN,
                f"the bundled {area} eval_criteria schema is unavailable; validation is unknown",
            )
        try:
            data = read_document(instance)
        except (OSError, DocumentError):
            return validate.CheckStatus.FAIL, f"{instance.name} is not a readable document"
        errors = list(
            Draft202012Validator(contract, format_checker=FormatChecker()).iter_errors(data)
        )
        if errors:
            return (
                validate.CheckStatus.FAIL,
                f"{instance.name} fails the {area} eval_criteria schema ({len(errors)} error(s))",
            )
        return validate.CheckStatus.PASS, f"{instance.name} valid against the {area} schema"

    return check


def checks(target: Path, feature: str, capabilities, project_type: str | None) -> list:
    """`(identifier, required, check)` for each selected check, or an empty list."""
    if not selected(capabilities):
        return []
    level = "5" if ADDS_LLM in capabilities else "4"
    _, named = validate._named_checks(level, project_type)
    instance_check = _instance_check(project_type)

    def criteria(directory: Path):
        # No marker is consulted: the profile's project type decides the schema.
        return validate.check_eval_criteria(
            directory, schema=_BUNDLED, validate_instance=instance_check
        )

    directory = target / "features" / feature
    return [
        (
            PREFIX + name,
            name != FORECAST,
            _adapt(name, criteria if name == CRITERIA else check, directory, feature),
        )
        for name, check in named
    ]


def _adapt(name: str, check, directory: Path, feature: str):
    location = f"features/{feature}"
    forecast = name == FORECAST
    proof = (
        Evidence(
            location,
            (location,),
            "feature-artifact-check",
            "agent-assertion" if forecast else "local-check",
            None,
            (_LIMITATION,),
        ),
    )

    def run(_context) -> CheckOutcome:
        try:
            status, message = check(directory)
        except Exception as exc:
            return _outcome(State.UNKNOWN, f"the check could not complete ({type(exc).__name__})")
        state = _STATE[status]
        if forecast and state is not State.UNKNOWN:
            # A forecast is not evidence. It can neither pass nor fail the feature.
            state, message = State.UNKNOWN, f"forecast, not evidence: {message}"
        return _outcome(state, message)

    def _outcome(state: State, message: str) -> CheckOutcome:
        severity = "error" if state is State.FAIL else "info" if state is State.PASS else "warning"
        finding = Finding(name, severity, "feature", message, _ACTION, location, proof)
        return CheckOutcome(state, Execution.EXECUTED, message, (finding,), proof)

    return run
