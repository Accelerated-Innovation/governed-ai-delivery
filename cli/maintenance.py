# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Canonical offline maintenance assessment, replay and post-operation verification."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from .check_models import CheckResult, CheckSpec, Identity
from .check_runner import CheckReport, normalize, parse_report
from .discovery import discover
from .maintenance_facts import ci_dimension, fit_dimension, release_dimension, resource_dimension
from .maintenance_inventory import inventory_repository, read_bounded, release_facts
from .observation_policy import parse_observation
from .pack_loading import contained_file
from .profiles import parse_profile
from .schema_validation import (
    DocumentError,
    canonical_json,
    content_digest,
    parse_document,
    validate_document,
)

MAX_ASSESSMENT_BYTES = 16 * 1024 * 1024


def _digest(document):
    return content_digest(canonical_json(document).encode())


@dataclass(frozen=True)
class MaintenanceAssessment:
    _document: dict

    @property
    def document(self):
        return deepcopy(self._document)

    @property
    def digest(self):
        return self._document["digest"]

    def to_json(self):
        return canonical_json(self._document)


def parse_assessment(document):
    document = deepcopy(document)
    if len(canonical_json(document).encode()) > MAX_ASSESSMENT_BYTES:
        raise DocumentError("Maintenance assessment exceeds size limit")
    validate_document(document, "maintenance-assessment")
    if _digest({k: v for k, v in document.items() if k != "digest"}) != document["digest"]:
        raise DocumentError("Invalid maintenance assessment digest")
    inventory = document["inventory"]
    validate_document(inventory, "maintenance-inventory")
    if inventory["schema_version"] != document["schema_version"]:
        raise DocumentError("Assessment and inventory versions differ")
    if document["schema_version"] == 2:
        budget = parse_observation(inventory["observation"])
        if budget.digest != inventory["identity"]["observation_digest"] or (
            budget.source_state == "unavailable" and inventory["identity"]["git_complete"]
        ):
            raise DocumentError("Inventory observation identity is inconsistent")
    if _digest({k: v for k, v in inventory.items() if k != "digest"}) != inventory["digest"]:
        raise DocumentError("Invalid maintenance inventory digest")
    if document["discovery"] is not None:
        validate_document(document["discovery"], "discovery")
    if document["inputs"]["baseline"] is not None:
        validate_document(document["inputs"]["baseline"], "discovery")
    if document["inputs"]["ci_report"] is not None:
        parse_report(document["inputs"]["ci_report"])
    profile = (
        parse_profile(document["inputs"]["profile"])
        if document["inputs"]["profile"] is not None
        else None
    )
    if (profile.digest if profile else None) != inventory["identity"]["profile_digest"]:
        raise DocumentError("Assessment profile identity does not match its inventory")
    metadata, candidates, _ = _replay_releases(document, profile, document["as_of"])
    if metadata != inventory["metadata"] or candidates != inventory["candidates"]:
        raise DocumentError("Assessment release facts do not match their saved metadata inputs")
    provider = (
        parse_report(document["inputs"]["ci_report"])
        if document["inputs"]["ci_report"] is not None
        else None
    )
    checks, recommendations = _compose_checks(
        inventory, profile, document["discovery"], provider, document["as_of"]
    )
    if canonical_json(checks) != canonical_json(document["checks"]) or canonical_json(
        recommendations
    ) != canonical_json(document["recommendations"]):
        raise DocumentError(
            "Assessment derived checks or recommendations do not match their evidence"
        )
    expected_identity = {
        **inventory["identity"],
        "inventory_digest": inventory["digest"],
        "discovery_digest": _digest(document["discovery"])
        if document["discovery"] is not None
        else None,
        "baseline_digest": _digest(document["inputs"]["baseline"])
        if document["inputs"]["baseline"] is not None
        else None,
        "ci_report_digest": _digest(document["inputs"]["ci_report"]) if provider else None,
    }
    if document["identity"] != expected_identity or any(
        document[k] != inventory[k] for k in ("target", "repository", "as_of")
    ):
        raise DocumentError("Assessment identity does not match its inputs")
    return MaintenanceAssessment(document)


def _replay_releases(document, profile, as_of):
    inventory = document["inventory"]
    installed = {p["id"]: p["version"] for p in inventory["locked_packs"]}
    installed["govkit"] = inventory["running_cli"]
    return release_facts(
        profile,
        document["inputs"]["metadata"],
        installed=installed,
        running_govkit=inventory["running_cli"],
        python_version=inventory["python_version"],
        as_of=as_of,
    )


