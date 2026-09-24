# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Pure privacy-filtered projection of saved canonical change results."""

from copy import deepcopy

from .change_conformance import parse_change_report
from .check_models import CheckOutcome, CheckResult, CheckSpec, Execution, Identity, State
from .check_runner import CheckReport
from .posture import (
    PostureReport,
    _architecture,
    _capabilities,
    _refs,
    _time,
    _version,
    _version_text,
    configured_controls,
    reference,
)
from .profiles import parse_profile
from .schema_validation import DocumentError, canonical_json, content_digest, validate_document


def _evidence(e):
    return {
        "source_ref": reference("source", e["source"]),
        "scope_refs": _refs("scope", e["scope"]),
        "method_ref": reference("method", e["method"]),
        "origin": e["origin"],
        "digest_ref": reference("evidence-digest", e["digest"]),
        "limitation_refs": _refs("limitation", e["limitations"]),
    }


def _requirement(c):
    return {
        "ref": reference("control", c["id"]),
        "required": c["required"],
        "reason_ref": reference("reason", c["reason"]),
        "policy_ref": reference("source", c["source_policy"]),
        "scope_refs": _refs("scope", c["scope"]),
    }


def _preserves_requirement(planned, recorded):
    """Canonical merging may add scopes, but retains the planned specification."""
    return (
        recorded is not None
        and (not planned["required"] or recorded["required"])
        and planned["policy_ref"] == recorded["policy_ref"]
        and planned["reason_ref"] == recorded["reason_ref"]
        and set(planned["scope_refs"]) <= set(recorded["scope_refs"])
    )


def _control(c, index):
    return {
        **_requirement(c),
        # Only this exact bundled check has a public evaluation identity. Custom
        # names/prefixes cannot establish that an arbitrary check evaluates models.
        "label": "llm-exact-match" if c["id"] == "llm-exact-match" else "custom",
        "state": c["state"],
        "execution": c["execution"],
        "summary_ref": reference("summary", c["summary"]),
        "evidence": [_evidence(e) for e in c["evidence"]],
        "findings": [
            {
                "ref": reference("finding", f["id"]),
                "code_ref": reference("finding-code", f["code"]),
                "severity": f["severity"],
                "category_ref": reference("finding-category", f["category"]),
                "message_ref": reference("message", f["message"]),
                "action_ref": reference("action", f["suggested_action"]),
                "location_ref": reference("location", f["location"]),
                "evidence": [_evidence(e) for e in f["evidence"]],
            }
            for f in c["findings"]
        ],
        "local_ref": f"/checks/results/{index}",
    }


def export_change_posture(document: dict) -> PostureReport:
    """Replay canonical inputs/results; do not read repositories or execute checks."""
    source = parse_change_report(document).document
    plan, checks = source["plan"], source["checks"]
    profile, context = plan["inputs"]["profile"], plan["inputs"]["context"]
    if checks["identity"]["repository"] != profile["repository"]["id"]:
        raise DocumentError("Change repository does not match its replayed profile")
    identity = checks["identity"]
    result = {
        "schema_version": 1,
        "kind": "change-posture",
        "repository_ref": reference("repository", identity["repository"]),
        "report_ref": reference("change-report", source),
        "as_of": _time(identity["observed_at"]),
        "identity": {
            "revision_ref": reference("revision", identity["revision"]),
            "tree_ref": reference("change-tree", identity["dirty_digest"]),
            "profile_ref": reference("profile", identity["profile_digest"]),
            "request_plan_ref": reference("request-plan", identity["resolution_digest"]),
            "pack_lock_ref": reference("pack-lock", identity["pack_lock_digest"]),
            "change_ref": reference("change", identity["change_digest"]),
            "base_ref": reference("revision", source["change"]["base"]),
        },
        "running_cli": _version(checks["govkit_version"]),
        "coverage": {
            "origin": "unauthenticated-snapshot",
            "git_complete": source["change"]["complete"],
            "maintenance": "not-supplied",
            "discovery": "not-supplied",
            "provider_enforcement": "not-supplied",
            "controls": "recorded-change-results",
            "lock": "recorded" if context["lock_digest"] else "unknown",
        },
        "capabilities": {
            "configured": _capabilities(c["id"] for c in profile["capabilities"]),
            "repository_required": _capabilities(parse_profile(profile).required_capabilities),
            "recorded": _capabilities(context["capabilities"]),
            "change_required": _capabilities(plan["required_capabilities"]),
        },
        "configured_controls": configured_controls(profile),
        "architecture": _architecture(profile, {}),
        "workflow": {
            "selected": plan["workflow"],
            "request_ref": reference("request", plan["identity"]["request_digest"]),
            "scope_refs": _refs("scope", plan["scope"]),
            "impacts": plan["impacts"],
            "requirements": [_requirement(c) for c in plan["checks"]],
            "artifacts": [
                {
                    "ref": reference("artifact", a["id"]),
                    "reason_ref": reference("reason", a["reason"]),
                    "local_ref": f"/plan/artifacts/{i}",
                }
                for i, a in enumerate(plan["artifacts"])
            ],
            "decisions": [
                {
                    "ref": reference("decision", d),
                    "code_ref": reference("decision-code", d["code"]),
                    "blocking": d["blocking"],
                    "affected_refs": _refs("affected", d["affected"]),
                    "local_ref": f"/plan/decisions/{i}",
                }
                for i, d in enumerate(plan["decisions"])
            ],
            "reassessment": {
                "required": plan["reassessment"]["required"],
                "previous_plan_ref": reference(
                    "request-plan", plan["reassessment"]["previous_identity"]
                ),
                "reason_refs": _refs("reason", plan["reassessment"]["reasons"]),
                "added_control_refs": _refs("control", plan["reassessment"]["added_checks"]),
            },
        },
        "results": {
            "controls": [_control(c, i) for i, c in enumerate(checks["results"])],
            **{k: checks[k] for k in ("summary", "state", "exit_code")},
        },
    }
    result["digest"] = content_digest(canonical_json(result).encode())
    # Projection and saved-export replay enforce the same obligation/pointer
    # contract in the privacy-filtered representation.
    return parse_change_posture(result)


