"""Is this baseline currently authorized? — increment 11.

**Three outcomes, never two.** Authorized, not authorized, and *could not
determine*. The third exists because conflating it with rejection tells
someone their approval is bad when their network is bad, and conflating it
with approval is worse. The acceptance criteria name the distinction
directly: network failure and unsupported contract versions must be
distinguishable from rejection.

**This asks the PDG every time.** No caching, and the reason is not
performance: an invalidation is precisely what a cache would hide. The whole
point of the invalidation path is that authority can be withdrawn, and a
cached "yes" makes withdrawal take effect never.

**Authority is not consistency.** `govkit validate-baseline` answers whether
the working tree still says what was approved — entirely locally, no PDG
needed, which is what an open-source adopter without one still gets. This
answers whether that approval is still current, and nothing local can.

**The baseline names no decision.** Increment 01 rejects a baseline that
asserts its own approval, so a local pointer names the commitment and the PDG
adjudicates it. Forging the pointer does not forge authority: it yields a
commitment that either does not exist or binds something other than this
baseline, which is why the comparison below is of the binding and not merely
of the status.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from cli.baseline import compute_digest

SUPPORTED_CONTRACT_VERSIONS = (1,)


class Outcome(Enum):
    AUTHORIZED = "authorized"
    NOT_AUTHORIZED = "not_authorized"
    UNDETERMINED = "undetermined"


class PdgUnreachable(RuntimeError):
    """The PDG could not be asked — not an answer about authority."""


@dataclass(frozen=True)
class Result:
    outcome: Outcome
    detail: str


def _binding_mismatch(baseline: dict, status: dict) -> str | None:
    """Whether the commitment the pointer names actually binds *this* baseline.

    Checked field by field rather than as a whole, because the useful thing to
    report is which part disagrees: a wrong revision is a replay, a wrong
    opportunity is a pointer to someone else's decision, and they lead
    somewhere different.

    **A field that is absent is a mismatch, not a match.** Treating missing
    values as nothing-to-compare meant a near-empty document plus any real
    commitment id passed as authorized — an incomplete baseline borrowing
    someone else's approval.
    """
    sources = baseline.get("sources") or []
    expected_opportunity = (baseline.get("opportunity") or {}).get("opportunity_ref")

    if not expected_opportunity or not sources:
        return (
            "this baseline does not declare the opportunity and sources a commitment "
            "binds, so there is nothing to verify it against"
        )

    if status.get("opportunity_ref") != expected_opportunity:
        return (
            f"the commitment binds opportunity {status.get('opportunity_ref')!r}, "
            f"and this baseline is for {expected_opportunity!r}"
        )
    # The digest of the *whole baseline artifact*, which is what the PDG
    # binds — `compute_digest`, not a per-element `content_digest`. Comparing
    # against the element digests rejected every valid approval, and the first
    # tests hid it by feeding one constant into both sides.
    expected_digest = compute_digest(baseline)
    if status.get("baseline_digest") != expected_digest:
        return (
            "the commitment binds a different baseline digest than this baseline "
            "computes"
        )
    for source in sources:
        if status.get("source_scope") == source.get("source_key"):
            if status.get("source_revision") != source.get("revision"):
                return (
                    f"the commitment binds revision "
                    f"{str(status.get('source_revision'))[:12]}… and this baseline "
                    f"declares {str(source.get('revision'))[:12]}…"
                )
            return None
    if sources:
        return (
            f"the commitment binds scope {status.get('source_scope')!r}, which this "
            f"baseline does not declare as a source"
        )
    return None


def verify(
    baseline: dict,
    *,
    commitment_id: str | None,
    fetch: Callable[[str], dict],
) -> Result:
    """Ask the PDG, then check that its answer is about *this* baseline.

    `fetch` is the bounded client seam: it either returns the status payload
    or raises `PdgUnreachable`. Keeping the HTTP out of here is what lets the
    interesting cases — a replayed revision, a superseded commitment, a forged
    pointer — be tested without a server.
    """
    if not commitment_id:
        # Nothing was looked up and nothing failed. No recorded approval is a
        # definite answer, not an inability to reach one.
        return Result(
            Outcome.NOT_AUTHORIZED,
            "no commitment is recorded for this baseline, so nothing authorizes work",
        )

    try:
        status = fetch(commitment_id)
    except PdgUnreachable as unreachable:
        return Result(
            Outcome.UNDETERMINED,
            f"the PDG could not be reached, so authority is unknown: {unreachable}",
        )

    version = status.get("schema_version")
    if version not in SUPPORTED_CONTRACT_VERSIONS:
        # An answer this checker cannot read is not evidence that authority is
        # absent, and treating it as rejection would block a pipeline over a
        # version skew.
        return Result(
            Outcome.UNDETERMINED,
            f"the PDG answered with contract version {version!r}, which this checker "
            f"does not understand; authority is unknown",
        )

    mismatch = _binding_mismatch(baseline, status)
    if mismatch:
        return Result(Outcome.NOT_AUTHORIZED, mismatch)

    if status.get("authorizes_work") is not True:
        # Identity, not truthiness. A type-invalid `"false"` is a non-empty
        # string, and generic truthiness let it exit an enforced gate zero.
        return Result(
            Outcome.NOT_AUTHORIZED,
            f"the commitment does not currently authorize work "
            f"({status.get('reason') or status.get('status')})",
        )

    return Result(Outcome.AUTHORIZED, f"commitment {status.get('commitment_id')} is current")


def exit_status(outcome: Outcome, *, enforced: bool) -> int:
    """What a caller should exit with.

    Enforcement is a property of the call site, not of configuration. A
    marker field named `enforce` is one line to flip in a pull request, and it
    would flip a gate while reading as a setting.

    An enforced check fails closed on **both** rejection and inability to
    determine: a gate that passes when the PDG is unreachable is not a gate.
    """
    if not enforced:
        return 0
    return 0 if outcome is Outcome.AUTHORIZED else 1
