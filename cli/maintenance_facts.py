# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Translate existing observations into independent maintenance recommendations."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .check_models import CheckOutcome, Evidence, Execution, Finding, State
from .release_metadata import timestamp
from .schema_validation import canonical_json, content_digest


@dataclass(frozen=True)
class Dimension:
    id: str
    outcome: CheckOutcome
    recommendations: tuple[dict, ...]
    required: bool


def evidence(source, digest, method="maintenance-observation", scope=(".",)):
    return asdict(
        Evidence(
            source,
            scope,
            method,
            "local-check",
            digest,
            (
                "Local consistency evidence does not authenticate policy, publishers or enforcement.",
            ),
        )
    )


def recommendation(
    dimension,
    code,
    action,
    reason,
    *,
    evidence,
    component=None,
    target_version=None,
    resources=(),
    controls=(),
    scope=(".",),
    required=False,
    source_policy=None,
    uncertainty=(),
    customizations=(),
    prerequisites=(),
    operation=None,
    severity="warning",
):
    identity = (dimension, code, component, target_version, sorted(resources), sorted(scope))
    identifier = "maintenance:" + content_digest(canonical_json(identity).encode())
    return {
        "id": identifier,
        "dimension": dimension,
        "action": action,
        "reason": reason,
        "component": component,
        "target_version": target_version,
        "scope": sorted(set(scope)),
        "resources": sorted(set(resources)),
        "controls": sorted(set(controls)),
        "required": required,
        "source_policy": source_policy if required else None,
        "urgency": "required"
        if required
        else "informational"
        if severity == "info"
        else "recommended",
        "severity": severity,
        "evidence": list(evidence),
        "uncertainty": list(uncertainty),
        "customizations": sorted(set(customizations)),
        "prerequisites": list(
            prerequisites
            or ("Review the cited evidence and accepted policy before authorizing changes.",)
        ),
        "preview": {"operation": operation or action, "assessment_required": True},
        "finding_ids": [],
    }


def dimension(identifier, state, summary, recommendations, observations, *, required=False):
    findings = tuple(
        Finding(
            r["id"],
            r["severity"],
            "maintenance",
            r["reason"],
            r["action"],
            r["resources"][0] if r["resources"] else None,
            tuple(
                Evidence(
                    e["source"],
                    tuple(e["scope"]),
                    e["method"],
                    e["origin"],
                    e["digest"],
                    tuple(e["limitations"]),
                )
                for e in r["evidence"]
            ),
        )
        for r in recommendations
    )
    return Dimension(
        identifier,
        CheckOutcome(
            state,
            Execution.EXECUTED,
            summary,
            findings,
            tuple(
                Evidence(
                    e["source"],
                    tuple(e["scope"]),
                    e["method"],
                    e["origin"],
                    e["digest"],
                    tuple(e["limitations"]),
                )
                for e in observations
            ),
        ),
        tuple(recommendations),
        required or any(r["required"] for r in recommendations),
    )


def release_dimension(inventory, profile):
    items, state = [], State.PASS
    observed = [evidence("maintenance-inventory", inventory["digest"], "release-policy-comparison")]
    if not inventory["candidates"]:
        state = State.UNKNOWN
        items.append(
            recommendation(
                "releases",
                "unavailable",
                "inspect-metadata",
                "No approved release comparison is available.",
                evidence=observed,
                uncertainty=("No latest-release conclusion can be drawn.",),
                operation="metadata-review",
            )
        )
    for candidate in inventory["candidates"]:
        component = candidate["component"]
        source = next(m for m in inventory["metadata"] if m["source_id"] == candidate["source_id"])
        proof = [
            evidence(
                candidate["source_url"],
                content_digest(canonical_json(source).encode()),
                "approved-release-policy-comparison",
            )
        ]
        outside = candidate["current_policy_state"] == "outside-policy"
        verified_current = component == "govkit" or inventory["lock_verification"] == "verified"
        required_failure = outside and verified_current
        if required_failure:
            state = State.FAIL
        elif (
            not verified_current
            or candidate["freshness"] != "fresh"
            or candidate["current_policy_state"] == "unknown"
        ):
            if state is not State.FAIL:
                state = State.UNKNOWN
            items.append(
                recommendation(
                    "releases",
                    "unknown:" + component,
                    "inspect-metadata",
                    f"Release freshness or installed compatibility for {component} is unverified.",
                    component=component,
                    evidence=proof,
                    uncertainty=(
                        f"Freshness: {candidate['freshness']}; lookup: {candidate['lookup_status']}; installed policy: {candidate['current_policy_state']}.",
                    ),
                    operation="metadata-review",
                )
            )
        target = candidate["selected_target"]
        if target is not None or outside:
            action = (
                ("upgrade-cli" if component == "govkit" else "upgrade-pack")
                if target
                else "review-policy"
            )
            items.append(
                recommendation(
                    "releases",
                    "candidate:" + component,
                    action,
                    f"The recorded {component} version is outside accepted version policy; verify installed facts before changing versions."
                    if outside
                    else f"A compatible {component} update is available; upgrading is optional.",
                    component=component,
                    target_version=target,
                    evidence=proof,
                    required=required_failure,
                    source_policy=".govkit/profile.yaml#maintenance/constraints",
                    severity="error" if required_failure else "info",
                    resources=tuple(
                        r["path"] for r in inventory["resources"] if r["owner"] == component
                    ),
                    controls=tuple(c.id for c in profile.repository.policy.required_checks)
                    if profile
                    else (),
                    customizations=tuple(
                        r["path"]
                        for r in inventory["resources"]
                        if r["owner"] == component and r["state"] == "modified"
                    ),
                    uncertainty=(
                        "Metadata is not publisher authentication or proof of the latest release.",
                        "Pack versions and ownership remain recorded claims until lock replay succeeds; the operation preview identifies replayable pack controls.",
                    ),
                    prerequisites=(
                        "Review compatible target and dependencies; supply an explicit local pack snapshot for pack operations.",
                    ),
                    operation="package-manager"
                    if action == "upgrade-cli"
                    else "govkit-pack-preview"
                    if action == "upgrade-pack"
                    else "policy-review",
                )
            )
            if state is State.PASS:
                state = State.WARN
    return dimension(
        "releases",
        state,
        "Release availability, compatibility and freshness remain separate facts.",
        items,
        observed,
    )


