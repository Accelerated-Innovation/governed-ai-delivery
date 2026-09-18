"""Gherkin closure, normalization and the materiality test — increment 10.

The rule these encode, supplied by the owner:

> A Gherkin edit makes it a different feature when it changes what a passing
> implementation would do, for whom, or under what conditions — rather than
> how the same behavior is described. The tell: if any step definition, test,
> or previously passing implementation could now fail, the contract changed.

So every test here is named for an edit and asserts whether it crosses that
line. The normalization exists to serve the test, not the other way round.
"""

from __future__ import annotations

import pytest

from cli import spec_closure

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
      And the draft is unchanged
"""


def closure_of(text: str, ref: str = "scenario:unapproved-blocked"):
    kind, slug = ref.split(":", 1)
    doc = spec_closure.parse_feature(text)
    element = spec_closure.resolve(doc, kind, slug)
    assert element is not None, f"{ref} did not resolve"
    return spec_closure.closure(doc, element)


def digest_of(text: str, ref: str = "scenario:unapproved-blocked") -> str:
    return spec_closure.content_digest(closure_of(text, ref))


def unchanged(edited: str) -> bool:
    return digest_of(edited) == digest_of(FEATURE)


# --- editorial: the digest must not move -------------------------------------

def test_reindenting_is_not_a_change():
    assert unchanged(FEATURE.replace("    Given a drafted", "        Given a drafted"))


def test_windows_line_endings_are_not_a_change():
    assert unchanged(FEATURE.replace("\n", "\r\n"))


def test_trailing_whitespace_is_not_a_change():
    assert unchanged(FEATURE.replace("Then the send is refused", "Then the send is refused   "))


def test_a_comment_is_not_a_change():
    """No comment can make a passing implementation fail, which is the test."""
    assert unchanged(FEATURE.replace(
        "    @scenario:unapproved-blocked",
        "    # the important one\n    @scenario:unapproved-blocked",
    ))


def test_reordering_scenarios_is_not_a_change():
    """Per-element closure, so a sibling moving cannot touch this one."""
    edited = FEATURE + """
    @scenario:approved-sends
    Scenario: An approved response sends
      Given an approved response
      When the representative sends it
      Then it is sent
"""
    assert unchanged(edited)


def test_extracting_a_shared_given_into_background_is_not_a_change():
    """On the owner's editorial list, and only invisible if the comparison is
    over the *effective* steps after Background inheritance. Comparing raw
    text would flag the one refactor the test explicitly permits."""
    inline = FEATURE.replace("  Background:\n    Given a representative is signed in\n\n", "")
    inline = inline.replace(
        "      Given a drafted response",
        "      Given a representative is signed in\n      And a drafted response",
    )

    assert digest_of(inline) == digest_of(FEATURE)


def test_reordering_tags_is_not_a_change():
    edited = FEATURE.replace(
        "    @scenario:unapproved-blocked",
        "    @mvp @scenario:unapproved-blocked",
    )
    reordered = FEATURE.replace(
        "    @scenario:unapproved-blocked",
        "    @scenario:unapproved-blocked @mvp",
    )
    assert digest_of(edited) == digest_of(reordered)


# --- semantic: the digest must move ------------------------------------------

@pytest.mark.parametrize(
    "description,edited",
    [
        ("a Then changed", FEATURE.replace("Then the send is refused",
                                           "Then the send is queued")),
        ("a Given changed", FEATURE.replace("Given a drafted response",
                                            "Given an approved response")),
        ("the When changed", FEATURE.replace("When the representative sends it",
                                             "When the representative schedules it")),
        ("the actor changed", FEATURE.replace("Given a representative is signed in",
                                              "Given an administrator is signed in")),
        ("a Then was dropped", FEATURE.replace("      And the draft is unchanged\n", "")),
        ("a tag was added", FEATURE.replace("    @scenario:unapproved-blocked",
                                            "    @v2 @scenario:unapproved-blocked")),
        ("the Rule text changed", FEATURE.replace("Rule: Only an approved response may be sent",
                                                  "Rule: Any response may be sent")),
    ],
)
def test_a_semantic_edit_changes_the_digest(description, edited):
    assert digest_of(edited) != digest_of(FEATURE), f"{description} did not register"


def test_a_docstring_reindent_is_a_change():
    """A docstring is payload. A YAML or JSON body means something different
    reindented, so its internal shape is preserved where Gherkin indentation
    is not."""
    with_doc = FEATURE.replace(
        "      Then the send is refused",
        '      Then the response body is:\n        """\n        a: 1\n          b: 2\n        """',
    )
    reindented = with_doc.replace("          b: 2", "        b: 2")

    assert digest_of(with_doc) != digest_of(reindented)


# --- structural refusals ------------------------------------------------------

def test_a_lowercase_keyword_is_reported_as_an_empty_element_not_a_digest_change():
    """gherkin-official does not reject a lowercase keyword — it silently
    yields a scenario with no steps. The digest of an empty thing is perfectly
    stable, so this must not be a digest question: a scenario that quietly
    lost its steps would re-approve cleanly the moment someone accepted the
    diff."""
    gutted = (FEATURE.replace("Given a drafted response", "given a drafted response")
                     .replace("When the representative sends it", "when the representative sends it")
                     .replace("Then the send is refused", "then the send is refused")
                     .replace("And the draft is unchanged", "and the draft is unchanged"))

    problems = spec_closure.structural_problems(closure_of(gutted))

    assert any("no steps" in p for p in problems), problems


def test_an_intact_scenario_reports_no_structural_problem():
    """The positive control: a check that flagged everything would pass the
    test above while blocking every real spec."""
    assert spec_closure.structural_problems(closure_of(FEATURE)) == []


def test_a_duplicate_authored_slug_is_ambiguous_rather_than_resolved():
    """One slug matching two elements has no single answer, and picking the
    first would bind an approval to file order."""
    doubled = FEATURE + """
    @scenario:unapproved-blocked
    Scenario: A different scenario wearing the same tag
      Given a drafted response
      When the representative sends it
      Then something else happens
