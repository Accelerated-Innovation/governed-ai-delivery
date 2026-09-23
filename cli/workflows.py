# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Normalized request contracts and pure, additive workflow selection.

Confirmation is a caller assertion of intent, not authenticated approval. Plans
select evidence obligations; no check executes and no requirement is waived here.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import PurePosixPath

from .check_models import CheckSpec, Evidence
from .profiles import ProjectProfile
from .resolution import resolve_request
from .resolution_models import Authority, CheckRequirement, Reason, RequestInput, SourceRef
from .schema_validation import DocumentError, canonical_json, content_digest, validate_document

IMPACTS = (
    "bounded",
    "within-contracts",
    "new-behavior",
    "security",
    "auth",
    "data",
    "public-contract",
    "nfr",
    "ownership",
    "architecture",
    "cross-service",
    "llm",
    "mcp",
)
SENSITIVE = (
    "security",
    "auth",
    "data",
    "public-contract",
    "nfr",
    "ownership",
    "architecture",
    "cross-service",
)
WORKFLOWS = ("defect", "bounded", "full-feature", "architecture")


def _scope(value: str) -> str:
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in value
        or ":" in value
        or any(c in value for c in "*?[]")
    ):
        raise DocumentError("Scope must be a literal repository-relative path")
    return path.as_posix()


@dataclass(frozen=True)
class NormalizedRequest:
    _document: dict

    @property
    def document(self):
        return deepcopy(self._document)

    @property
    def digest(self):
        return content_digest(canonical_json(self._document).encode())


def parse_request(document: dict) -> NormalizedRequest:
    document = deepcopy(document)
    validate_document(document, "workflow-request")
    document["scope"] = sorted({_scope(p) for p in document["scope"]})
    document["references"] = sorted(document["references"], key=canonical_json)
    return NormalizedRequest(document)


def request_template() -> dict:
    return {
        "schema_version": 1,
        "id": "request-id",
        "source": "ticket-or-local-reference",
        "summary": "Summarize the intended behavior locally before confirming.",
        "confirmation": "proposed",
        "change": "unknown",
        "scope": ["."],
        "impacts": dict.fromkeys(IMPACTS),
        "acceptance": [],
        "references": [],
        "preference": "auto",
    }


def parse_scope(document: dict | None) -> dict | None:
    if document is None:
        return None
    validate_document(document, "workflow-scope")
    result = deepcopy(document)
    result["paths"] = sorted({_scope(p) for p in result["paths"]})
    return result


@dataclass(frozen=True)
class WorkflowContext:
    _document: dict

    @property
    def document(self):
        return deepcopy(self._document)


def parse_context(document: dict) -> WorkflowContext:
    validate_document(document, "workflow-context")
    return WorkflowContext(deepcopy(document))


@dataclass(frozen=True)
class RequestPlan:
    _document: dict

    @property
    def document(self):
        return deepcopy(self._document)

    @property
    def ready(self):
        return not any(d["blocking"] for d in self._document["decisions"])

    @property
    def identity(self):
        return self._document["identity"]["plan_digest"]

    def to_json(self):
        return canonical_json(self._document)

    def check_specs(self) -> tuple[CheckSpec, ...]:
        return tuple(
            CheckSpec(c["id"], c["required"], c["reason"], c["source_policy"], tuple(c["scope"]))
            for c in self._document["checks"]
        )

    def evidence(self) -> tuple[Evidence, ...]:
        return tuple(
            Evidence(
                e["source"],
                tuple(e["scope"]),
                e["method"],
                e["origin"],
                e["digest"],
                tuple(e["limitations"]),
            )
            for e in self._document["evidence"]
        )


def _covers(prefix, path):
    prefix = prefix.rstrip("/")
    return prefix == "." or path == prefix or path.startswith(prefix + "/")


def _effective(request, observed):
    impacts, paths = dict(request["impacts"]), set(request["scope"])
    if observed:
        widened = any(not any(_covers(p, actual) for p in paths) for actual in observed["paths"])
        paths.update(observed["paths"])
        for name, value in observed["impacts"].items():
            before = impacts[name]
            # Positive risk/new-behavior assertions cannot be erased; positive
            # eligibility requires both sources to agree when evidence is supplied.
            if name in {"bounded", "within-contracts"}:
                impacts[name] = (
                    False if False in (before, value) else None if None in (before, value) else True
                )
            else:
                impacts[name] = (
                    True if True in (before, value) else None if None in (before, value) else False
                )
        if widened:
            impacts["bounded"] = False
    return impacts, sorted(paths)