def resource_dimension(inventory, profile):
    observed = [
        evidence("maintenance-inventory", inventory["digest"], "bounded-resource-digest-comparison")
    ]
    required = bool(profile and profile.repository.capabilities)
    controls = tuple(c.id for c in profile.repository.policy.required_checks) if profile else ()
    items = []
    for resource in inventory["resources"]:
        if resource["state"] == "matching":
            continue
        items.append(
            recommendation(
                "resources",
                resource["path"],
                resource["action"],
                f"Recorded resource {resource['path']} is {resource['state']}.",
                component=resource["owner"],
                resources=(resource["path"],),
                controls=controls,
                # Drift prevents full lock verification. Do not promote this
                # individual recorded ownership claim into accepted policy.
                required=False,
                severity="warning",
                evidence=[
                    evidence(
                        resource["path"],
                        resource["actual_digest"],
                        "bounded-resource-digest-comparison",
                    )
                ],
                customizations=(resource["path"],) if resource["state"] == "modified" else (),
                uncertainty=(
                    "Ownership and expected bytes remain recorded lock claims until replay succeeds.",
                ),
                prerequisites=(
                    "Revalidate the accepted profile and lock; preserve user edits in the existing pack preview/apply workflow.",
                ),
                operation="govkit-pack-preview",
            )
        )
    if inventory["lock_verification"] != "verified":
        action = (
            "migrate-legacy"
            if profile is None and inventory["recorded_install"]
            else "inspect-resources"
        )
        items.append(
            recommendation(
                "resources",
                "lock-unverified",
                action,
                "Installed resource ownership or synchronization is not fully verified.",
                required=required,
                source_policy=".govkit/profile.yaml#capabilities",
                controls=controls,
                evidence=observed,
                uncertainty=tuple(inventory["problems"]),
                operation="govkit-migrate-preview"
                if action == "migrate-legacy"
                else "govkit-pack-preview",
            )
        )
    state = (
        State.FAIL
        if any(r["severity"] == "error" for r in items)
        else State.UNKNOWN
        if inventory["lock_verification"] != "verified"
        else State.WARN
        if items
        else State.PASS
    )
    return dimension(
        "resources",
        state,
        "Actual managed bytes, ownership and customization observations.",
        items,
        observed,
        required=required,
    )


