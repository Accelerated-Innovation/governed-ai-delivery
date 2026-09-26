# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Privacy-filtered projection of canonical maintenance snapshots; no assessment I/O."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from packaging.version import InvalidVersion, Version

from .check_models import CheckOutcome, CheckResult, CheckSpec, Execution, Identity, State
from .check_runner import CheckReport
from .maintenance import parse_assessment
from .profiles import parse_profile
from .release_metadata import timestamp
from .schema_validation import DocumentError, canonical_json, content_digest, validate_document

CAPABILITIES = {"application-governance", "gherkin-delivery", "llm-evaluation"}
DIMENSIONS = {"maintenance:" + v for v in ("releases", "resources", "repository-fit", "ci")}


def reference(kind: str, value: object) -> str | None:
    """Stable pseudonymous join key; this is not anonymization or authentication."""
    return (
        None if value is None else "ref:" + content_digest(canonical_json([kind, value]).encode())
    )


def _refs(kind, values):
    return [reference(kind, v) for v in values]


def _version(value):
    if value is None:
        return None
    try:
        # Local version labels may contain internal names. Keep a reference to the
        # exact value but export only the normalized public version as display text.
        display = Version(value).public
        if len(display) > 80:
            display = None
    except (InvalidVersion, TypeError):
        display = None
    return {"display": display, "ref": reference("version", value)}


def _time(value):
    if value is None:
        return None
    try:
        return timestamp(value).isoformat()
    except ValueError:
        return None


def _capabilities(values):
    return sorted(
        (
            {"ref": reference("capability", v), "label": v if v in CAPABILITIES else "custom"}
            for v in set(values)
        ),
        key=lambda v: v["ref"],
    )


def _architecture(profile, discovery):
    policy = profile.get("policy", {})
    return {
        "observed": [
            {
                "source_ref": reference("source", o["source"]),
                "scope_ref": reference("scope", o["scope"]),
                **{k: o[k] for k in ("category", "status", "confidence")},
            }
            for o in discovery.get("observations", [])
        ],
        "accepted_contracts": [
            {
                "source_ref": reference("source", c["source"]["reference"]),
                "scope_refs": _refs("scope", c["scope"]),
            }
            for c in policy.get("contracts", [])
        ],
        "transitions": [
            {
                "ref": reference("transition", t["id"]),
                "mode": t["mode"],
                "applies_to": t["applies_to"],
                "source_ref": reference("source", t["source"]["reference"]),
                "scope_refs": _refs("scope", t["scope"]),
                "current_refs": _refs("contract", t["current"]),
                "target_refs": _refs("contract", t["target"]),
                "exceptions": [
                    {
                        "ref": reference("exception", e["id"]),
                        "source_ref": reference("source", e["source"]["reference"]),
                        "scope_refs": _refs("scope", e["scope"]),
                        "expires_at": e["expires_at"],
                    }
                    for e in t.get("exceptions", [])
                ],
            }
            for t in policy.get("transitions", [])
        ],
    }


def _candidate(c, index):
    return {
        "component_ref": reference("component", c["component"]),
        "source_ref": reference("source", c["source_url"]),
        "channel_ref": reference("channel", c["channel"]),
        "compatibility_ref": reference("compatibility", c["compatibility"]),
        **{k: _version(c[k]) for k in ("installed", "pin", "newest_known", "selected_target")},
        "compatible_candidates": [_version(v) for v in c["compatible_candidates"]],
        "excluded": [
            {
                "version": _version(e["version"]),
                "reasons": sorted(
                    set("dependency" if r.startswith("dependency:") else r for r in e["reasons"])
                ),
                "reason_refs": _refs("exclusion", e["reasons"]),
            }
            for e in c["excluded"]
        ],
        **{
            k: c[k]
            for k in (
                "current_policy_state",
                "freshness",
                "age_hours",
                "lookup_status",
                "latest_verified",
            )
        },
        **{k: _time(c[k]) for k in ("as_of", "retrieved_at")},
        "local_ref": f"/inventory/candidates/{index}",
    }


def _recommendation(r, index):
    return {
        **{k: r[k] for k in ("id", "dimension", "action", "required", "urgency", "severity")},
        "component_ref": reference("component", r["component"]),
        "target_version": _version(r["target_version"]),
        "reason_ref": reference("reason", r["reason"]),
        "source_policy_ref": reference("source", r["source_policy"]),
        "scope_refs": _refs("scope", r["scope"]),
        "resource_refs": _refs("resource", r["resources"]),
        "control_refs": _refs("control", r["controls"]),
        "customization_refs": _refs("resource", r["customizations"]),
        "prerequisite_refs": _refs("prerequisite", r["prerequisites"]),
        "uncertainty_refs": _refs("uncertainty", r["uncertainty"]),
        "evidence_refs": _refs("evidence", r["evidence"]),
        "finding_refs": _refs("finding", r["finding_ids"]),
        "preview_operation": r["preview"]["operation"],
        "local_ref": f"/recommendations/{index}",
    }


