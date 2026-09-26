# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Accepted observation budgets and their replayable, unauthenticated provenance."""

from dataclasses import asdict, dataclass, replace

from .change_policy import load_change_policy
from .change_scope import capture_change
from .observation_limits import DEFAULT_OBSERVATION_LIMITS, ObservationLimits
from .pack_loading import contained_file
from .profiles import parse_profile
from .schema_validation import (
    DocumentError,
    canonical_json,
    content_digest,
    parse_document,
    validate_document,
)

POLICY_SOURCE_BYTES = 65536


def read_policy_source(target, reference):
    """Policy bootstrap stays small even when its accepted capture budget is larger."""
    with contained_file(target, reference).open("rb") as stream:
        content = stream.read(POLICY_SOURCE_BYTES + 1)
    if len(content) > POLICY_SOURCE_BYTES:
        raise DocumentError("Observation policy source exceeds 64 KiB")
    return content


def load_observation_profile(target):
    return parse_profile(parse_document(read_policy_source(target, ".govkit/profile.yaml")))


@dataclass(frozen=True)
class ObservationBudget:
    limits: ObservationLimits = DEFAULT_OBSERVATION_LIMITS
    source_digest: str | None = None
    source_state: str = "default"

    @property
    def document(self):
        return {
            "limits": asdict(self.limits),
            "source_digest": self.source_digest,
            "source_state": self.source_state,
        }

    @property
    def digest(self):
        return content_digest(canonical_json(self.document).encode())


def parse_observation(document):
    validate_document(document, "observation-budget")
    # JSON Schema accepts 1.0 as integer; runtime values must be strict integers.
    return ObservationBudget(
        ObservationLimits(**document["limits"]), document["source_digest"], document["source_state"]
    )


def policy_budget(policy, digest):
    return ObservationBudget(
        ObservationLimits(
            max_file_bytes=policy.get("observation_limits", {}).get(
                "max_file_bytes", DEFAULT_OBSERVATION_LIMITS.max_file_bytes
            )
        ),
        digest,
        "accepted",
    )


def resolve_observation_budget(target, profile):
    """A missing declaration uses defaults; an invalid declared source stays unknown."""
    if profile is None:
        return ObservationBudget(source_state="unavailable")
    try:
        if load_observation_profile(target).digest != profile.digest:
            raise DocumentError("Observation profile changed during capture")
        if "conformance" not in profile.document["policy"]:
            return ObservationBudget()
        policy, digest = load_change_policy(target, profile)
        return policy_budget(policy, digest)
    except (OSError, ValueError):
        return ObservationBudget(source_state="unavailable")


def capture_observation(target, base, budget):
    snapshot = capture_change(target, base, limits=budget.limits)
    problems = snapshot.problems
    if budget.source_state == "unavailable":
        problems += ("Accepted observation policy is unavailable; repair it and recapture",)
    return replace(snapshot, observation=budget.document, problems=problems)
