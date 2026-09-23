# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Pure resolution of supplied requirements, without discovery or pack loading.

Adapters decide which available contributions enter these explicit inputs.
This module checks consistency; it never infers approval or downloads a missing
capability. Full pack/version graph resolution and workflow selection come later.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from typing import TypeVar

from .resolution_models import (
    ArtifactRequirement,
    Authority,
    CapabilityRequirement,
    CheckRequirement,
    InstallationPlan,
    Reason,
    RepositoryInput,
    RequestInput,
    Selections,
    UnresolvedDecision,
    WorkflowPlan,
)

Requirement = TypeVar("Requirement", CapabilityRequirement, ArtifactRequirement, CheckRequirement)
Contribution = TypeVar("Contribution", ArtifactRequirement, CheckRequirement)


def _decision(code: str, affected: tuple[str, ...], message: str, reasons: tuple[Reason, ...]):
    identity = hashlib.sha256(
        json.dumps(affected, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return UnresolvedDecision(f"{code}:{identity}", code, affected, message, reasons)


def _merge_requirements(
    requirements: tuple[Requirement, ...],
    kind: str,
    decisions: list[UnresolvedDecision],
) -> tuple[Requirement, ...]:
    selected: dict[str, Requirement] = {}
    for item in requirements:
        affected = (f"{kind}:{item.id}",)
        if not item.reasons or any(not r.text or not r.source.reference for r in item.reasons):
            decisions.append(
                _decision("missing-reason", affected, "Supply a reason and source.", item.reasons)
            )
        if any(
            r.source.authority in (Authority.OBSERVED, Authority.PROPOSED) for r in item.reasons
        ):
            decisions.append(
                _decision(
                    "unaccepted-requirement",
                    affected,
                    "Observed practice or a proposal needs an explicit accepted decision before adoption.",
                    item.reasons,
                )
            )
        prior = selected.get(item.id)
        if prior is None:
            selected[item.id] = item
        elif replace(prior, reasons=()) != replace(item, reasons=()):
            decisions.append(
                _decision(
                    "conflicting-declaration",
                    affected,
                    "Different declarations use the same identifier; reconcile them before applying.",
                    prior.reasons + item.reasons,
                )
            )
        else:
            reasons = tuple(dict.fromkeys(prior.reasons + item.reasons))
            selected[item.id] = replace(prior, reasons=reasons)
    return tuple(selected.values())


def _resolve(
    capabilities: tuple[CapabilityRequirement, ...],
    artifacts: tuple[ArtifactRequirement, ...],
    checks: tuple[CheckRequirement, ...],
    initial_decisions: tuple[UnresolvedDecision, ...] = (),
) -> Selections:
    decisions = list(initial_decisions)
    capabilities = _merge_requirements(capabilities, "capability", decisions)
    by_id = {c.id: c for c in capabilities}
    for capability in capabilities:
        for dependency in capability.requires:
            if dependency not in by_id:
                decisions.append(
                    _decision(
                        "missing-capability",
                        (capability.id, dependency),
                        f"{capability.id} requires the unselected capability {dependency}.",
                        capability.reasons,
                    )
                )
        for conflict in capability.conflicts:
            if conflict in by_id:
                decisions.append(
                    _decision(
                        "capability-conflict",
                        tuple(sorted((capability.id, conflict))),
                        "Conflicting capabilities were selected; reconcile the explicit inputs.",
                        capability.reasons + by_id[conflict].reasons,
                    )
                )

    def applicable(items: tuple[Contribution, ...], kind: str) -> tuple[Contribution, ...]:
        result = []
        for item in _merge_requirements(items, kind, decisions):
            if item.capability_id is not None and item.capability_id not in by_id:
                decisions.append(
                    _decision(
                        "unavailable-capability",
                        (f"{kind}:{item.id}", item.capability_id),
                        f"Select an available {item.capability_id} capability before using {item.id}.",
                        item.reasons,
                    )
                )
            else:
                result.append(item)
        return tuple(result)

    selected_artifacts = applicable(artifacts, "artifact")
    selected_checks = applicable(checks, "check")
    # Coalesce symmetric conflict reports without losing either declaration's reasons.
    unique: dict[str, UnresolvedDecision] = {}
    for decision in decisions:
        previous = unique.get(decision.id)
        if previous:
            decision = replace(
                decision, reasons=tuple(dict.fromkeys(previous.reasons + decision.reasons))
            )
        unique[decision.id] = decision
    return Selections(capabilities, selected_artifacts, selected_checks, tuple(unique.values()))


def resolve_repository(repository: RepositoryInput) -> InstallationPlan:
    """Resolve a snapshot; returned data never aliases mutable caller attributes."""
    repository = deepcopy(repository)
    policy_checks = ()
    if repository.policy:
        required = Reason("Required by accepted policy", repository.policy.source)
        policy_checks = tuple(
            replace(check, reasons=check.reasons + (required,))
            for check in repository.policy.required_checks
        )
    selections = _resolve(
        repository.capabilities, repository.artifacts, policy_checks + repository.checks
    )
    return InstallationPlan(
        repository.id,
        selections,
        repository.integrations,
        repository.policy,
        repository.observations,
        repository.proposals,
        repository.provenance,
    )


def resolve_request(repository: RepositoryInput, request: RequestInput) -> WorkflowPlan:
    """Add request requirements without changing the repository or enabling packs.

    Repository controls are always included. This is a requirements foundation,
    not the later intent/impact-based workflow chooser or conformance engine.
    """
    installation = resolve_repository(repository)
    request = deepcopy(request)
    available = {c.id: c for c in installation.selections.capabilities}
    decisions = list(installation.selections.unresolved)
    for capability in request.required_capabilities:
        if capability.id not in available:
            decisions.append(
                _decision(
                    "unavailable-capability",
                    (f"request:{request.id}", capability.id),
                    f"Request requires {capability.id}; repository setup must resolve it first.",
                    capability.reasons,
                )
            )
        else:
            existing = available[capability.id]
            # A request adds constraints/reasons to the configured capability;
            # omitting a dependency in a request cannot erase the existing one.
            available[capability.id] = replace(
                existing,
                reasons=tuple(dict.fromkeys(existing.reasons + capability.reasons)),
                requires=tuple(dict.fromkeys(existing.requires + capability.requires)),
                conflicts=tuple(dict.fromkeys(existing.conflicts + capability.conflicts)),
            )
    selections = _resolve(
        tuple(available.values()),
        installation.selections.artifacts + request.artifacts,
        installation.selections.checks + request.checks,
        tuple(decisions),
    )
    return WorkflowPlan(request.id, request.source, installation.identity, selections)
