# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Pure declarations for shared conformance; never authorize or execute CI."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass

from packaging.version import Version

from .pack_resolution import resolve_packs
from .schema_validation import DocumentError, canonical_json, content_digest, validate_document
from .workflows import _scope

ENGINE = "govkit:change-conformance"
ENGINE_ARGV = (
    "govkit",
    "conform",
    "--target",
    "{target}",
    "--request",
    "{request}",
    "--base",
    "{base}",
    "--policy-target",
    "{policy_target}",
    "--json",
)


@dataclass(frozen=True)
class GateRequirement:
    kind: str
    selectors: tuple[str, ...]
    scope: tuple[str, ...]
    source: str
    blocking: bool
    capability_id: str | None = None


@dataclass(frozen=True)
class GateSpec:
    """A logical control within one common-engine invocation, not a CI job."""

    id: str
    requirements: tuple[GateRequirement, ...]
    dependencies: tuple[str, ...]
    commands: tuple[tuple[str, ...], ...] = ()
    triggers: tuple[str, ...] = ("pull-request", "push", "manual")
    path_filters: tuple[str, ...] = ()
    permissions: tuple[str, ...] | None = None
    secrets: tuple[str, ...] | None = None
    configuration: tuple[str, ...] = ("trusted-conformance-configuration", "execution-opt-ins")
    evidence: tuple[str, ...] = ("change-results/v2",)

    @property
    def blocking(self):
        return any(r.blocking for r in self.requirements)

    def document(self):
        return {**asdict(self), "blocking": self.blocking, "runner": "common-conformance"}


@dataclass(frozen=True)
class GateCatalog:
    _document: dict

    @property
    def document(self):
        return deepcopy(self._document)

    @property
    def ready(self):
        return not self._document["decisions"]

    def to_json(self):
        return canonical_json(self._document)


def parse_catalog(document):
    """Validate consistency, not accepted authority or an executable allowlist."""
    document = deepcopy(document)
    validate_document(document, "gate-catalog")
    digest = content_digest(
        canonical_json({k: v for k, v in document.items() if k != "digest"}).encode()
    )
    if document["digest"] != digest:
        raise DocumentError("Invalid gate catalog digest")
    pins = document["pins"]
    Version(pins["govkit"])
    for pack in pins["packs"]:
        Version(pack["version"])
    if len({p["id"] for p in pins["packs"]}) != len(pins["packs"]):
        raise DocumentError("Duplicate pack version pins")
    provided = {capability for pack in pins["packs"] for capability in pack["provides"]}
    if set(document["capabilities"]) != provided:
        raise DocumentError("Catalog capabilities differ from pinned pack capabilities")
    gates = {g["id"]: g for g in document["gates"]}
    if len(gates) != len(document["gates"]):
        raise DocumentError("Duplicate gate IDs")
    if ENGINE not in gates or gates[ENGINE]["commands"] != [list(ENGINE_ARGV)]:
        raise DocumentError("The shared conformance engine cannot be omitted or replaced")
    if not any(
        r["kind"] == "repository" and r["blocking"] and r["scope"] == ["."]
        for r in gates[ENGINE]["requirements"]
    ):
        raise DocumentError("Shared conformance requires repository-wide blocking policy")
    for gate in gates.values():
        if gate["evidence"] != gates[ENGINE]["evidence"]:
            raise DocumentError("Logical gates must share the engine's result contract")
        if gate["blocking"] != any(r["blocking"] for r in gate["requirements"]):
            raise DocumentError("Gate blocking policy differs from its requirements")
        if gate["id"] != ENGINE and (gate["commands"] or ENGINE not in gate["dependencies"]):
            raise DocumentError("Logical gates must use the single shared engine invocation")
        for requirement in gate["requirements"]:
            for scope in requirement["scope"]:
                if _scope(scope) != scope:
                    raise DocumentError("Gate scope must be a normalized literal path")
        if set(gate["dependencies"]) - gates.keys():
            raise DocumentError("Unknown gate dependency")
    pending = {identifier: set(gate["dependencies"]) for identifier, gate in gates.items()}
    dependents = {identifier: set() for identifier in gates}
    for identifier, dependencies in pending.items():
        for dependency in dependencies:
            dependents[dependency].add(identifier)
    available = [identifier for identifier, dependencies in pending.items() if not dependencies]
    visited = set()
    while available:
        identifier = available.pop()
        visited.add(identifier)
        for dependent in dependents[identifier]:
            pending[dependent].remove(identifier)
            if not pending[dependent]:
                available.append(dependent)
    if len(visited) != len(gates):
        raise DocumentError("Cyclic gate dependency")
    if document["ready"] != (not document["decisions"]):
        raise DocumentError("Gate readiness differs from unresolved decisions")
    return GateCatalog(document)


