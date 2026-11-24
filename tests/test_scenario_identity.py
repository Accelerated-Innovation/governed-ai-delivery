"""Scenario identity and revision digests equal the Product Definition Graph's.

The engine refuses a whole verification run when one revision digest differs
from the one it indexed, so GovKit's reader is pinned to the engine's with
copied fixtures. The slug pairs come from `aipos-plugins` by way of the engine;
the revision cases were produced by running the engine's reader.
"""

import json
from pathlib import Path

import pytest

from cli import scenario_identity as si

FIXTURES = Path(__file__).parent / "fixtures" / "scenario-identity"
SLUGS = json.loads((FIXTURES / "slug_parity.json").read_text(encoding="utf-8"))
REVISIONS = json.loads((FIXTURES / "revision_parity.json").read_text(encoding="utf-8"))
PACKAGE = REVISIONS["package"]


def _case(name: str) -> dict:
    return next(case for case in REVISIONS["cases"] if case["name"] == name)


@pytest.mark.parametrize("title, slug", SLUGS["pairs"])
def test_slug_equals_the_skill_packs(title, slug):
    assert si.slugify(title) == slug


@pytest.mark.parametrize(
    "case",
    [c for c in REVISIONS["cases"] if "scenarios" in c["expected"]],
    ids=lambda c: c["name"],
)
def test_scenarios_equal_the_engines(case):
    scenarios = si.read_scenarios(PACKAGE, case["feature"].encode("utf-8"))
    assert [
        {
            "id": s.id,
            "id_source": s.id_source,
            "title": s.title,
            "tags": list(s.tags),
            "revision_digest": s.revision_digest,
        }
        for s in scenarios
    ] == case["expected"]["scenarios"]


@pytest.mark.parametrize(
    "case",
    [c for c in REVISIONS["cases"] if "refused" in c["expected"]],
    ids=lambda c: c["name"],
)
def test_refusals_equal_the_engines(case):
    with pytest.raises(si.IdentityError) as refused:
        si.read_scenarios(PACKAGE, case["feature"].encode("utf-8"))
    assert refused.value.reason == case["expected"]["refused"]


def test_the_fixtures_cover_every_refusal_reason():
    refused = {c["expected"]["refused"] for c in REVISIONS["cases"] if "refused" in c["expected"]}
    assert refused == set(si.REASONS)


def test_the_fixtures_record_where_they_came_from():
    for fixture in (SLUGS, REVISIONS):
        assert len(fixture["source"]["commit"]) == 40, fixture["source"]


def test_bytes_that_are_not_utf8_are_refused():
    with pytest.raises(si.IdentityError) as refused:
        si.read_scenarios(PACKAGE, b"Feature: \xff\n")
    assert refused.value.reason == "parse_error"


def test_a_comment_does_not_change_the_revision():
    plain = "Feature: F\n  Scenario: S\n    Given a step\n"
    commented = "Feature: F\n  Scenario: S\n    # why\n    Given a step\n"
    assert _digests(plain) == _digests(commented)


def test_a_changed_step_changes_the_revision():
    before = "Feature: F\n  Scenario: S\n    Given a step\n"
    after = "Feature: F\n  Scenario: S\n    Given another step\n"
    assert _digests(before) != _digests(after)


def test_a_background_is_not_part_of_a_scenarios_revision():
    """Recorded, not endorsed: the engine's span stops at a Background, so GovKit's
    does too. L06 treats a Background edit as a finding for that reason."""
    before = "Feature: F\n  Background:\n    Given one\n  Scenario: S\n    Then ok\n"
    after = "Feature: F\n  Background:\n    Given two\n  Scenario: S\n    Then ok\n"
    assert _digests(before) == _digests(after)


def test_a_scenario_reports_whether_it_is_an_outline():
    case = _case("outline-with-examples")
    scenarios = si.read_scenarios(PACKAGE, case["feature"].encode("utf-8"))
    assert [s.outline for s in scenarios] == [True, True]
    plain = si.read_scenarios(PACKAGE, b"Feature: F\n  Scenario: S\n    Then ok\n")
    assert [s.outline for s in plain] == [False]


def _digests(text: str) -> list[str]:
    return [s.revision_digest for s in si.read_scenarios(PACKAGE, text.encode("utf-8"))]
