# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Typed check execution and evidence facts; no collection, rendering or writes."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol


class State(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    UNKNOWN = "unknown"
    SKIPPED = "skipped"
    NOT_APPLICABLE = "not-applicable"
    WAIVED = "waived"


class Execution(str, Enum):
    NOT_RUN = "not-run"
    EXECUTED = "executed"
    ERROR = "error"


@dataclass(frozen=True)
class Identity:
    repository: str
    revision: str | None = None
    dirty_digest: str | None = None
    profile_digest: str | None = None
    resolution_digest: str | None = None
    pack_lock_digest: str | None = None
    change_digest: str | None = None
    observed_at: str | None = None


@dataclass(frozen=True)
class Evidence:
    source: str
    scope: tuple[str, ...]
    method: str
    origin: str
    digest: str | None
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    category: str
    message: str
    suggested_action: str
    location: str | None = None
    evidence: tuple[Evidence, ...] = ()


@dataclass(frozen=True)
class CheckOutcome:
    state: State
    execution: Execution
    summary: str
    findings: tuple[Finding, ...] = ()
    evidence: tuple[Evidence, ...] = ()


@dataclass(frozen=True)
class CheckSpec:
    id: str
    required: bool
    reason: str
    source_policy: str
    scope: tuple[str, ...]


@dataclass(frozen=True)
class CheckContext:
    target: Path
    identity: Identity
    execute_pack_checks: tuple[str, ...] = ()
    pack_arguments: dict[str, tuple[str, ...]] = field(default_factory=dict)


class Check(Protocol):
    def __call__(self, context: CheckContext) -> CheckOutcome:
        """Return facts; do not print, exit, fetch policy, or mutate the target."""
        ...


@dataclass(frozen=True)
class CheckResult:
    spec: CheckSpec
    outcome: CheckOutcome