def compose_catalog(profile, packs, *, govkit_version):
    """Describe known controls from explicit accepted inputs without request filtering.

    The common engine still re-resolves trusted policy, pinned resources, accepted
    intent and actual changes at execution. This catalog is neither complete
    runtime applicability nor permission to execute selected command/pack code.
    """
    resolution = resolve_packs(profile, tuple(packs), govkit_version=govkit_version)
    requirements = {
        ENGINE: [GateRequirement("repository", (), (".",), "bundled:change-conformance", True)]
    }

    def add(identifier, kind, selectors, source, blocking=True, scope=(".",), capability_id=None):
        requirements.setdefault(identifier, []).append(
            GateRequirement(
                kind,
                tuple(sorted(set(selectors))),
                tuple(sorted({_scope(p) for p in scope})),
                source,
                blocking,
                capability_id,
            )
        )

    for check in profile.repository.policy.required_checks:
        add(
            check.id,
            "repository",
            (),
            profile.repository.policy.source.reference,
            capability_id=check.capability_id,
        )
    for pack in resolution.packs:
        for check in pack.checks:
            add(
                check.id,
                "capability",
                pack.provides,
                f"pack:{pack.id}@{pack.version}#{check.id}",
                check.required,
            )
    for rule in profile.workflows:
        for identifier in rule.additional_checks:
            add(identifier, "workflow", rule.when, rule.source.reference)
    for transition in profile.repository.policy.transitions:
        add(
            "change:architecture",
            "architecture",
            (transition.id,),
            transition.source.reference,
            scope=transition.scope,
        )
    specs = []
    for identifier, items in sorted(requirements.items()):
        ordered = tuple(sorted(set(items), key=lambda r: canonical_json(asdict(r))))
        spec = GateSpec(identifier, ordered, () if identifier == ENGINE else (ENGINE,))
        if identifier == ENGINE:
            spec = GateSpec(
                identifier,
                ordered,
                (),
                (ENGINE_ARGV,),
                permissions=("repository:read",),
                secrets=(),
                configuration=(
                    "trusted-policy-checkout",
                    "trusted-base",
                    "accepted-request",
                    "execution-opt-ins",
                ),
            )
        specs.append(spec)
    document = {
        "schema_version": 1,
        "kind": "gate-catalog",
        "repository": profile.repository.id,
        "profile_digest": profile.digest,
        "provider": profile.repository.integrations.ci,
        "pins": {"govkit": govkit_version, "packs": [p.summary() for p in resolution.packs]},
        "capabilities": sorted({c for p in resolution.packs for c in p.provides}),
        "capability_requirements": [
            {"id": capability, "source": profile.repository.policy.source.reference}
            for capability in sorted(profile.required_capabilities)
        ],
        "workflow_requirements": [
            {
                "id": r.id,
                "when": sorted(r.when),
                "required_capabilities": sorted(r.required_capabilities),
                "source": r.source.reference,
            }
            for r in sorted(profile.workflows, key=lambda r: r.id)
        ],
        "gates": [s.document() for s in specs],
        "decisions": [asdict(d) for d in resolution.decisions],
        "ready": resolution.ready,
        "execution": "not-run",
        "enforcement": "unknown",
        "limitations": [
            "Logical gate declarations share one conformance invocation; they are not individual CI jobs or runtime allowlists.",
            "Workflow conditions describe accepted policy and cannot authorize a label/path filter to skip shared conformance.",
            "Runtime may add checks for actual changes, missing context, capabilities, architecture and approvals; re-resolve through the common engine.",
            "Resolved versions are composition pins, not proof of installed resources, published availability or publisher authenticity.",
            "Null permissions/secrets mean provider requirements are unmeasured; catalog readiness is not runnable or enforced CI.",
            "I10b owns provider rendering, trusted execution wiring, protected generation, configuration drift and provider evidence.",
        ],
    }
    document = json.loads(canonical_json(document))
    document["digest"] = content_digest(canonical_json(document).encode())
    return parse_catalog(document)