@dataclass(frozen=True)
class PostureReport:
    _document: dict

    @property
    def document(self) -> dict:
        return deepcopy(self._document)

    def to_json(self) -> str:
        return canonical_json(self._document)


def configured_controls(profile: dict) -> list[dict]:
    """Declared controls are distinct from recorded executions in either snapshot."""
    requirements = [
        {
            "ref": reference("control", c["id"]),
            "applies_when": "repository",
            "execution": "not-assessed",
        }
        for c in profile.get("policy", {}).get("required_checks", [])
    ]
    requirements.extend(
        {"ref": reference("control", c), "applies_when": "workflow", "execution": "not-assessed"}
        for rule in profile.get("policy", {}).get("workflows", [])
        for c in rule.get("additional_checks", [])
    )
    return sorted(requirements, key=canonical_json)


def export_posture(assessment: dict) -> PostureReport:
    """Replay canonical facts and project an allowlist; never inspect/fetch/execute."""
    source = parse_assessment(assessment).document
    inventory = source["inventory"]
    profile = source["inputs"]["profile"] or {}
    discovery = source["discovery"] or {}
    checks = source["checks"]
    document = {
        "schema_version": source["schema_version"],
        "kind": "posture-export",
        "repository_ref": reference("repository", source["repository"]),
        "assessment_ref": "ref:" + source["digest"],
        "as_of": _time(source["as_of"]),
        "identity": {
            k + "_ref": reference("identity:" + k, v)
            for k, v in source["identity"].items()
            if k != "git_complete"
        },
        "coverage": {
            "profile": "present" if profile else "missing",
            "git_complete": source["identity"]["git_complete"],
            "discovery_complete": discovery.get("coverage", {}).get("complete", False),
            "change_results": "not-supplied",
            "controls": "maintenance-dimensions-only",
            "origin": "unauthenticated-snapshot",
        },
        "capabilities": {
            "configured": _capabilities(c["id"] for c in profile.get("capabilities", [])),
            "required": _capabilities(
                parse_profile(profile).required_capabilities if profile else []
            ),
            "recorded": _capabilities(c for p in inventory["locked_packs"] for c in p["provides"]),
            "lock_verification": inventory["lock_verification"],
        },
        "configured_controls": configured_controls(profile),
        "architecture": _architecture(profile, discovery),
        "versions": {
            **{
                k: _version(inventory[k])
                for k in ("running_cli", "recorded_install", "resolved_govkit")
            },
            "locked": [
                {
                    "component_ref": reference("component", p["id"]),
                    "version": _version(p["version"]),
                }
                for p in inventory["locked_packs"]
            ],
            "candidates": [_candidate(c, i) for i, c in enumerate(inventory["candidates"])],
            "metadata": [
                {
                    "source_ref": reference("source", m["source_url"]),
                    "lookup_status": m["lookup_status"],
                    **{k: _time(m[k]) for k in ("as_of", "retrieved_at")},
                }
                for m in inventory["metadata"]
            ],
        },
        "resources": [
            {
                "ref": reference("resource", r["path"]),
                "component_ref": reference("component", r["owner"]),
                "state": r["state"],
                "action": r["action"],
                "local_ref": f"/inventory/resources/{i}",
            }
            for i, r in enumerate(inventory["resources"])
        ],
        "maintenance": {
            "dimensions": [
                {
                    **{k: d[k] for k in ("id", "state", "execution", "required")},
                    "finding_refs": _refs("finding", [f["id"] for f in d["findings"]]),
                }
                for d in checks["results"]
            ],
            "summary": checks["summary"],
            "state": checks["state"],
            "exit_code": checks["exit_code"],
            "recommendations": [
                _recommendation(r, i) for i, r in enumerate(source["recommendations"])
            ],
        },
    }
    document["digest"] = content_digest(canonical_json(document).encode())
    return parse_posture(document)


def parse_posture(document: dict) -> PostureReport:
    """Validate export consistency; a schema/digest never authenticates its origin."""
    document = deepcopy(document)
    validate_document(document, "posture-export")
    if (
        content_digest(
            canonical_json({k: v for k, v in document.items() if k != "digest"}).encode()
        )
        != document["digest"]
    ):
        raise DocumentError("Invalid posture digest")
    maintenance = document["maintenance"]
    dimensions = maintenance["dimensions"]
    if len(dimensions) != 4 or {d["id"] for d in dimensions} != DIMENSIONS:
        raise DocumentError("Invalid posture dimensions")
    if any(
        (d["state"] == "pass" and d["execution"] != "executed")
        or (d["execution"] == "error" and d["state"] != "unknown")
        for d in dimensions
    ):
        raise DocumentError("Invalid posture execution state")
    replay = CheckReport(
        Identity(document["repository_ref"]),
        tuple(
            CheckResult(
                CheckSpec(d["id"], d["required"], "", "", ()),
                CheckOutcome(State(d["state"]), Execution(d["execution"]), ""),
            )
            for d in dimensions
        ),
        "",
    )
    if replay.summary != maintenance["summary"]:
        raise DocumentError("Invalid posture summary")
    if replay.state.value != maintenance["state"] or replay.exit_code != maintenance["exit_code"]:
        raise DocumentError("Invalid posture aggregate")
    return PostureReport(document)


