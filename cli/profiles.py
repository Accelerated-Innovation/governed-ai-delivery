# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Runtime profile contracts and deterministic records, separate from writes.

Accepted authority is an explicit project assertion, not authenticated approval.
Workflow and maintenance declarations do not execute routing, checks or lookups.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from . import paths, version
from .resolution import resolve_repository
from .resolution_models import (
    AcceptedPolicy,
    ArchitectureTransition,
    Authority,
    CapabilityRequirement,
    CheckRequirement,
    ContractRef,
    InstallationPlan,
    Integrations,
    JSONValue,
    Observation,
    PolicyException,
    ProposedDecision,
    Provenance,
    Reason,
    RepositoryInput,
    SourceRef,
    UnresolvedDecision,
)


class ProfileError(ValueError):
    """Invalid, conflicting or unsafe profile/record input."""


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class _ProfileLoader(yaml.SafeLoader):
    """JSON-shaped YAML only: no aliases, duplicate keys or implicit dates."""

    yaml_implicit_resolvers = {
        key: [(tag, regex) for tag, regex in values if tag != "tag:yaml.org,2002:timestamp"]
        for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }

    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise ProfileError("YAML aliases are not allowed in a profile or resolution record")
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ProfileError("Object keys must be strings")
            if key in result:
                raise ProfileError(f"Duplicate YAML/JSON key: {key}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def _read_document(path: Path) -> dict:
    try:
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=_ProfileLoader)
        # Reject YAML-specific objects and non-finite values before validation.
        canonical_json(value)
        return value
    except (OSError, UnicodeError, yaml.YAMLError, TypeError, ValueError, RecursionError) as exc:
        raise ProfileError(f"{path}: {exc}") from exc


def _validate(document: dict, schema_name: str) -> None:
    try:
        canonical_json(document)
        schema = json.loads(
            (paths.GOVERNANCE_DIR / "schemas" / f"{schema_name}.schema.json").read_text(
                encoding="utf-8"
            )
        )
    except (OSError, UnicodeError, TypeError, ValueError, RecursionError) as exc:
        raise ProfileError(f"Cannot validate {schema_name}: {exc}") from exc
    # Bundled schemas use local $defs only; validation never retrieves schemas.
    errors = list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(document)
    )
    if errors:
        details = []
        for error in errors:
            location = "/" + "/".join(str(part) for part in error.absolute_path)
            details.append(f"{location}: {error.message}")
        raise ProfileError(f"Invalid {schema_name}: " + "; ".join(details))


def _source(data: dict) -> SourceRef:
    return SourceRef(data["reference"], Authority(data["authority"]))


def _contract(data: dict) -> ContractRef:
    return ContractRef(_source(data["source"]), tuple(data["scope"]))


def _transition(data: dict) -> ArchitectureTransition:
    exceptions = tuple(
        PolicyException(
            item["id"], _source(item["source"]), tuple(item["scope"]), item["expires_at"]
        )
        for item in data.get("exceptions", [])
    )
    return ArchitectureTransition(
        data["id"],
        _source(data["source"]),
        tuple(data["scope"]),
        data["mode"],
        tuple(_contract(item) for item in data["current"]),
        tuple(_contract(item) for item in data["target"]),
        data["applies_to"],
        exceptions,
    )


@dataclass(frozen=True)
class WorkflowRule:
    id: str
    source: SourceRef
    when: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    additional_checks: tuple[str, ...]


@dataclass(frozen=True)
class ReleaseSource:
    id: str
    url: str
    channels: tuple[str, ...]


@dataclass(frozen=True)
class VersionConstraint:
    component: str
    source_id: str
    channel: str
    pin: str | None
    compatibility: str | None


@dataclass(frozen=True)
class MaintenancePolicy:
    sources: tuple[ReleaseSource, ...] = ()
    constraints: tuple[VersionConstraint, ...] = ()
    metadata_max_age_hours: int | None = None
    assessment_max_age_hours: int | None = None
    allow_refresh: bool = False


@dataclass(frozen=True)
class ProjectProfile:
    repository: RepositoryInput
    workflows: tuple[WorkflowRule, ...]
    maintenance: MaintenancePolicy
    required_capabilities: tuple[str, ...]
    context_requirements: tuple[tuple[str, tuple[str, ...]], ...]
    _document: dict[str, JSONValue]

    @property
    def document(self) -> dict[str, JSONValue]:
        return deepcopy(self._document)

    @property
    def digest(self) -> str:
        return content_digest(canonical_json(self._document).encode("utf-8"))