def fit_dimension(discovery, inventory, error=None):
    observed = [
        evidence(
            "repository-discovery",
            content_digest(canonical_json(discovery).encode()) if discovery else None,
            "bounded-discovery",
        )
    ]
    if discovery is None:
        item = recommendation(
            "repository-fit",
            "unavailable",
            "review-policy",
            "Repository fit evidence is unavailable.",
            evidence=observed,
            uncertainty=(error or "Discovery unavailable",),
            operation="govkit-discover",
        )
        return dimension(
            "repository-fit", State.UNKNOWN, "Repository fit is unknown.", [item], observed
        )
    # Consume I05's canonical outcomes rather than infer violations from observations.
    from .discovery import DiscoveryReport

    outcome = DiscoveryReport(discovery).maintenance_outcome()
    decisions = {d["id"]: d for d in discovery["review"]}
    items = []
    for finding in outcome.findings:
        decision = decisions.get(finding.code)
        capability = (
            finding.code.removeprefix("capability:")
            if finding.code.startswith("capability:")
            else None
        )
        items.append(
            recommendation(
                "repository-fit",
                finding.code + ":" + (finding.location or ""),
                "review-capability" if capability else "review-policy",
                finding.message,
                component=capability,
                evidence=[asdict(e) for e in finding.evidence] or observed,
                scope=(decision["scope"],) if decision else (".",),
                resources=tuple(decision["sources"])
                if decision
                else (finding.location,)
                if finding.location
                else (),
                controls=tuple(decision["affects"]) if decision else (),
                uncertainty=(
                    "Observations are neither accepted policy nor conformance violations.",
                ),
                operation="govkit-discover",
            )
        )
    state = (
        State.UNKNOWN
        if not discovery["coverage"]["complete"]
        else State.WARN
        if items
        else State.PASS
    )
    return dimension("repository-fit", state, outcome.summary, items, observed)


def ci_dimension(inventory, profile, report, as_of):
    observed = [
        evidence(
            "ci-check-results",
            content_digest(report.to_json().encode()) if report else None,
            "canonical-check-report-comparison",
        )
    ]
    identifiers = set()
    if profile:
        identifiers.update(
            c.id
            for c in profile.repository.policy.required_checks
            if c.id.startswith("ci:") or c.id == "migration:ci-enforcement"
        )
        if profile.document.get("integrations", {}).get("ci") not in (None, "none"):
            identifiers.add("ci:integration")
    if profile is not None and not identifiers:
        return dimension(
            "ci",
            State.NOT_APPLICABLE,
            "No CI integration is required by this accepted profile.",
            [],
            observed,
        )
    issues = []
    if profile is None:
        issues.append("Accepted CI requirements are unavailable.")
    if report is None:
        issues.append(
            "No CI provider check report was supplied; workflow presence is not enforcement."
        )
    else:
        identity = report.identity
        if not inventory["identity"]["git_complete"] or not inventory["identity"]["revision"]:
            issues.append(
                "Complete Git revision and dirty-tree identity are required for CI evidence."
            )
        if identity.repository != inventory["repository"] or any(
            getattr(identity, key) != inventory["identity"][key]
            for key in (
                "revision",
                "dirty_digest",
                "profile_digest",
                "resolution_digest",
                "pack_lock_digest",
            )
        ):
            issues.append("CI report identity does not match the assessed inputs.")
        try:
            age = (timestamp(as_of) - timestamp(identity.observed_at)).total_seconds() / 3600
            max_age = profile.maintenance.assessment_max_age_hours if profile else None
            if max_age is None or age < 0 or age > max_age:
                issues.append(
                    "CI evidence freshness is unknown or outside accepted assessment age."
                )
        except ValueError:
            issues.append("CI evidence needs explicit valid observation and assessment times.")
    items, state = [], State.PASS
    results = {r.spec.id: r for r in report.results} if report else {}
    for identifier in sorted(identifiers or {"ci:integration"}):
        result = results.get(identifier)
        uncertainty = list(issues)
        if result is None:
            uncertainty.append("Required integration has no check result.")
        elif "." not in result.spec.scope:
            uncertainty.append("CI result does not cover the required repository scope.")
        outcome = result.outcome if result and not uncertainty else None
        if outcome and outcome.state is State.PASS:
            continue
        failed = bool(outcome and outcome.state is State.FAIL)
        if failed:
            state = State.FAIL
        elif state is not State.FAIL:
            state = State.UNKNOWN
        proof = [asdict(e) for e in outcome.evidence] if outcome else []
        proof += [asdict(e) for f in outcome.findings for e in f.evidence] if outcome else []
        items.append(
            recommendation(
                "ci",
                identifier,
                "repair-ci",
                outcome.summary if outcome else "Required CI integration evidence is unverified.",
                controls=(identifier,),
                required=bool(profile and identifiers),
                source_policy=".govkit/profile.yaml#integrations/ci"
                if identifier == "ci:integration"
                and profile
                and profile.document.get("integrations", {}).get("ci")
                else ".govkit/profile.yaml#policy/required_checks",
                evidence=proof or observed,
                uncertainty=uncertainty
                + [
                    "Result consistency does not authenticate the provider; I10 owns provider-specific collection and repair."
                ],
                severity="error" if failed else "warning",
                operation="ci-integration-review",
            )
        )
    return dimension(
        "ci",
        state,
        "CI health reuses supplied canonical check outcomes; no provider is queried.",
        items,
        observed,
        required=bool(profile and identifiers),
    )