def parse_change_posture(document: dict) -> PostureReport:
    """Verify allowlist/aggregate consistency; never infer authenticity or freshness."""
    document = deepcopy(document)
    validate_document(document, "change-posture")
    if (
        content_digest(
            canonical_json({k: v for k, v in document.items() if k != "digest"}).encode()
        )
        != document["digest"]
    ):
        raise DocumentError("Invalid change posture digest")
    results = document["results"]
    controls = results["controls"]
    by_ref = {c["ref"]: c for c in controls}
    if len(by_ref) != len(controls):
        raise DocumentError("Duplicate change control")
    for records, prefix in (
        (controls, "/checks/results"),
        (document["workflow"]["artifacts"], "/plan/artifacts"),
        (document["workflow"]["decisions"], "/plan/decisions"),
    ):
        if any(r["local_ref"] != f"{prefix}/{i}" for i, r in enumerate(records)):
            raise DocumentError("Source pointer does not match its record")
    for c in controls:
        if (c["label"] == "llm-exact-match") != (
            c["ref"] == reference("control", "llm-exact-match")
        ):
            raise DocumentError("Invalid public control label")
        if c["state"] == "pass" and (
            c["execution"] != "executed"
            or not c["evidence"]
            or any(e["origin"] not in ("local-check", "tool-execution") for e in c["evidence"])
            or any(f["severity"] != "info" for f in c["findings"])
        ):
            raise DocumentError("Unverified change control pass")
        if (c["execution"] == "error" and c["state"] != "unknown") or (
            c["execution"] != "error"
            and c["state"] != "fail"
            and any(f["severity"] == "error" for f in c["findings"])
        ):
            raise DocumentError("Invalid change control outcome")
    requirements = document["workflow"]["requirements"]
    if len({r["ref"] for r in requirements}) != len(requirements) or any(
        not _preserves_requirement(r, by_ref.get(r["ref"])) for r in requirements
    ):
        raise DocumentError("Missing or weakened planned control")
    replay = CheckReport(
        Identity(document["repository_ref"]),
        tuple(
            CheckResult(
                CheckSpec(c["ref"], c["required"], "", "", ()),
                CheckOutcome(State(c["state"]), Execution(c["execution"]), ""),
            )
            for c in controls
        ),
        "",
    )
    if (results["summary"], results["state"], results["exit_code"]) != (
        replay.summary,
        replay.state.value,
        replay.exit_code,
    ):
        raise DocumentError("Invalid change posture aggregate")
    return PostureReport(document)


def render_change_posture(report: PostureReport) -> str:
    """Describe only the projected object; private explanations stay in the source."""
    doc = report.document
    lines = [
        f"Change posture: {doc['results']['state']} (canonical exit {doc['results']['exit_code']})",
        f"Repository: {doc['repository_ref']}",
        f"Observed: {doc['as_of'] or 'unknown'}; workflow: {doc['workflow']['selected']}",
        f"Recorded CLI: {_version_text(doc['running_cli'])}",
        "Recorded snapshot; not authenticated approval or current repository health.",
        "Maintenance, discovery and provider enforcement are not supplied.",
        "Change-required capabilities: "
        + ", ".join(
            c["label"] + " (" + c["ref"] + ")" for c in doc["capabilities"]["change_required"]
        ),
        "Configured declarations are distinct from the control results below.",
    ]
    for transition in doc["architecture"]["transitions"]:
        lines.append(
            f"  Transition {transition['ref']}: {transition['mode']}; {transition['applies_to']}"
        )
        for exception in transition["exceptions"]:
            lines.append(
                f"    Exception {exception['ref']}: expires {exception['expires_at']}; scope {', '.join(exception['scope_refs'])}"
            )
    for c in doc["results"]["controls"]:
        lines.append(
            f"  {c['ref']} ({c['label']}): {c['state']}; {c['execution']}; {'required' if c['required'] else 'advisory'}; local {c['local_ref']}"
        )
        for f in c["findings"]:
            lines.append(f"    Finding {f['ref']}: {f['severity']}; action {f['action_ref']}")
    for d in doc["workflow"]["decisions"]:
        lines.append(
            f"  Decision {d['ref']}: {'blocking' if d['blocking'] else 'advisory'}; local {d['local_ref']}"
        )
    lines.append(
        "Detailed reasons, evidence and actions remain in the private change-results document."
    )
    return "\n".join(lines)
