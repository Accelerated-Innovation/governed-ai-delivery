"""Classify a Gherkin change by clause role — increment 10.

A digest answers *different or not*. The response in this system is tiered:
cosmetic needs nothing, clarifying needs a readiness re-run, a semantic edit
goes back through refinement with the PM/QA/engineering trio and reissues the
Development Token. A hash cannot tell those apart, so it would report every
edit identically and hand the classification back to a human — which is the
work `govkit-feature-refine → readiness` already does.

So this module says *which clause moved*, because that is what decides the
tier and what the downstream effects hang off.

**The limit, stated where it lives.** Nothing here can tell a reworded `Then`
from a changed one: "the user sees an error" → "is shown an error" is
editorial, → "sees a warning" is semantic, and no parser separates them. So a
difference carries the **maximum tier its clause implies**, erring strict, and
a person downgrades it after reading the diff. It never upgrades silently and
it never assigns the tier itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from cli.spec_closure import Closure

#: Words that name *who* rather than *what*. A change among these alters the
#: authorization surface and the affected parties, which can move the
#: consequence class — and that is an upstream question about whether the
#: validation evidence still holds, not merely a re-approval.
_ACTORS = (
    "admin", "administrator", "user", "representative", "agent", "operator",
    "manager", "owner", "customer", "guest", "engineer", "lead", "approver",
    "reviewer", "supervisor", "anonymous", "service account",
)
_ACTOR = re.compile(r"\b(" + "|".join(re.escape(a) for a in _ACTORS) + r")\b", re.I)

_GIVEN, _WHEN, _THEN = "Given", "When", "Then"


@dataclass(frozen=True)
class Difference:
    """One clause that moved, and what it implies."""

    role: str
    detail: str
    tier: str = "semantic"
    actor_shaped: bool = False


def _by_role(steps: tuple[tuple[str, str, str], ...]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {_GIVEN: [], _WHEN: [], _THEN: []}
    for keyword, text, payload in steps:
        bucket = keyword if keyword in grouped else _GIVEN
        grouped[bucket].append(f"{text}\x1f{payload}")
    return grouped


def _actors(values: list[str]) -> set[str]:
    return {m.group(0).lower() for v in values for m in _ACTOR.finditer(v)}


def classify(old: Closure, new: Closure) -> list[Difference]:
    """Every clause that differs, most contract-bearing first.

    `Then` leads because it is the promised observable outcome — the heart of
    what was approved.
    """
    differences: list[Difference] = []
    before, after = _by_role(old.steps), _by_role(new.steps)

    for role, label in ((_THEN, "then"), (_WHEN, "when"), (_GIVEN, "given")):
        if before[role] == after[role]:
            continue
        # Every clause, not only Given. Who *performs* an action and who
        # *receives* an outcome are both affected parties, and either change
        # alters the authorization surface — the flag considered only the
        # precondition while the matcher already scanned all three.
        actor_shaped = _actors(before[role]) != _actors(after[role])
        differences.append(
            Difference(
                role=label,
                detail=(
                    f"{label} clauses differ: "
                    f"{len(before[role])} -> {len(after[role])} step(s)"
                ),
                actor_shaped=actor_shaped,
            )
        )

    if old.examples != new.examples:
        # Rows compare as a set, so a reorder never reaches here. Added or
        # removed rows change the input domain the contract covers, which also
        # makes the size/slice scoring stale.
        differences.append(
            Difference(
                role="examples",
                detail=f"Examples rows differ: {len(old.examples)} -> {len(new.examples)}",
            )
        )

    if old.tags != new.tags:
        # Nothing behavioral moved and the commitment did: a release tag
        # changes what was promised, and a tag binding a scenario to an NFR or
        # an eval criterion changes which gates apply.
        differences.append(
            Difference(
                role="tags",
                detail=f"tags differ: {sorted(set(old.tags) ^ set(new.tags))}",
            )
        )

    if (old.rule_text, old.rule_description) != (new.rule_text, new.rule_description):
        differences.append(
            Difference(role="rule", detail="the Rule's obligation text differs")
        )

    return differences


def voided_by(differences: list[Difference]) -> list[str]:
    """What a semantic change invalidates downstream.

    Naming these is the point of classifying at all. A changed spec does not
    merely need re-reading — the readiness verdict and Development Token were
    issued for a spec that no longer exists, the size/slice assessment is
    stale, and the evidence lineage is broken because validation proved demand
    for the old behavior and nobody has confirmed it covers the new.

    An actor change adds the upstream question, because it can move the
    consequence class and therefore how much evidence and review the feature
    needs at all.
    """
    if not any(d.tier == "semantic" for d in differences):
        return []
    voided = ["development_token", "size_slice_assessment", "evidence_lineage"]
    if any(d.actor_shaped for d in differences):
        voided.append("consequence_class")
    return voided
