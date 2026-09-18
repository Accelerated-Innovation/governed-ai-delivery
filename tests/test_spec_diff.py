"""Classifying a Gherkin change by clause role — increment 10.

A digest answers *different or not*. The response here is tiered — cosmetic
needs nothing, clarifying needs a readiness re-run, semantic goes back through
refinement and reissues the Development Token — so the report has to say
*which clause moved*, because that is what decides the tier.

The limit is stated where it lives, in `spec_diff`: nothing here can tell a
reworded `Then` from a changed one. It reports the clause and the maximum tier
that clause implies, and a person downgrades it after reading the diff.
"""

from __future__ import annotations

from cli import spec_closure, spec_diff

FEATURE = """\
Feature: Response approval

  Background:
    Given a representative is signed in

  @rule:only-approved-may-send
  Rule: Only an approved response may be sent

    @scenario:unapproved-blocked
    Scenario: An unapproved response cannot be sent
      Given a drafted response
      When the representative sends it
      Then the send is refused
"""


def closure_of(text: str):
    doc = spec_closure.parse_feature(text)
    element = spec_closure.resolve(doc, "scenario", "unapproved-blocked")
    return spec_closure.closure(doc, element)


def roles(edited: str) -> set[str]:
    return {d.role for d in spec_diff.classify(closure_of(FEATURE), closure_of(edited))}


def test_an_unchanged_element_yields_no_differences():
    assert spec_diff.classify(closure_of(FEATURE), closure_of(FEATURE)) == []


def test_a_changed_then_is_reported_as_a_then():
    assert roles(FEATURE.replace("Then the send is refused", "Then the send is queued")) == {"then"}


def test_a_changed_given_is_reported_as_a_given():
    assert roles(FEATURE.replace("Given a drafted response", "Given an approved response")) == {"given"}


def test_a_changed_when_is_reported_as_a_when():
    assert roles(
        FEATURE.replace("When the representative sends it", "When the representative schedules it")
    ) == {"when"}


def test_a_changed_actor_is_reported_as_a_given_and_flagged_as_actor_shaped():
    """The actor lives in a Given, so it surfaces as one. It is flagged
    separately because it alters the authorization surface and can change the
    consequence class, which cascades into required evidence and review — and
    that is an upstream question, not just a re-approval."""
    edited = FEATURE.replace(
        "Given a representative is signed in", "Given an administrator is signed in"
    )
    differences = spec_diff.classify(closure_of(FEATURE), closure_of(edited))

    assert [d.role for d in differences] == ["given"]
    assert differences[0].actor_shaped is True


def test_an_ordinary_given_change_is_not_flagged_as_an_actor_change():
    """The positive control. A flag that fired on every Given would tell the
    reader nothing about which changes need an upstream evidence check."""
    edited = FEATURE.replace("Given a drafted response", "Given a submitted response")
    differences = spec_diff.classify(closure_of(FEATURE), closure_of(edited))

    assert differences[0].actor_shaped is False


def test_a_dropped_step_is_reported_with_the_clause_it_removed():
    assert roles(FEATURE.replace("      Then the send is refused\n", "")) == {"then"}


def test_a_tag_change_is_reported_as_tags():
    assert roles(FEATURE.replace("    @scenario:unapproved-blocked",
                                 "    @v2 @scenario:unapproved-blocked")) == {"tags"}


def test_a_rule_text_change_is_reported_as_rule():
    assert roles(FEATURE.replace("Rule: Only an approved response may be sent",
                                 "Rule: Any response may be sent")) == {"rule"}


def test_examples_rows_added_or_removed_are_reported_as_examples():
    outline = FEATURE.replace(
        """    Scenario: An unapproved response cannot be sent
      Given a drafted response
      When the representative sends it
      Then the send is refused
""",
        """    Scenario Outline: An unapproved response cannot be sent
      Given a <state> response
      When the representative sends it
      Then the send is refused

      Examples:
        | state     |
        | drafted   |
        | rejected  |
""",
    )
    trimmed = outline.replace("        | rejected  |\n", "")

    differences = spec_diff.classify(closure_of(outline), closure_of(trimmed))

    assert [d.role for d in differences] == ["examples"]


def test_every_reported_difference_carries_the_semantic_tier():
    """The validator never assigns a lower tier than the clause implies. A
    person downgrades a reworded Then after reading it; nothing here does
    that silently."""
    edited = FEATURE.replace("Then the send is refused", "Then the send is refused promptly")

    differences = spec_diff.classify(closure_of(FEATURE), closure_of(edited))

    assert differences and all(d.tier == "semantic" for d in differences)


def test_the_report_names_what_a_semantic_change_voids():
    """The downstream effects are the point of classifying at all: the token
    was issued for a spec that no longer exists, the sizing is stale, and the
    evidence lineage is unconfirmed for the new behavior."""
    edited = FEATURE.replace("Then the send is refused", "Then the send is queued")

    voided = spec_diff.voided_by(spec_diff.classify(closure_of(FEATURE), closure_of(edited)))

    assert "development_token" in voided
    assert "size_slice_assessment" in voided
    assert "evidence_lineage" in voided


def test_an_actor_change_additionally_voids_the_upstream_evidence_question():
    edited = FEATURE.replace(
        "Given a representative is signed in", "Given an administrator is signed in"
    )

    voided = spec_diff.voided_by(spec_diff.classify(closure_of(FEATURE), closure_of(edited)))

    assert "consequence_class" in voided


def test_nothing_is_voided_when_nothing_changed():
    assert spec_diff.voided_by([]) == []
