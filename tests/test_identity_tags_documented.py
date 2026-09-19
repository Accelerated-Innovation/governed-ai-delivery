"""The payload documents the identifiers a baseline requires.

`GHERKIN_TAGS.md` and `GHERKIN_CONVENTIONS.md` are **copied into every target
repository** by `govkit apply`. For most projects they are the only Gherkin
guidance that ever arrives.

Until now neither mentioned `@rule:` or `@scenario:` — the identifiers a
behavioral baseline requires and whose absence it refuses (`id_source:
derived` is rejected by `validate_baseline` — note the schema *permits* it,
because the field has to be able to express it). A team following
the installed conventions exactly authored none of them, and the entire
behavior contract was unreachable to them: `inspect-package` flags every
element and a baseline can bind nothing.

The rule with teeth has to ship with the thing that enforces it. This test is
what keeps it shipped.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

DOCS = pathlib.Path("docs/backend/architecture")
TAGS = DOCS / "GHERKIN_TAGS.md"
CONVENTIONS = DOCS / "GHERKIN_CONVENTIONS.md"
SCHEMA = pathlib.Path("governance/schemas/behavioral_baseline.schema.json")

SECTION = "## Identity Tags"


def _identity_section() -> str:
    """The Identity Tags section only.

    Scoped rather than searching the file, because `@rule:` could appear in
    any example anywhere and an unanchored match would pass on one.
    """
    body = TAGS.read_text(encoding="utf-8")
    assert SECTION in body, f"{TAGS} has no '{SECTION}' section"
    rest = body[body.index(SECTION) + len(SECTION):]
    nxt = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


@pytest.mark.parametrize("tag", ["@rule:", "@scenario:"])
def test_the_payload_documents_the_identity_tags(tag):
    assert tag in _identity_section()


def test_it_says_a_contract_makes_them_required():
    """"Recommended" is what the plugin used to say, and it is what made a
    released feature unreachable for anyone who believed it."""
    section = _identity_section().lower()

    assert "required" in section
    assert "derived" in section


def test_the_conventions_point_at_them():
    """`GHERKIN_CONVENTIONS.md` is the door most readers come through; a
    reference only reachable from the other file is half-shipped."""
    assert "identity" in CONVENTIONS.read_text(encoding="utf-8").lower()


def test_a_derived_identifier_is_actually_refused():
    """The reason the documentation above has to exist — asserted by
    running the check, not by reading the schema for a word.

    The first version of this test searched the schema JSON for
    `"derived"` and passed. It would have passed whatever the behaviour
    was, because **the schema deliberately permits `derived`**: it is a
    value of the `id_source` enum, and has to be, or the field could not
    express a derived identity at all.

    The refusal is in `validate_baseline` — the cross-field checker — and
    that is where it has to be tested. Two layers, two jobs; asserting
    against the wrong one is how a guarantee quietly stops holding.
    """
    from cli.baseline import validate_baseline

    baseline = {
        "version": 1,
        "commitment_key": "k",
        "opportunity": {"opportunity_ref": "O", "outcome": "x"},
        "sources": [{"source_key": "a", "repository": "r", "revision": "0" * 40,
                     "path": "f", "kind": "repository"}],
        "selected_behavior": [{"ref": "a/f#rule:r", "kind": "rule",
                               "id_source": "derived",
                               "content_digest": "sha256:" + "0" * 64}],
    }

    errors, _ = validate_baseline(baseline)

    assert any("derived" in error for error in errors), errors


def test_the_same_baseline_with_an_authored_identifier_passes():
    """The other half. A refusal test that never sees the accepting case
    cannot distinguish "refuses derived" from "refuses everything"."""
    from cli.baseline import validate_baseline

    baseline = {
        "version": 1,
        "commitment_key": "k",
        "opportunity": {"opportunity_ref": "O", "outcome": "x"},
        "sources": [{"source_key": "a", "repository": "r", "revision": "0" * 40,
                     "path": "f", "kind": "repository"}],
        "selected_behavior": [{"ref": "a/f#rule:r", "kind": "rule",
                               "id_source": "tag",
                               "content_digest": "sha256:" + "0" * 64}],
    }

    errors, _ = validate_baseline(baseline)

    assert not errors, errors


def test_the_schema_permits_derived_because_the_field_must_express_it():
    """Recorded so nobody "fixes" the schema to match the prose. The enum
    carries both values; the *decision* not to accept one is made a layer
    up."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert schema["$defs"]["behaviorRef"]["properties"]["id_source"]["enum"] == [
        "tag", "derived",
    ]