"""
    doc = spec_closure.parse_feature(doubled)

    with pytest.raises(spec_closure.AmbiguousReference):
        spec_closure.resolve(doc, "scenario", "unapproved-blocked")


def test_an_element_with_no_authored_tag_does_not_resolve():
    """`id_source: derived` is rejected by the contract — a slugified name is
    stable only as long as the name is, so binding an approval to one binds it
    to a rename."""
    untagged = FEATURE.replace("    @scenario:unapproved-blocked\n", "")
    doc = spec_closure.parse_feature(untagged)

    assert spec_closure.resolve(doc, "scenario", "unapproved-blocked") is None


# --- review of PR #160 -------------------------------------------------------

def test_the_parser_is_a_declared_dependency():
    """`parse_feature` refuses without gherkin-official, and CI installs only
    the declared extras — so an undeclared parser turns every test in this
    module red on a clean checkout. It was undeclared."""
    import pathlib
    import tomllib

    config = tomllib.loads(pathlib.Path("pyproject.toml").read_text(encoding="utf-8"))
    extras = config["project"]["optional-dependencies"]
    declared = " ".join(extras.get("test", []) + extras.get("baseline", []))

    assert "gherkin-official" in declared


def test_table_cells_cannot_be_confused_by_their_separator():
    """`a|b` in one cell and `a`,`b` in two cells are different step inputs.
    Joining cells with a bare pipe made them serialize identically, so two
    materially different tables shared a digest."""
    # An *escaped* pipe is a literal inside one cell; an unescaped one is a
    # separator. So the colliding pair is two cells `a|b`,`c` against three
    # cells `a`,`b`,`c` — a first version of this test used the unescaped
    # form, which the parser simply reads as three cells either way.
    two_cells = FEATURE.replace(
        "      Then the send is refused",
        "      Then the send is refused\n        | a\\|b | c |",
    )
    three_cells = FEATURE.replace(
        "      Then the send is refused",
        "      Then the send is refused\n        | a | b | c |",
    )

    assert digest_of(two_cells) != digest_of(three_cells)


def test_a_docstring_media_type_is_part_of_the_payload():
    """The same bytes marked json and marked yaml are read differently by
    whatever consumes them."""
    as_json = FEATURE.replace(
        "      Then the send is refused",
        '      Then the body is:\n        """json\n        a: 1\n        """',
    )
    as_yaml = as_json.replace('"""json', '"""yaml')

    assert digest_of(as_json) != digest_of(as_yaml)


def test_a_duplicate_examples_row_is_not_a_change():
    """Rows compare as a set — the documented semantics — and a duplicate row
    runs the scenario twice on identical inputs, covering nothing new. Sorting
    without deduplicating made an unchanged input domain read as semantic."""
    outline = FEATURE.replace(
        """    Scenario: An unapproved response cannot be sent
      Given a drafted response""",
        """    Scenario Outline: An unapproved response cannot be sent
      Given a <state> response""",
    ) + """
      Examples:
        | state   |
        | drafted |
"""
    duplicated = outline + "        | drafted |\n"

    assert digest_of(duplicated) == digest_of(outline)


def test_a_header_only_examples_block_is_a_structural_problem():
    """Checked per block, not in aggregate: an outline with one populated
    block and one header-only block has a non-empty aggregate, so the empty
    block sailed through the refusal it was supposed to trip."""
    outline = FEATURE.replace(
        """    Scenario: An unapproved response cannot be sent
      Given a drafted response""",
        """    Scenario Outline: An unapproved response cannot be sent
      Given a <state> response""",
    ) + """
      Examples: populated
        | state   |
        | drafted |

      Examples: empty
        | state   |
"""

    problems = spec_closure.structural_problems(closure_of(outline))

    assert any("Examples" in p for p in problems), problems


def test_a_tag_on_an_examples_block_is_part_of_the_closure():
    """Gherkin allows tags on an Examples block, and one can bind those
    generated cases to a gate. Discarding them let a gate change pass with an
    unchanged digest."""
    outline = FEATURE.replace(
        """    Scenario: An unapproved response cannot be sent
      Given a drafted response""",
        """    Scenario Outline: An unapproved response cannot be sent
      Given a <state> response""",
    ) + """
      @slow
      Examples:
        | state   |
        | drafted |
"""
    retagged = outline.replace("      @slow", "      @v2")

    assert digest_of(outline) != digest_of(retagged)