def _reference_available(request, context, kind):
    for reference in request["references"]:
        if reference["kind"] != kind:
            continue
        if kind == "established-behavior" and reference["authority"] != "accepted":
            continue
        if any(
            e["source"] == reference["reference"] and e["digest"] and e["origin"] == "local-check"
            for e in context["evidence"]
        ):
            return True
    return False


def _route(request, impacts, context):
    if request["change"] == "architecture" or impacts["architecture"] is True:
        return "architecture"
    low_risk = all(impacts[name] is False for name in SENSITIVE)
    bounded = impacts["bounded"] is True and impacts["within-contracts"] is True
    if request["change"] == "defect":
        eligible = bounded and low_risk and impacts["new-behavior"] is False
        eligible = eligible and all(
            _reference_available(request, context, kind)
            for kind in ("established-behavior", "regression-test")
        )
        return "defect" if eligible else "full-feature"
    if request["change"] in {"enhancement", "refactor", "maintenance"} and bounded and low_risk:
        return "bounded"
    return "full-feature"


def _selectors(workflow, request, impacts):
    selectors = {"*", workflow, request["change"]}
    if workflow == "defect":
        selectors.add("bounded-defect")
    if workflow == "bounded":
        selectors.add("small-change")
    if workflow == "full-feature":
        selectors.add("substantial-feature")
    if impacts["llm"] is not False:
        selectors.add("model-behavior")
    selectors.update(
        name for name, value in impacts.items() if value is not False and name != "bounded"
    )
    return selectors


def _previous(plan):
    if plan is None or isinstance(plan, dict):
        return deepcopy(plan)
    doc = plan.document
    return {
        "identity": doc["identity"],
        "workflow": doc["workflow"],
        "checks": sorted(c["id"] for c in doc["checks"]),
    }