def _unique(items: list[dict], location: str, key: str = "id") -> None:
    seen = set()
    for item in items:
        if item[key] in seen:
            raise ProfileError(f"{location}: duplicate {key} {item[key]!r}")
        seen.add(item[key])


def _maintenance(data: dict) -> MaintenancePolicy:
    sources = tuple(
        ReleaseSource(s["id"], s["url"], tuple(s["channels"])) for s in data.get("sources", [])
    )
    constraints = tuple(
        VersionConstraint(
            c["component"], c["source_id"], c["channel"], c.get("pin"), c.get("compatibility")
        )
        for c in data.get("constraints", [])
    )
    by_id = {s.id: s for s in sources}
    for source in sources:
        parsed = urlsplit(source.url)
        if parsed.username is not None or parsed.password is not None:
            raise ProfileError("maintenance/sources: URLs must not contain embedded credentials")
    for constraint in constraints:
        source = by_id.get(constraint.source_id)
        if source is None or constraint.channel not in source.channels:
            raise ProfileError(
                f"maintenance: {constraint.component} must reference an approved source/channel"
            )
        if constraint.pin is None and constraint.compatibility is None:
            raise ProfileError(
                f"maintenance: {constraint.component} needs a pin or compatibility constraint"
            )
    return MaintenancePolicy(
        sources,
        constraints,
        data.get("metadata_max_age_hours"),
        data.get("assessment_max_age_hours"),
        data.get("allow_refresh", False),
    )


def parse_profile(document: dict) -> ProjectProfile:
    """Validate the complete desired configuration before constructing typed inputs."""
    document = deepcopy(document)
    _validate(document, "profile")
    policy_data = document["policy"]
    maintenance_data = document.get("maintenance", {})
    _unique(document["capabilities"], "capabilities")
    for name in ("required_checks", "workflows", "transitions"):
        _unique(policy_data.get(name, []), f"policy/{name}")
    for transition in policy_data.get("transitions", []):
        _unique(transition.get("exceptions", []), f"transition/{transition['id']}/exceptions")
    _unique(maintenance_data.get("sources", []), "maintenance/sources")
    _unique(maintenance_data.get("constraints", []), "maintenance/constraints", "component")

    source = _source(document["source"])
    policy_source = _source(policy_data["source"])
    reason = Reason("Explicit desired capability", source)
    policy_reason = Reason("Required by accepted project policy", policy_source)
    capabilities = tuple(
        CapabilityRequirement(
            c["id"], (reason,), tuple(c.get("requires", [])), tuple(c.get("conflicts", []))
        )
        for c in document["capabilities"]
    )
    policy = AcceptedPolicy(
        policy_source,
        tuple(
            CheckRequirement(c["id"], (policy_reason,), c.get("capability_id"))
            for c in policy_data.get("required_checks", [])
        ),
        tuple(_contract(c) for c in policy_data.get("contracts", [])),
        tuple(_transition(t) for t in policy_data.get("transitions", [])),
    )
    context = document["repository"]
    integrations = document.get("integrations", {})
    digest = content_digest(canonical_json(document).encode("utf-8"))
    repository = RepositoryInput(
        context["id"],
        capabilities=capabilities,
        integrations=Integrations(
            integrations.get("agent"),
            context.get("project_type"),
            integrations.get("ci"),
            context.get("stack"),
        ),
        policy=policy,
        provenance=(Provenance(source, digest, {"kind": "profile", "schema_version": 1}),),
    )
    workflows = tuple(
        WorkflowRule(
            w["id"],
            _source(w["source"]),
            tuple(w["when"]),
            tuple(w.get("required_capabilities", [])),
            tuple(w.get("additional_checks", [])),
        )
        for w in policy_data.get("workflows", [])
    )
    requirements = tuple(
        (c["id"], tuple(c.get("requires_context", []))) for c in document["capabilities"]
    )
    return ProjectProfile(
        repository,
        workflows,
        _maintenance(maintenance_data),
        tuple(policy_data.get("required_capabilities", [])),
        requirements,
        document,
    )


def load_profile(path: Path) -> ProjectProfile:
    return parse_profile(_read_document(path))


