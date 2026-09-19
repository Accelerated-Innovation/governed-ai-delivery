"""Verifying current authorization against the PDG — increment 11.

Three outcomes, never two. **Authorized**, **not authorized**, and **could
not determine** — and the third must never render as either of the others.
Telling someone they are unauthorized when the network is down sends them to
repair an approval that is perfectly valid; the reverse is worse.

The baseline deliberately carries no decision id: increment 01 rejects a
baseline that asserts its own approval. So a local pointer names the decision
and the PDG adjudicates it, which is why "a local forged approval file never
passes authoritative verification" is an acceptance criterion rather than a
worry — forging the pointer gets you a commitment whose binding does not match.
"""

from __future__ import annotations

import pytest

from cli import authority_check
from cli.authority_check import Outcome

DIGEST = "sha256:" + "f" * 64

BASELINE = {
    "version": 1,
    "commitment_key": "support-response-approval",
    "opportunity": {"opportunity_ref": "PDG-OPP-4471"},
    "sources": [{
        "source_key": "support-app",
        "repository": "https://example.invalid/support-app",
        "revision": "1f0c9a6d3b5e27184c0a9f2d6b8e4713a5c9d0f2",
        "path": "features",
        "kind": "repository",
    }],
    "selected_behavior": [{
        "ref": "support-app/response-approval#scenario:x",
        "kind": "scenario",
        "id_source": "tag",
        "content_digest": DIGEST,
    }],
}


def engine_says(**overrides):
    """What `GET /v1/commitments/{id}` answers, per increment 08B."""
    data = {
        "commitment_id": "cmt-1",
        "opportunity_ref": "PDG-OPP-4471",
        "baseline_digest": DIGEST,
        "source_scope": "support-app",
        "source_revision": "1f0c9a6d3b5e27184c0a9f2d6b8e4713a5c9d0f2",
        "consequence_class": "standard",
        "status": "authorizing",
        "authorizes_work": True,
        "reason": None,
        "schema_version": 1,
    }
    data.update(overrides)
    return data


def check(status=None, unreachable=None, baseline=None, commitment_id="cmt-1"):
    def transport(_commitment_id):
        if unreachable is not None:
            raise authority_check.PdgUnreachable(unreachable)
        return status if status is not None else engine_says()

    return authority_check.verify(
        baseline or BASELINE, commitment_id=commitment_id, fetch=transport
    )


# --- the three outcomes ------------------------------------------------------

def test_a_current_matching_approval_is_authorized():
    assert check().outcome is Outcome.AUTHORIZED


def test_an_invalidated_approval_is_not_authorized():
    result = check(engine_says(status="invalidated", authorizes_work=False,
                               reason="COMMITMENT_INVALIDATED"))

    assert result.outcome is Outcome.NOT_AUTHORIZED
    assert "COMMITMENT_INVALIDATED" in result.detail


def test_a_superseded_approval_is_not_authorized():
    result = check(engine_says(status="superseded", authorizes_work=False,
                               reason="COMMITMENT_SUPERSEDED"))

    assert result.outcome is Outcome.NOT_AUTHORIZED


def test_an_unconfirmed_approval_is_not_authorized():
    """The two-phase transition from increment 07 reaches all the way here:
    a commitment whose state transition never completed authorizes nothing."""
    result = check(engine_says(status="incomplete", authorizes_work=False,
                               reason="COMMITMENT_INCOMPLETE"))

    assert result.outcome is Outcome.NOT_AUTHORIZED


def test_an_unreachable_pdg_is_undetermined_not_rejected():
    """The distinction the acceptance criterion names. A rejection sends
    someone to repair an approval that is fine."""
    result = check(unreachable="connection timed out after 5s")

    assert result.outcome is Outcome.UNDETERMINED
    assert "timed out" in result.detail


def test_an_unsupported_contract_version_is_undetermined_not_rejected():
    """Also named in the acceptance criteria. A schema this checker does not
    understand is not evidence that authority is absent."""
    result = check(engine_says(schema_version=99))

    assert result.outcome is Outcome.UNDETERMINED
    assert "version" in result.detail.lower()


# --- a forged pointer does not become authority ------------------------------

def test_a_pointer_to_a_commitment_binding_something_else_is_not_authorized():
    """"A local forged approval file never passes authoritative verification."
    Naming a real commitment that binds a different baseline is the realistic
    forgery — it exists, it is current, and it is not this."""
    result = check(engine_says(baseline_digest="sha256:" + "a" * 64))

    assert result.outcome is Outcome.NOT_AUTHORIZED
    assert "digest" in result.detail.lower()


def test_a_commitment_bound_to_another_opportunity_is_not_authorized():
    result = check(engine_says(opportunity_ref="PDG-OPP-9999"))

    assert result.outcome is Outcome.NOT_AUTHORIZED
    assert "opportunity" in result.detail.lower()


def test_a_commitment_at_another_revision_is_not_authorized():
    """A replay of an approval made against a different revision of the
    source."""
    result = check(engine_says(source_revision="9" * 40))

    assert result.outcome is Outcome.NOT_AUTHORIZED
    assert "revision" in result.detail.lower()


def test_a_commitment_for_another_scope_is_not_authorized():
    result = check(engine_says(source_scope="billing-app"))

    assert result.outcome is Outcome.NOT_AUTHORIZED
    assert "scope" in result.detail.lower()


def test_no_pointer_at_all_is_not_authorized_rather_than_undetermined():
    """Nothing was looked up and nothing failed. There is simply no recorded
    approval, which is a definite answer."""
    result = check(commitment_id=None)

    assert result.outcome is Outcome.NOT_AUTHORIZED


# --- what it must not leak ----------------------------------------------------

def test_the_result_carries_no_secret_and_no_evidence_text():
    """Printed by CI. The binding is identifiers and digests; nothing here
    should ever carry a token or quoted evidence."""
    result = check(engine_says(status="invalidated", authorizes_work=False,
                               reason="COMMITMENT_INVALIDATED"))

    rendered = f"{result.outcome} {result.detail}"
    assert "Bearer" not in rendered
    assert "token" not in rendered.lower()


# --- enforcement is a property of the call site ------------------------------

@pytest.mark.parametrize(
    "outcome,enforced,expected",
    [
        (Outcome.AUTHORIZED, True, 0),
        (Outcome.AUTHORIZED, False, 0),
        (Outcome.NOT_AUTHORIZED, True, 1),
        (Outcome.NOT_AUTHORIZED, False, 0),
        (Outcome.UNDETERMINED, True, 1),
        (Outcome.UNDETERMINED, False, 0),
    ],
)
def test_only_an_enforced_check_fails_closed(outcome, enforced, expected):
    """Drafting reports and continues; the protected boundary fails closed —
    on *both* rejection and inability to determine, because a gate that
    passes when the PDG is unreachable is not a gate."""
    assert authority_check.exit_status(outcome, enforced=enforced) == expected