def validate_freshness(document, *, as_of):
    """Reject changed time-dependent advice while preserving a reviewed snapshot's digest.

    Input identity is re-observed separately by the operation owner. This pure check
    uses the same release and CI evaluators at the operation time; elapsed time alone
    need not invalidate a proposal while its evidence remains within accepted ages.
    """
    prior = parse_assessment(document).document
    profile = parse_profile(prior["inputs"]["profile"]) if prior["inputs"]["profile"] else None
    provider = parse_report(prior["inputs"]["ci_report"]) if prior["inputs"]["ci_report"] else None
    inventory = prior["inventory"]
    _, candidates, _ = _replay_releases(prior, profile, as_of)
    # Numeric age advances within the same accepted window. A changed freshness
    # classification must invalidate the proposal even if another policy failure
    # leaves the dimension's overall state and recommendations unchanged.
    previous = [{k: v for k, v in c.items() if k != "age_hours"} for c in inventory["candidates"]]
    current = [{k: v for k, v in c.items() if k != "age_hours"} for c in candidates]
    if previous != current or ci_dimension(
        inventory, profile, provider, prior["as_of"]
    ) != ci_dimension(inventory, profile, provider, as_of):
        raise DocumentError(
            "Stale maintenance evidence: freshness changed; regenerate the assessment and proposal"
        )


def read_assessment(path: Path):
    with path.open("rb") as stream:
        content = stream.read(MAX_ASSESSMENT_BYTES + 1)
    if len(content) > MAX_ASSESSMENT_BYTES:
        raise DocumentError("Maintenance assessment exceeds size limit")
    return parse_assessment(parse_document(content))


def _discover(target, baseline):
    try:
        return discover(target, baseline=baseline).document, None
    except (OSError, ValueError):
        return None, "Discovery or its baseline could not be replayed; review the local inputs."


def _compose_checks(inventory, profile, discovery, provider, as_of):
    facts = (
        release_dimension(inventory, profile),
        resource_dimension(inventory, profile),
        fit_dimension(
            discovery,
            inventory,
            "Discovery or its baseline could not be replayed; review the local inputs."
            if discovery is None
            else None,
        ),
        ci_dimension(inventory, profile, provider, as_of),
    )
    identity = Identity(
        inventory["repository"],
        revision=inventory["identity"]["revision"],
        dirty_digest=inventory["identity"]["dirty_digest"],
        profile_digest=inventory["identity"]["profile_digest"],
        resolution_digest=inventory["identity"]["resolution_digest"],
        pack_lock_digest=inventory["identity"]["pack_lock_digest"],
        observed_at=as_of,
    )
    checks = CheckReport(
        identity,
        tuple(
            CheckResult(
                CheckSpec(
                    "maintenance:" + fact.id,
                    fact.required,
                    "Assess this maintenance dimension independently",
                    ".govkit/profile.yaml",
                    (".",),
                ),
                normalize(fact.outcome),
            )
            for fact in facts
        ),
        inventory["running_cli"],
    ).to_document()
    checks["kind"] = "maintenance-dimensions"
    checks["limitations"] = [
        "Only the four named maintenance dimensions and their bounded evidence were assessed.",
        "These normalized observations are not change conformance or authenticated enforcement evidence.",
    ]
    recommendations = []
    for fact, result in zip(facts, checks["results"], strict=True):
        for item in fact.recommendations:
            item = deepcopy(item)
            item["finding_ids"] = [f["id"] for f in result["findings"] if f["code"] == item["id"]]
            recommendations.append(item)
    return checks, sorted(recommendations, key=lambda r: r["id"])