def _version_text(value):
    if value is None:
        return "unknown"
    return f"{value['display'] or 'undisclosed'} ({value['ref']})"


def render_posture(report: PostureReport) -> str:
    """Render the export, never unfiltered source summaries or evidence strings."""
    d = parse_posture(report.document).document
    lines = [
        f"Maintenance posture: {d['repository_ref']}",
        f"Assessed: {d['as_of'] or 'unknown'}",
        f"Source: {d['assessment_ref']}",
        "Snapshot only; origin is unauthenticated. Change controls were not assessed.",
        "Versions (public display; exact versions retained by reference):",
    ]
    for key in ("running_cli", "recorded_install", "resolved_govkit"):
        lines.append(f"  {key}: {_version_text(d['versions'][key])}")
    for locked in d["versions"]["locked"]:
        lines.append(f"  Locked {locked['component_ref']}: {_version_text(locked['version'])}")
    for candidate in d["versions"]["candidates"]:
        lines.extend(
            [
                f"  Component {candidate['component_ref']}: policy={candidate['current_policy_state']}, freshness={candidate['freshness']}",
                f"    Installed: {_version_text(candidate['installed'])}; selected: {_version_text(candidate['selected_target'])}",
                f"    Newest known: {_version_text(candidate['newest_known'])}; pin: {_version_text(candidate['pin'])}",
                f"    Compatibility: {candidate['compatibility_ref'] or 'unspecified'}; local details: {candidate['local_ref']}",
            ]
        )
        lines.extend(
            "    Compatible: " + _version_text(v) for v in candidate["compatible_candidates"]
        )
        lines.extend(
            f"    Excluded {_version_text(e['version'])}: {', '.join(e['reasons'])}"
            for e in candidate["excluded"]
        )
    for metadata in d["versions"]["metadata"]:
        lines.append(
            f"  Source {metadata['source_ref']}: {metadata['lookup_status']}; as of {metadata['as_of'] or 'unknown'}; retrieved {metadata['retrieved_at'] or 'unknown'}"
        )
    lines.append(f"Capabilities (lock {d['capabilities']['lock_verification']}):")
    for category in ("configured", "required", "recorded"):
        labels = [f"{c['label']} ({c['ref']})" for c in d["capabilities"][category]]
        lines.append(f"  {category}: " + (", ".join(labels) or "none recorded"))
    lines.append("Configured controls (not executed by this report):")
    lines.extend(
        f"  {c['ref']}: {c['applies_when']}, {c['execution']}" for c in d["configured_controls"]
    )
    lines.append("Architecture:")
    lines.extend(
        f"  Observed {o['category']}: {o['status']}, confidence={o['confidence']}, source={o['source_ref']}"
        for o in d["architecture"]["observed"]
    )
    lines.extend(
        f"  Accepted contract: {c['source_ref']}" for c in d["architecture"]["accepted_contracts"]
    )
    for transition in d["architecture"]["transitions"]:
        lines.append(
            f"  Transition {transition['ref']}: {transition['mode']} for {transition['applies_to']}"
        )
        lines.extend(
            f"    Exception {e['ref']}: expires {e['expires_at'] or 'unspecified'}"
            for e in transition["exceptions"]
        )
    lines.append("Resources:")
    lines.extend(
        f"  {r['ref']}: {r['state']}; {r['action']}; {r['local_ref']}" for r in d["resources"]
    )
    lines.append(
        f"Maintenance: {d['maintenance']['state']} (canonical exit {d['maintenance']['exit_code']})"
    )
    for dim in d["maintenance"]["dimensions"]:
        lines.append(
            f"  {dim['id']}: {dim['state']} ({dim['execution']}, required={dim['required']})"
        )
        lines.extend("    Finding: " + ref for ref in dim["finding_refs"])
    lines.append("Recommendations (no changes authorized):")
    for r in d["maintenance"]["recommendations"]:
        lines.extend(
            [
                f"  {r['id']} {r['action']} ({r['urgency']}, {r['severity']})",
                f"    Component: {r['component_ref'] or 'repository'}; target: {_version_text(r['target_version'])}",
                f"    Reason: {r['reason_ref']}; policy: {r['source_policy_ref'] or 'advisory'}",
            ]
        )
        for key in (
            "resource_refs",
            "control_refs",
            "customization_refs",
            "evidence_refs",
            "finding_refs",
        ):
            if r[key]:
                lines.append(f"    {key}: " + ", ".join(r[key]))
        lines.append(
            f"    Preview: {r['preview_operation']}; inspect {r['local_ref']} in the local source assessment for prerequisites and uncertainty."
        )
    return "\n".join(lines)