@dataclass(frozen=True)
class ProfileResolution:
    profile: ProjectProfile
    plan: InstallationPlan
    unknowns: tuple[str, ...]
    govkit_version: str
    release_metadata_status: str = "not-queried"

    @property
    def profile_digest(self) -> str:
        return self.profile.digest

    @property
    def ready(self) -> bool:
        return self.plan.ready

    def to_json(self) -> str:
        return canonical_json(
            {
                "schema_version": 1,
                "kind": "profile-resolution",
                "govkit_version": self.govkit_version,
                "profile_digest": self.profile_digest,
                "profile": self.profile.document,
                "plan": json.loads(self.plan.to_json()),
                "unknowns": list(self.unknowns),
                "release_metadata_status": self.release_metadata_status,
            }
        )


def resolve_profile(
    profile: ProjectProfile,
    *,
    observations: tuple[Observation, ...] = (),
    proposals: tuple[ProposedDecision, ...] = (),
    overrides: dict[str, str | None] | None = None,
) -> ProfileResolution:
    """Resolve declared requirements; do not infer a framework or query releases."""
    profile = deepcopy(profile)
    integrations = profile.repository.integrations
    for key, value in (overrides or {}).items():
        if value is None:
            continue
        field = "project_type" if key == "type" else key
        if field not in ("agent", "project_type", "ci", "stack"):
            raise ProfileError(
                f"Explicit {key} is not supported with a profile; edit the level-free profile"
            )
        if value != getattr(integrations, field):
            raise ProfileError(
                f"Explicit {key}={value!r} conflicts with profile value {getattr(integrations, field)!r}; edit the profile to accept a change"
            )
    repository = replace(profile.repository, observations=observations, proposals=proposals)
    plan = resolve_repository(repository)
    decisions = list(plan.selections.unresolved)
    reason = Reason("Required by accepted profile", profile.repository.policy.source)

    def missing(code: str, affected: tuple[str, ...], message: str) -> None:
        digest = content_digest(canonical_json(affected).encode("utf-8"))
        decisions.append(UnresolvedDecision(f"{code}:{digest}", code, affected, message, (reason,)))

    for capability, fields in profile.context_requirements:
        for field in fields:
            if getattr(integrations, field) is None:
                missing(
                    "missing-context",
                    (capability, field),
                    f"{capability} requires an accepted {field}; unrelated unknowns may remain unset.",
                )
    selected = {c.id for c in plan.selections.capabilities}
    for capability in profile.required_capabilities:
        if capability not in selected:
            missing(
                "missing-required-capability",
                (capability,),
                f"Accepted policy requires {capability}; reconcile the desired capabilities.",
            )
    transitions = profile.repository.policy.transitions
    for index, transition in enumerate(transitions):
        for prior in transitions[:index]:
            common_scopes = set(transition.scope) & set(prior.scope)
            constraints = (transition.mode, transition.current, transition.target)
            prior_constraints = (prior.mode, prior.current, prior.target)
            if common_scopes and constraints != prior_constraints:
                missing(
                    "conflicting-transition",
                    (prior.id, transition.id, *sorted(common_scopes)),
                    "Conflicting transitions name the same scope; reconcile current/target rules before applying.",
                )
    plan = replace(plan, selections=replace(plan.selections, unresolved=tuple(decisions)))
    unknowns = tuple(
        key
        for key in ("agent", "ci", "project_type", "stack")
        if getattr(integrations, key) is None
    )
    return ProfileResolution(profile, plan, unknowns, version.GOVKIT_VERSION)


def load_resolution(path: Path) -> ProfileResolution:
    """Validate and replay a record; serialized output cannot waive policy."""
    data = _read_document(path)
    _validate(data, "resolution")
    observations = tuple(
        Observation(_source(o["source"]), o["summary"], tuple(o["scope"]), o["confidence"])
        for o in data["plan"]["observations"]
    )
    proposals = tuple(
        ProposedDecision(_source(p["source"]), p["question"], tuple(p["scope"]))
        for p in data["plan"]["proposals"]
    )
    replay = resolve_profile(
        parse_profile(data["profile"]), observations=observations, proposals=proposals
    )
    replay = replace(replay, govkit_version=data["govkit_version"])
    if replay.to_json() != canonical_json(data):
        raise ProfileError(
            "Resolution does not match its profile/context; regenerate from accepted inputs"
        )
    return replay
