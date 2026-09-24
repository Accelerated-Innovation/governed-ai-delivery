# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Offline provider observations translated into the canonical CI check contract."""

from __future__ import annotations

from pathlib import Path

from .change_conformance import parse_change_report
from .change_scope import capture_change
from .check_models import CheckOutcome, CheckResult, CheckSpec, Evidence, Execution, Identity, State
from .check_runner import CheckReport, normalize
from .maintenance_inventory import inventory_repository
from .pipeline_render import parse_settings
from .pipeline_runtime import read_input
from .pipeline_store import check_pipeline, preview_pipeline
from .profiles import load_profile
from .release_metadata import timestamp
from .schema_validation import (
    DocumentError,
    canonical_json,
    content_digest,
    parse_document,
    validate_document,
)
from .version import GOVKIT_VERSION

LIMITATIONS = (
    "Caller-supplied exports do not authenticate provider origin; collect them through a trusted protected job.",
    "No provider is queried and no policy, workflow, package or branch protection is changed.",
)
ENFORCEMENT = ("enabled", "required_check", "all_changes", "trusted_policy", "approvals")


def _digest(document):
    return content_digest(canonical_json(document).encode())


def _fresh(observed_at, as_of, max_age):
    try:
        age = (timestamp(as_of) - timestamp(observed_at)).total_seconds() / 3600
        return max_age is not None and 0 <= age <= max_age
    except ValueError:
        return False


def collect_evidence(
    target, settings_source, packs, *, as_of, change_report=None, observation=None
):
    """Measure configuration and compare explicit trusted exports; never infer activation."""
    target = Path(target).absolute()
    timestamp(as_of)
    settings_bytes = read_input(Path(settings_source))
    settings = parse_settings(parse_document(settings_bytes))
    inventory = inventory_repository(target, as_of=as_of).document
    profile = load_profile(target / ".govkit/profile.yaml")
    facts, proofs = {}, {}
    try:
        preview = preview_pipeline(target / ".govkit/profile.yaml", target, settings_source, packs)
        configuration = check_pipeline(preview)
        artifact = preview.artifact.document
        state = State.PASS if configuration["configuration"] == "current" else State.FAIL
        facts["configuration"] = (
            state,
            "Generated integration is "
            + configuration["configuration"]
            + "; review pipeline preview before repair.",
        )
        proofs["configuration"] = _digest(configuration)
    except (OSError, ValueError):
        artifact = None
        facts["configuration"] = (
            State.FAIL,
            "Generated integration is invalid or protected; reconcile metadata and customizations through pipeline preview.",
        )
        proofs["configuration"] = inventory["identity"]["input_digest"]
    facts["runtime"] = (State.UNKNOWN, "No current bound change execution is available.")
    facts["enforcement"] = (
        State.UNKNOWN,
        "Required checks, activation, all-change admission and approvals need trusted provider observations.",
    )
    observed_at = as_of
    bound = False
    if observation is not None:
        validate_document(observation, "provider-observation")
        proofs["enforcement"] = _digest(observation)
        admission = settings.admission
        bound = bool(
            artifact
            and admission
            and inventory["identity"]["git_complete"]
            and observation["provider"] == artifact["provider"] == admission["provider"]
            and observation["repository"] == admission["repository"]
            and observation["target_ref"] == admission["target_ref"]
            and observation["revision"] == inventory["identity"]["revision"]
            and observation["artifact_digest"] == artifact["digest"]
            and _fresh(
                observation["observed_at"], as_of, profile.maintenance.assessment_max_age_hours
            )
        )
        if bound:
            observed_at = observation["observed_at"]
            values = [observation[key] for key in ENFORCEMENT]
            # Negative observations are actionable, but caller assertions cannot
            # independently establish that external controls are enforced.
            state = State.FAIL if False in values else State.UNKNOWN
            facts["enforcement"] = (
                state,
                "Provider export: "
                + ", ".join(f"{key}={observation[key]}" for key in ENFORCEMENT)
                + ". Provider origin is unauthenticated; verify protected caller and provider settings.",
            )
    if change_report is not None:
        runtime = parse_change_report(change_report)
        proofs["runtime"] = _digest(change_report)
        change = capture_change(target, runtime.change["base"])
        matched = bool(
            bound
            and observation["report_digest"] == proofs["runtime"]
            and observation["base"] == runtime.change["base"]
            and change.complete
            and change.document == runtime.change
            and runtime.checks.identity.repository == inventory["repository"]
            and runtime.checks.identity.profile_digest == inventory["identity"]["profile_digest"]
            and runtime.checks.identity.pack_lock_digest
            == inventory["identity"]["pack_lock_digest"]
            and _fresh(
                runtime.checks.identity.observed_at,
                as_of,
                profile.maintenance.assessment_max_age_hours,
            )
        )
        if matched:
            observed_at = min((observed_at, runtime.checks.identity.observed_at), key=timestamp)
            state = State.FAIL if runtime.state is State.FAIL else State.UNKNOWN
            if (
                observation["runtime_version"] != settings.govkit_version
                or runtime.checks.govkit_version != settings.govkit_version
            ):
                state = State.FAIL
            facts["runtime"] = (
                state,
                "Reported change results: "
                + runtime.state.value
                + "; execution origin is unauthenticated. Check runtime pin and required conformance outcomes.",
            )
        elif bound:
            facts["runtime"] = (
                State.UNKNOWN,
                "Provider run and change report identities disagree; collect matching evidence.",
            )
    values = [state for state, _ in facts.values()]
    overall = (
        State.FAIL
        if State.FAIL in values
        else State.PASS
        if all(s is State.PASS for s in values)
        else State.UNKNOWN
    )
    facts["integration"] = (
        overall,
        "Integration health requires current configuration, bound execution and explicit enforcement evidence.",
    )
    proofs["integration"] = _digest({"facts": facts, "proofs": proofs})
    fields = inventory["identity"]
    identity = Identity(
        inventory["repository"],
        revision=fields["revision"],
        dirty_digest=fields["dirty_digest"],
        profile_digest=fields["profile_digest"],
        resolution_digest=fields["resolution_digest"],
        pack_lock_digest=fields["pack_lock_digest"],
        change_digest=fields["input_digest"],
        observed_at=observed_at,
    )
    results = tuple(
        CheckResult(
            CheckSpec(
                "ci:" + name,
                True,
                "Assess the configured CI integration",
                ".govkit/profile.yaml#integrations/ci",
                (".",),
            ),
            normalize(
                CheckOutcome(
                    state,
                    Execution.EXECUTED,
                    message,
                    evidence=(
                        Evidence(
                            "pipeline:" + name,
                            (".",),
                            "bounded-local-and-provider-export-comparison",
                            "unverified-artifact"
                            if name in {"runtime", "enforcement"}
                            else "local-check",
                            proofs.get(name),
                            LIMITATIONS,
                        ),
                    ),
                )
            ),
        )
        for name, (state, message) in facts.items()
    )
    if (
        inventory_repository(target, as_of=as_of).document != inventory
        or read_input(Path(settings_source)) != settings_bytes
    ):
        raise DocumentError("Pipeline assessment inputs changed during collection")
    return CheckReport(identity, results, GOVKIT_VERSION)
