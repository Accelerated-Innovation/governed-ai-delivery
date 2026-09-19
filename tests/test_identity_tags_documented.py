"""The payload documents the identifiers a baseline requires.

`GHERKIN_TAGS.md` and `GHERKIN_CONVENTIONS.md` are **copied into every target
repository** by `govkit apply`. For most projects they are the only Gherkin
guidance that ever arrives.

Until now neither mentioned `@rule:` or `@scenario:` — the identifiers a
behavioral baseline requires and whose absence it refuses (`id_source:
derived` is rejected by `behavioral_baseline.schema.json`). A team following
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


def test_the_schema_still_refuses_derived_identifiers():
    """The reason the documentation above has to exist. If this ever stops
    being true, the guidance is overstated and should be softened rather
    than left to frighten people."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    id_source = schema["$defs"]["behaviorRef"]["properties"]["id_source"]

    assert "derived" in json.dumps(id_source).lower()
    assert "content_digest" in schema["$defs"]["behaviorRef"]["required"]