def assess_repository(target: Path, *, as_of=None, metadata=(), baseline=None, ci_report=None):
    """Observe facts without executing controls, fetching releases or changing policy.

    Time and provider records are explicit inputs. This checks snapshot consistency,
    not authenticity, and does not make concurrent reads a filesystem transaction.
    """
    target = target.absolute()
    baseline = deepcopy(baseline)
    metadata = deepcopy(tuple(metadata))
    if baseline is not None:
        validate_document(baseline, "discovery")
    provider = parse_report(deepcopy(ci_report)) if ci_report is not None else None
    inventory = inventory_repository(target, as_of=as_of, metadata=metadata).document
    profile = None
    if inventory["identity"]["profile_digest"] is not None:
        profile = parse_profile(
            parse_document(read_bounded(contained_file(target, ".govkit/profile.yaml")))
        )
        if profile.digest != inventory["identity"]["profile_digest"]:
            raise DocumentError("Inputs changed during maintenance assessment")
    discovery, discovery_error = _discover(target, baseline)
    if (
        discovery is not None
        and discovery["profile_digest"] != inventory["identity"]["profile_digest"]
    ):
        raise DocumentError("Inputs changed during maintenance discovery")
    checks, recommendations = _compose_checks(inventory, profile, discovery, provider, as_of)
    repeated = inventory_repository(target, as_of=as_of, metadata=metadata)
    if repeated.digest != inventory["digest"] or _discover(target, baseline) != (
        discovery,
        discovery_error,
    ):
        raise DocumentError(
            "Inputs changed during maintenance assessment; retry on a quiescent target"
        )
    document = {
        "schema_version": 2,
        "kind": "maintenance-assessment",
        "target": str(target),
        "repository": inventory["repository"],
        "as_of": as_of,
        "identity": {
            **inventory["identity"],
            "inventory_digest": inventory["digest"],
            "discovery_digest": _digest(discovery) if discovery else None,
            "baseline_digest": _digest(baseline) if baseline is not None else None,
            "ci_report_digest": _digest(ci_report) if ci_report is not None else None,
        },
        "inputs": {
            "baseline": baseline,
            "ci_report": provider.to_document() if provider else None,
            "metadata": list(metadata),
            "profile": profile.document if profile else None,
        },
        "inventory": inventory,
        "discovery": discovery,
        "checks": checks,
        "recommendations": sorted(recommendations, key=lambda r: r["id"]),
        "limitations": [
            "Four independent dimensions; an available update is not automatically required.",
            "Offline bounded observations, not approval, latest-release certification or authenticated CI enforcement.",
            "Only canonical ci:* and migration:ci-enforcement requirements are consumed; I10 owns provider collection and configuration.",
            "Git/discovery coverage is bounded and reads are not a concurrent transaction; unobserved changes may remain unknown.",
        ],
    }
    document = json.loads(canonical_json(document))
    document["digest"] = _digest(document)
    return parse_assessment(document)


def reassess(target, document, *, as_of=None, metadata=None, baseline=None, ci_report=None):
    prior = parse_assessment(document).document
    if str(target.absolute()) != prior["target"]:
        raise DocumentError("Assessment target does not match this repository path")
    return assess_repository(
        target,
        as_of=prior["as_of"] if as_of is None else as_of,
        metadata=prior["inputs"]["metadata"] if metadata is None else metadata,
        baseline=prior["inputs"]["baseline"] if baseline is None else baseline,
        ci_report=prior["inputs"]["ci_report"] if ci_report is None else ci_report,
    )


def compare_assessments(before, after):
    old, new = parse_assessment(before).document, parse_assessment(after).document
    if old["target"] != new["target"]:
        raise DocumentError("Cannot compare maintenance assessments of different repositories")
    prior = {r["id"]: r for r in old["recommendations"]}
    current = {r["id"] for r in new["recommendations"]}
    states = {r["id"].removeprefix("maintenance:"): r["state"] for r in new["checks"]["results"]}
    same_policy = (
        old["identity"]["profile_digest"] == new["identity"]["profile_digest"]
        and old["repository"] == new["repository"]
        and old["identity"].get("observation_digest") == new["identity"].get("observation_digest")
    )
    resolved = {
        identifier
        for identifier in prior.keys() - current
        if same_policy and states[prior[identifier]["dimension"]] == "pass"
    }
    return {
        "schema_version": 1,
        "kind": "maintenance-verification",
        "previous_digest": old["digest"],
        "assessment": new,
        "resolved": sorted(resolved),
        "remaining": sorted(prior.keys() & current),
        "unverified": sorted(prior.keys() - current - resolved),
        "new": sorted(current - prior.keys()),
        "limitations": [
            "A disappeared finding is resolved only when its dimension passes under unchanged accepted policy; otherwise it is unverified."
        ],
    }


def verify_assessment(
    target, document, *, as_of=None, metadata=None, baseline=None, ci_report=None
):
    return compare_assessments(
        document,
        reassess(
            target, document, as_of=as_of, metadata=metadata, baseline=baseline, ci_report=ci_report
        ).document,
    )


def render_assessment(report):
    document = report.document
    lines = [f"Maintenance assessment (read-only): {document['repository']}"]
    for result in document["checks"]["results"]:
        lines.append(f"  {result['id'].removeprefix('maintenance:')}: {result['state']}")
    for item in document["recommendations"]:
        target = f" -> {item['target_version']}" if item["target_version"] else ""
        lines.append(f"  {item['action']}{target} ({item['urgency']}): {item['reason']}")
        lines.append(f"    Recommendation: {item['id']}")
        for uncertainty in item["uncertainty"]:
            lines.append(f"    Uncertainty: {uncertainty}")
    return "\n".join(lines)
