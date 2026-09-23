# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Explicit resolution inputs and plans; no observation, loading, or execution.

These internal contracts precede the profile/pack loaders. An accepted source is
a caller-supplied trust assertion, never an inference made by the resolver.
Artifact selections describe requirements, not authorized filesystem operations.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Literal

JSONValue = str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]


class Authority(str, Enum):
    OBSERVED = "observed"
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    BUNDLED = "bundled"
    LEGACY = "legacy"


class Ownership(str, Enum):
    AGENT_CONFIG = "agent-config"
    PROJECT_ARTIFACT = "project-artifact"
    GOVERNED_CONTRACT = "governed-contract"


@dataclass(frozen=True)
class SourceRef:
    reference: str
    authority: Authority

    def require_authority(self, authority: Authority) -> None:
        if self.authority != authority:
            raise ValueError(f"{self.reference!r} must have {authority.value} authority")


@dataclass(frozen=True)
class Reason:
    text: str
    source: SourceRef


@dataclass(frozen=True)
class Provenance:
    source: SourceRef
    digest: str
    details: dict[str, JSONValue] = field(default_factory=dict)


@dataclass(frozen=True)
class CapabilityRequirement:
    id: str
    reasons: tuple[Reason, ...]
    requires: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArtifactRequirement:
    id: str
    source_path: str
    destination: str
    ownership: Ownership
    reasons: tuple[Reason, ...]
    capability_id: str | None = None
    # Installer attributes such as managed_block/path_scoped stay lossless.
    attributes: dict[str, JSONValue] = field(default_factory=dict)


@dataclass(frozen=True)
class CheckRequirement:
    id: str
    reasons: tuple[Reason, ...]
    capability_id: str | None = None


@dataclass(frozen=True)
class Integrations:
    agent: str | None = None
    project_type: str | None = None
    ci: str | None = None
    stack: str | None = None


@dataclass(frozen=True)
class Observation:
    source: SourceRef
    summary: str
    scope: tuple[str, ...]
    confidence: Literal["unknown", "partial", "confirmed"]

    def __post_init__(self) -> None:
        self.source.require_authority(Authority.OBSERVED)


@dataclass(frozen=True)
class ProposedDecision:
    source: SourceRef
    question: str
    scope: tuple[str, ...]

    def __post_init__(self) -> None:
        self.source.require_authority(Authority.PROPOSED)


@dataclass(frozen=True)
class ContractRef:
    source: SourceRef
    scope: tuple[str, ...]

    def __post_init__(self) -> None:
        self.source.require_authority(Authority.ACCEPTED)


@dataclass(frozen=True)
class PolicyException:
    id: str
    source: SourceRef
    scope: tuple[str, ...]
    expires_at: str | None

    def __post_init__(self) -> None:
        self.source.require_authority(Authority.ACCEPTED)


@dataclass(frozen=True)
class ArchitectureTransition:
    id: str
    source: SourceRef
    scope: tuple[str, ...]
    mode: Literal["retain", "improve", "migrate"]
    current: tuple[ContractRef, ...]
    target: tuple[ContractRef, ...]
    applies_to: Literal["new", "new-and-changed", "all"]
    exceptions: tuple[PolicyException, ...] = ()

    def __post_init__(self) -> None:
        self.source.require_authority(Authority.ACCEPTED)


@dataclass(frozen=True)
class AcceptedPolicy:
    source: SourceRef
    required_checks: tuple[CheckRequirement, ...] = ()
    contracts: tuple[ContractRef, ...] = ()
    transitions: tuple[ArchitectureTransition, ...] = ()

    def __post_init__(self) -> None:
        self.source.require_authority(Authority.ACCEPTED)


@dataclass(frozen=True)
class RepositoryInput:
    id: str
    capabilities: tuple[CapabilityRequirement, ...] = ()
    artifacts: tuple[ArtifactRequirement, ...] = ()
    checks: tuple[CheckRequirement, ...] = ()
    integrations: Integrations = field(default_factory=Integrations)
    policy: AcceptedPolicy | None = None
    observations: tuple[Observation, ...] = ()
    proposals: tuple[ProposedDecision, ...] = ()
    provenance: tuple[Provenance, ...] = ()


@dataclass(frozen=True)
class RequestInput:
    id: str
    source: SourceRef
    required_capabilities: tuple[CapabilityRequirement, ...] = ()
    artifacts: tuple[ArtifactRequirement, ...] = ()
    checks: tuple[CheckRequirement, ...] = ()


@dataclass(frozen=True)
class UnresolvedDecision:
    id: str
    code: str
    affected: tuple[str, ...]
    message: str
    reasons: tuple[Reason, ...]


@dataclass(frozen=True)
class Selections:
    capabilities: tuple[CapabilityRequirement, ...]
    artifacts: tuple[ArtifactRequirement, ...]
    checks: tuple[CheckRequirement, ...]
    unresolved: tuple[UnresolvedDecision, ...]


class SerializablePlan:
    """Stable object-key ordering; arrays retain explicit selection precedence."""

    selections: Selections

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), allow_nan=False)

    @property
    def identity(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    @property
    def ready(self) -> bool:
        """Resolved requirements, NOT approval to write or proof of conformance."""
        return not self.selections.unresolved


@dataclass(frozen=True)
class InstallationPlan(SerializablePlan):
    repository_id: str
    selections: Selections
    integrations: Integrations
    policy: AcceptedPolicy | None
    observations: tuple[Observation, ...]
    proposals: tuple[ProposedDecision, ...]
    provenance: tuple[Provenance, ...]
    schema_version: int = field(default=1, init=False)
    kind: Literal["installation"] = field(default="installation", init=False)


@dataclass(frozen=True)
class WorkflowPlan(SerializablePlan):
    request_id: str
    source: SourceRef
    repository_identity: str
    selections: Selections
    schema_version: int = field(default=1, init=False)
    kind: Literal["workflow"] = field(default="workflow", init=False)
