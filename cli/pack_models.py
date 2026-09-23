# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Explicit pack snapshots and graph output, separate from observation and writes."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class PackDependency:
    capability: str
    version: str
    reason: str


@dataclass(frozen=True)
class PackSkill:
    path: str
    install_as: str


@dataclass(frozen=True)
class PackCheck:
    id: str
    path: str
    required: bool


@dataclass(frozen=True)
class PackFile:
    path: str
    content: bytes
    kind: str


@dataclass(frozen=True)
class PackSnapshot:
    id: str
    version: str
    govkit_min_version: str
    provides: tuple[str, ...]
    requires: tuple[PackDependency, ...]
    conflicts: tuple[str, ...]
    project_types: tuple[str, ...]
    agents: tuple[str, ...]
    skills: tuple[PackSkill, ...]
    checks: tuple[PackCheck, ...]
    files: tuple[PackFile, ...]
    digest: str
    source_kind: str
    root: Path
    legacy: dict

    def summary(self) -> dict:
        # Roots are local read handles, never portable lock references.
        return {
            "id": self.id,
            "version": self.version,
            "digest": self.digest,
            "source": self.source_kind,
            "provides": list(self.provides),
            "legacy": self.legacy,
        }


@dataclass(frozen=True)
class PackDecision:
    code: str
    subjects: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class DependencyEdge:
    parent: str
    capability: str
    provider: str
    reason: str


@dataclass(frozen=True)
class PackResolution:
    profile_digest: str
    govkit_version: str
    available: tuple[str, ...]
    packs: tuple[PackSnapshot, ...]
    edges: tuple[DependencyEdge, ...]
    required_checks: tuple[str, ...]
    decisions: tuple[PackDecision, ...]

    @property
    def ready(self) -> bool:
        return not self.decisions

    def to_json(self) -> str:
        return json.dumps(
            {
                "schema_version": 1,
                "kind": "pack-resolution",
                "profile_digest": self.profile_digest,
                "govkit_version": self.govkit_version,
                "available": list(self.available),
                "selected": [p.summary() for p in self.packs],
                "edges": [asdict(e) for e in self.edges],
                "required_checks": list(self.required_checks),
                "decisions": [asdict(d) for d in self.decisions],
                "execution": "not-run",
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
