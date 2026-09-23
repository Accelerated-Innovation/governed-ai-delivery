# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Read-only request-plan input capture and replay; no installation or execution."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from .agent_layout import AGENT_LAYOUTS
from .pack_loading import PackError, contained_file
from .pack_store import verified_lock_document
from .profiles import load_profile, parse_profile
from .schema_validation import (
    DocumentError,
    canonical_json,
    content_digest,
    read_document,
    validate_document,
)
from .workflows import (
    NormalizedRequest,
    RequestPlan,
    parse_context,
    parse_request,
    parse_scope,
    resolve_workflow,
)


def _source_refs(profile, request):
    references = {r["reference"] for r in request.document["references"]}

    def collect(value):
        if isinstance(value, dict):
            if value.get("authority") == "accepted" and isinstance(value.get("reference"), str):
                references.add(value["reference"])
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(profile.document["policy"])
    references.add(profile.document["source"]["reference"])
    return sorted(references)


def _context(target, profile, request):
    decisions, evidence = [], []

    def unavailable(code, message, affected):
        decisions.append(
            {"code": code, "message": message, "affected": list(affected), "blocking": True}
        )

    lock_digest, capabilities, checks, guidance = None, [], [], []
    try:
        lock = verified_lock_document(target)
        if lock["profile_digest"] != profile.digest:
            raise PackError("Accepted profile changed during request capture; plan again")
        lock_digest = content_digest((canonical_json(lock) + "\n").encode())
        capabilities = sorted({c for p in lock["packs"] for c in p["provides"]})
        checks = [
            {"id": key, "required": value["required"]}
            for key, value in sorted(lock["checks"].items())
        ]
        layout = AGENT_LAYOUTS.get(lock["agent"])
        if layout and layout.skills_dir:
            prefix = layout.skills_dir + "/"
            packs = {p["id"]: p for p in lock["packs"]}
            for relative, digest in sorted(lock["files"].items()):
                if not relative.startswith(prefix):
                    continue
                suffix = PurePosixPath(relative[len(prefix) :])
                if len(suffix.parts) == 2 and suffix.name == "SKILL.md":
                    owner = lock["owners"][relative]
                    guidance.append(
                        {
                            "id": suffix.parts[0],
                            "path": relative,
                            "digest": digest,
                            "capabilities": sorted(packs[owner]["provides"]),
                        }
                    )
    except (OSError, ValueError):
        unavailable(
            "unavailable-lock",
            "Verify or explicitly reconcile pinned capabilities and native guidance before using them.",
            ("pack-lock",),
        )
    requested = request.document["references"]
    for reference in _source_refs(profile, request):
        digest, origin, limitations = None, "unverified", []
        try:
            path = contained_file(target, reference)
            with path.open("rb") as stream:
                content = stream.read(65537)
            if len(content) > 65536:
                raise DocumentError("Reference exceeds observation byte limit")
            digest, origin = content_digest(content), "local-check"
            expected = {
                r["digest"] for r in requested if r["reference"] == reference and r.get("digest")
            }
            if expected - {digest}:
                unavailable(
                    "changed-reference",
                    "A versioned request source no longer matches its declared digest.",
                    (reference,),
                )
                origin = "unverified"
                limitations.append("Declared digest does not match observed content.")
        except (OSError, ValueError):
            limitations.append("Reference is unavailable, unsafe, remote or larger than 64 KiB.")
            unavailable(
                "unavailable-reference",
                "Resolve the local source required by this plan; no live tracker lookup is performed.",
                (reference,),
            )
        evidence.append(
            {
                "source": reference,
                "scope": list(request.document["scope"]),
                "method": "local-reference-snapshot",
                "origin": origin,
                "digest": digest,
                "limitations": limitations
                + ["Source bytes do not authenticate accepted authority or test execution."],
            }
        )
    return parse_context(
        {
            "profile_digest": profile.digest,
            "lock_digest": lock_digest,
            "capabilities": capabilities,
            "checks": checks,
            "guidance": guidance,
            "evidence": evidence,
            "decisions": decisions,
        }
    )


def plan_request(
    target: Path,
    request: NormalizedRequest,
    *,
    observed_scope=None,
    previous: RequestPlan | None = None,
) -> RequestPlan:
    target = target.absolute()
    try:
        profile = load_profile(contained_file(target, ".govkit/profile.yaml"))
    except (OSError, PackError) as exc:
        raise DocumentError(
            "An explicit local accepted profile is required; use profile preview/apply first"
        ) from exc
    context = _context(target, profile, request)
    result = resolve_workflow(
        profile, request, context, observed_scope=parse_scope(observed_scope), previous=previous
    )
    validate_document(result.document, "workflow-plan")
    return result


def load_workflow_plan(path: Path) -> RequestPlan:
    """Recompute selections; editable labels cannot rewrite the stored obligations.

    Replay detects inconsistency, not forged author assertions. CI must separately
    re-resolve against its trusted profile/lock, approved intent and actual diff.
    """
    return parse_workflow_plan(read_document(path))


def parse_workflow_plan(document: dict) -> RequestPlan:
    """Replay a record from explicit data; authority remains a caller assertion."""
    validate_document(document, "workflow-plan")
    inputs = document["inputs"]
    result = resolve_workflow(
        parse_profile(inputs["profile"]),
        parse_request(inputs["request"]),
        parse_context(inputs["context"]),
        observed_scope=parse_scope(inputs["observed_scope"]),
        previous=inputs["previous"],
    )
    if result.document != document:
        raise DocumentError("Request plan does not match deterministic replay of its inputs")
    return result


def render_workflow(plan: RequestPlan, *, explain=False) -> str:
    doc = plan.document
    lines = [
        f"Workflow: {doc['workflow']} — {'ready to plan' if plan.ready else 'decisions required'}",
        "Checks have not run; planning readiness is not conformance or approval.",
    ]
    for decision in doc["decisions"][:5]:
        lines.append(f"Next: {decision['message']}")
    if not doc["decisions"]:
        lines.append(
            "Next: use the selected guidance, retain the intent record, and collect required test evidence."
        )
    for guidance in doc["guidance"]:
        lines.append(f"Guidance: {guidance['id']} ({guidance['path']})")
    lines.append("Required checks: " + ", ".join(c["id"] for c in doc["checks"]))
    lines.append("Evidence/artifacts: " + ", ".join(a["id"] for a in doc["artifacts"]))
    if doc["reassessment"]["required"]:
        lines.append("Prior plan needs reassessment: inputs or scope changed.")
    if explain:
        for check in doc["checks"]:
            lines.append(f"{check['id']}: {check['reason']} [{check['source_policy']}]")
        for decision in doc["decisions"][5:]:
            lines.append(f"Next: {decision['message']}")
        lines.extend(doc["limitations"])
    return "\n".join(lines)