def resolve_workflow(
    profile: ProjectProfile,
    request: NormalizedRequest,
    context: WorkflowContext,
    *,
    observed_scope: dict | None = None,
    previous: RequestPlan | dict | None = None,
) -> RequestPlan:
    """Pure resolution from validated snapshots; adapters own all external reads."""
    req, ctx = request.document, context.document
    observed = deepcopy(observed_scope)
    prior = _previous(previous)
    impacts, scope = _effective(req, observed)
    decisions = deepcopy(ctx["decisions"])

    def decide(code, message, affected=(), blocking=True):
        decisions.append(
            {"code": code, "message": message, "affected": list(affected), "blocking": blocking}
        )

    if req["confirmation"] != "confirmed":
        decide(
            "unconfirmed-intent",
            "Confirm the normalized intent with its owner; an agent cannot redefine it.",
            (req["id"],),
        )
    if req["change"] == "unknown":
        decide("unknown-change", "Resolve the intended change before selecting its workflow.")
    for name, value in impacts.items():
        if value is None:
            decide("unknown-impact", f"Resolve the {name} impact for the affected work.", (name,))
    workflow = _route(req, impacts, ctx)
    if req["change"] == "defect" and workflow != "defect":
        decide(
            "defect-ineligible",
            "Defect planning requires existing accepted behavior, a local regression test, no new behavior and no sensitive scope.",
            ("defect",),
        )
    preference = req["preference"]
    if preference in {"architecture", "full-feature"} and WORKFLOWS.index(
        preference
    ) > WORKFLOWS.index(workflow):
        workflow = preference
    elif preference not in {"auto", workflow}:
        decide(
            "preference-escalated",
            "The preferred workflow cannot lower impact or accepted policy requirements.",
            (preference, workflow),
            False,
        )
    if req["change"] in {"refactor", "maintenance"} and impacts["new-behavior"] is not False:
        decide(
            "behavior-contradiction",
            "Behavior-preserving work needs an explicit no-new-behavior assertion.",
            (req["change"],),
        )
    if not req["acceptance"] and not any(
        r["kind"] == "acceptance" and r["authority"] == "accepted" for r in req["references"]
    ):
        decide(
            "missing-acceptance",
            "Record acceptance locally or reference an accepted local acceptance source.",
            (req["id"],),
        )
    applicable_contracts = [
        c
        for c in profile.document["policy"].get("contracts", [])
        if any(_covers(s, p) or _covers(p, s) for s in c["scope"] for p in scope)
    ]
    required = set(profile.required_capabilities)
    if workflow == "full-feature":
        required.add("gherkin-delivery")
    if impacts["llm"] is not False:
        required.add("llm-evaluation")
    known_selectors = (
        set(IMPACTS)
        | set(WORKFLOWS)
        | {
            "*",
            "enhancement",
            "refactor",
            "maintenance",
            "feature",
            "bounded-defect",
            "small-change",
            "model-behavior",
            "substantial-feature",
        }
    )
    checks = {
        "project:tests": (
            "Test the intended behavior and applicable regressions",
            "bundled:request-workflows",
        )
    }
    if workflow == "defect":
        checks["defect:eligibility"] = (
            "Preserve existing defect eligibility, including red/green evidence",
            "bundled:defect-lane",
        )
    for impact in (*SENSITIVE, "mcp"):
        if impacts[impact] is not False:
            checks[f"review:{impact}"] = (
                f"Review {impact} effects regardless of the author's label",
                "bundled:request-workflows",
            )
    if workflow == "architecture":
        checks["review:architecture"] = (
            "Verify accepted current/target rules and approval separately",
            "bundled:request-workflows",
        )
    matched_rules = set()
    # Additive closure: a policy can require full delivery, which activates
    # further full-delivery rules regardless of their declaration order.
    while True:
        selectors = _selectors(workflow, req, impacts)
        for rule in profile.workflows:
            if rule.id in matched_rules:
                continue
            unknown = set(rule.when) - known_selectors
            if unknown:
                decide(
                    "unknown-policy-selector",
                    "Unsupported accepted policy condition must be reconciled, not ignored.",
                    tuple(sorted(unknown)),
                )
            if unknown or selectors.intersection(rule.when):
                matched_rules.add(rule.id)
                required.update(rule.required_capabilities)
                checks.update(
                    {
                        c: (f"Required by workflow policy {rule.id}", rule.source.reference)
                        for c in rule.additional_checks
                    }
                )
        if "gherkin-delivery" in required and workflow in {"bounded", "defect"}:
            workflow = "full-feature"
            continue
        break
    uncovered = [
        p for p in scope if not any(_covers(s, p) for c in applicable_contracts for s in c["scope"])
    ]
    if workflow == "bounded" and uncovered:
        decide(
            "missing-contract",
            "Identify accepted contracts covering each path for bounded work.",
            tuple(uncovered),
        )
    sources = {
        profile.document["source"]["reference"],
        profile.document["policy"]["source"]["reference"],
    }
    sources.update(r["reference"] for r in req["references"])
    sources.update(c["source"]["reference"] for c in applicable_contracts)
    sources.update(r.source.reference for r in profile.workflows if r.id in matched_rules)
    for transition in profile.document["policy"].get("transitions", []):
        if any(_covers(s, p) or _covers(p, s) for s in transition["scope"] for p in scope):
            sources.add(transition["source"]["reference"])
            for role in ("current", "target", "exceptions"):
                sources.update(item["source"]["reference"] for item in transition.get(role, []))
    # Inspection can report unavailable unrelated references without turning
    # them into a global blocker. Every source used by this plan is required.
    for decision in decisions:
        if decision["code"] == "unavailable-reference":
            decision["blocking"] = bool(sources.intersection(decision["affected"]))
    for source in sorted(sources):
        if not any(e["source"] == source for e in ctx["evidence"]):
            decide(
                "missing-source-snapshot",
                "Capture the applicable local source before planning.",
                (source,),
            )
    for check in ctx["checks"]:
        if check["required"]:
            checks.setdefault(check["id"], ("Required by pinned capability", "pinned-pack-lock"))
    # The existing requirements engine carries unconditional accepted policy
    # checks forward; request preferences never subtract from that selection.
    contributions = tuple(
        CheckRequirement(identifier, (Reason(reason, SourceRef(source, Authority.BUNDLED)),))
        for identifier, (reason, source) in sorted(checks.items())
    )
    resolved = resolve_request(
        profile.repository,
        RequestInput(req["id"], SourceRef(req["source"], Authority.PROPOSED), checks=contributions),
    )
    for decision in resolved.selections.unresolved:
        decide(decision.code, decision.message, decision.affected)
    for capability in sorted(required - set(ctx["capabilities"])):
        decide(
            "missing-capability",
            f"Explicitly preview/accept/install the missing {capability} capability, then re-plan.",
            (capability,),
        )
    if ctx["profile_digest"] != profile.digest:
        decide(
            "profile-lock-mismatch",
            "Pinned resources must match the current accepted profile.",
            ("pack-lock",),
        )
    artifacts = {
        "change-record": "Keep this intent, acceptance, scope and decisions in one compact record.",
        "test-evidence": "Reference actual test outcomes; a plan does not prove execution.",
    }
    if workflow == "defect":
        artifacts = {
            "fix-record": "Use the existing fix-record contract with established expectation and regression evidence.",
            "test-evidence": artifacts["test-evidence"],
        }
    elif workflow == "full-feature":
        artifacts = {
            "spec": "Observable Gherkin scenarios and acceptance",
            "plan": "Implementation plan",
            "architecture-preflight": "Relevant accepted architecture checks",
            "test-plan": "Tests and evidence strategy",
            "validation": "Executed validation evidence",
        }
    elif workflow == "architecture":
        artifacts.update(
            {
                "architecture-decision": "Reference an accepted scoped decision, never self-approve.",
                "transition-plan": "Current/target rules, existing exceptions, applicability and exit verification.",
            }
        )
    for name in SENSITIVE:
        if impacts[name] is not False:
            artifacts[f"review:{name}"] = (
                f"Record or reference the applicable {name} decision/evidence."
            )
    evidence = deepcopy(ctx["evidence"])
    checks_document = []
    for check in resolved.selections.checks:
        policy_reason = next(
            (r for r in check.reasons if r.source.authority == Authority.ACCEPTED), check.reasons[0]
        )
        checks_document.append(
            {
                "id": check.id,
                "required": True,
                "reason": policy_reason.text,
                "source_policy": policy_reason.source.reference,
                "scope": scope,
                "execution": "not-run",
            }
        )
    selected_guidance = set(required) | {"application-governance"}
    guidance = [g for g in ctx["guidance"] if selected_guidance.intersection(g["capabilities"])]
    identity = {
        "profile_digest": profile.digest,
        "request_digest": request.digest,
        "lock_digest": ctx["lock_digest"],
        "scope_digest": content_digest(
            canonical_json({"scope": scope, "impacts": impacts}).encode()
        ),
    }
    identity["plan_digest"] = content_digest(
        canonical_json(
            {"resolver_version": 1, "identity": identity, "evidence": evidence, "context": ctx}
        ).encode()
    )
    changed = bool(prior and prior["identity"] != identity)
    reassessment = {
        "required": changed,
        "previous_identity": prior["identity"]["plan_digest"] if prior else None,
        "reasons": [
            "Intent, policy, resources, evidence or scope changed; use the freshly resolved obligations."
        ]
        if changed
        else [],
        "added_checks": sorted({c["id"] for c in checks_document} - set(prior["checks"]))
        if prior
        else [],
    }
    document = {
        "kind": "request-plan",
        "schema_version": 1,
        "resolver_version": 1,
        "identity": identity,
        "workflow": workflow,
        "scope": scope,
        "impacts": impacts,
        "inputs": {
            "profile": profile.document,
            "request": req,
            "context": ctx,
            "observed_scope": observed,
            "previous": prior,
        },
        "required_capabilities": sorted(required),
        "checks": sorted(checks_document, key=lambda c: c["id"]),
        "artifacts": [{"id": i, "reason": r} for i, r in sorted(artifacts.items())],
        "guidance": guidance,
        "evidence": evidence,
        "reused_contracts": applicable_contracts,
        "decisions": sorted(decisions, key=canonical_json),
        "reassessment": reassessment,
        "limitations": [
            "Normalized request/scope and authority are caller assertions, not authenticated approval.",
            "No checks were executed; I07 must derive actual scope and compare with trusted current inputs.",
        ],
    }
    return RequestPlan(document)
