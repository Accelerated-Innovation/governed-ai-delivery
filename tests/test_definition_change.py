"""A change cannot weaken the scenarios and criteria it is judged by.

The module under test is pure: the definition files as they were at the
comparison base, as they are now, and the paths that changed. A finding means
a person must look; it is never a judgement that the edit made things worse.
"""

import pytest

from cli import definition_change as dc

ACCEPTANCE = "features/07_invoice/acceptance.feature"
CRITERIA = "features/07_invoice/eval_criteria.yaml"

FEATURE = """Feature: Invoice approval

  Background:
    Given a signed-in clerk

  @scenario:routing
  Scenario: Amount decides the path
    Given an invoice of 12000
    Then it goes to the finance manager

  Scenario: Rejected invoices return
    Given a rejected invoice
    Then it returns to its author

  Rule: Large invoices need two approvers

    Background:
      Given the two-approver policy is on

    Scenario: A large invoice waits for the second approver
      Given an invoice of 90000
      Then it waits for a second approver
"""

YAML = """version: 1
llm_evaluation:
  criteria:
    - name: faithfulness
      threshold: 0.9
criteria:
  - name: p95-latency
    target: {metric: p95_latency, comparator: "<=", value: 0.2, unit: seconds}
"""


def _assess(before: str | None, after: str | None, path: str = ACCEPTANCE) -> dc.Assessment:
    base = {} if before is None else {path: before.encode()}
    now = {} if after is None else {path: after.encode()}
    return dc.assess(base, now, [path])


def _codes(assessment: dc.Assessment) -> list[tuple[str, str | None]]:
    return [(finding.code, finding.requirement) for finding in assessment.findings]


class TestWhichFiles:
    def test_definition_files_are_selected_by_their_place(self):
        paths = [
            ACCEPTANCE,
            CRITERIA,
            "features/07_invoice/plan.md",
            "features/acceptance.feature",
            "src/features/07_invoice/acceptance.feature",
            "features/07_invoice/nested/acceptance.feature",
        ]
        assert dc.definition_paths(paths) == (ACCEPTANCE, CRITERIA)

    def test_only_changed_definition_files_are_assessed(self):
        result = dc.assess({"src/a.py": b"1"}, {"src/a.py": b"2"}, ["src/a.py"])
        assert (result.checked, result.findings, result.unknown) == ((), (), ())


class TestScenarios:
    def test_an_unchanged_file_has_no_finding(self):
        assert _assess(FEATURE, FEATURE).findings == ()

    def test_adding_a_scenario_is_allowed(self):
        added = FEATURE + "\n    Scenario: A new case\n      Given something new\n"
        result = _assess(FEATURE, added)
        assert result.findings == () and result.checked == (ACCEPTANCE,)

    def test_a_new_file_is_allowed(self):
        assert _assess(None, FEATURE).findings == ()

    def test_a_comment_or_trailing_space_is_not_a_change(self):
        """The revision digest ignores them, so they are not an alteration here either."""
        edited = FEATURE.replace("  @scenario:routing", "  # why this matters\n  @scenario:routing")
        assert _assess(FEATURE, edited.replace("12000", "12000  ")).findings == ()

    def test_a_removed_scenario_is_a_finding(self):
        start = FEATURE.index("  Scenario: Rejected")
        end = FEATURE.index("  Rule:")
        result = _assess(FEATURE, FEATURE[:start] + FEATURE[end:])
        assert _codes(result) == [
            ("scenario-removed", "07_invoice#scenario:rejected-invoices-return")
        ]
        assert result.findings[0].path == ACCEPTANCE

    def test_an_altered_scenario_is_a_finding(self):
        result = _assess(FEATURE, FEATURE.replace("12000", "1"))
        assert _codes(result) == [("scenario-altered", "07_invoice#scenario:routing")]

    def test_retitling_a_derived_scenario_removes_the_one_that_was_there(self):
        result = _assess(FEATURE, FEATURE.replace("Rejected invoices return", "Rejections"))
        assert _codes(result) == [
            ("scenario-removed", "07_invoice#scenario:rejected-invoices-return")
        ]

    def test_a_deleted_file_is_a_finding(self):
        assert _codes(_assess(FEATURE, None)) == [("definition-removed", None)]

    def test_a_file_that_can_no_longer_be_identified_is_a_finding(self):
        result = _assess(FEATURE, FEATURE + "\nFeature: A second one\n")
        assert _codes(result) == [("definition-unreadable", None)]

    def test_a_base_that_cannot_be_identified_is_unknown_not_a_pass(self):
        result = _assess("Scenario: no feature\n", FEATURE)
        assert result.findings == ()
        assert len(result.unknown) == 1 and ACCEPTANCE in result.unknown[0]


class TestSharedSteps:
    """A `Background` is in no scenario's digest, and runs before every one it covers."""

    def test_a_changed_feature_background_is_a_finding_for_what_it_covers(self):
        result = _assess(FEATURE, FEATURE.replace("a signed-in clerk", "anyone"))
        assert [f.code for f in result.findings] == ["shared-steps-changed"] * 3

    def test_a_changed_rule_background_covers_only_that_rule(self):
        result = _assess(FEATURE, FEATURE.replace("policy is on", "policy is off"))
        assert _codes(result) == [
            (
                "shared-steps-changed",
                "07_invoice#scenario:a-large-invoice-waits-for-the-second-approver",
            )
        ]

    def test_a_removed_background_is_a_finding(self):
        removed = FEATURE.replace("  Background:\n    Given a signed-in clerk\n\n", "", 1)
        assert [f.code for f in _assess(FEATURE, removed).findings] == ["shared-steps-changed"] * 3

    def test_a_background_added_above_existing_scenarios_is_a_finding(self):
        plain = "Feature: F\n\n  Scenario: One\n    Given a\n"
        added = "Feature: F\n\n  Background:\n    Given b\n\n  Scenario: One\n    Given a\n"
        assert _codes(_assess(plain, added)) == [
            ("shared-steps-changed", "07_invoice#scenario:one")
        ]

    def test_moving_a_scenario_under_another_background_is_a_finding(self):
        start = FEATURE.index("  Scenario: Rejected")
        end = FEATURE.index("  Rule:")
        moved = FEATURE[:start] + FEATURE[end:] + "\n" + FEATURE[start:end]
        assert _codes(_assess(FEATURE, moved)) == [
            ("shared-steps-changed", "07_invoice#scenario:rejected-invoices-return")
        ]

    def test_a_background_that_covers_only_new_scenarios_is_allowed(self):
        added = FEATURE + (
            "\n  Rule: A new rule\n\n    Background:\n      Given c\n\n"
            "    Scenario: New\n      Given d\n"
        )
        assert _assess(FEATURE, added).findings == ()

    def test_an_altered_scenario_is_reported_once(self):
        edited = FEATURE.replace("a signed-in clerk", "anyone").replace("12000", "1")
        codes = _codes(_assess(FEATURE, edited))
        assert ("scenario-altered", "07_invoice#scenario:routing") in codes
        assert ("shared-steps-changed", "07_invoice#scenario:routing") not in codes


class TestCriteria:
    def _assess(self, before, after):
        return _assess(before, after, path=CRITERIA)

    def test_adding_a_criterion_is_allowed(self):
        added = YAML + "  - name: refusal-safety\n    threshold: 0.99\n"
        assert self._assess(YAML, added).findings == ()

    def test_reordering_and_reformatting_are_allowed(self):
        other = YAML.replace(
            'target: {metric: p95_latency, comparator: "<=", value: 0.2, unit: seconds}',
            "target:\n      unit: seconds\n      value: 0.2\n      comparator: '<='\n"
            "      metric: p95_latency",
        )
        assert self._assess(YAML, other).findings == ()

    def test_a_lowered_threshold_is_a_finding(self):
        result = self._assess(YAML, YAML.replace("0.9", "0.5"))
        assert _codes(result) == [("criterion-altered", "07_invoice#evaluation:faithfulness")]

    def test_a_loosened_target_is_a_finding(self):
        result = self._assess(YAML, YAML.replace("value: 0.2", "value: 2"))
        assert _codes(result) == [("criterion-altered", "07_invoice#evaluation:p95-latency")]

    def test_a_removed_criterion_is_a_finding(self):
        removed = YAML[: YAML.index("criteria:\n  - name: p95")] + "criteria: []\n"
        result = self._assess(YAML, removed)
        assert _codes(result) == [("criterion-removed", "07_invoice#evaluation:p95-latency")]

    def test_moving_a_criterion_between_lists_is_a_finding(self):
        """The same name under another list is judged by another rule."""
        moved = (
            "version: 1\nllm_evaluation:\n  criteria: []\ncriteria:\n"
            "  - name: faithfulness\n    threshold: 0.9\n  - name: p95-latency\n"
            '    target: {metric: p95_latency, comparator: "<=", value: 0.2, unit: seconds}\n'
        )
        assert ("criterion-removed", "07_invoice#evaluation:faithfulness") in _codes(
            self._assess(YAML, moved)
        )

    def test_a_change_outside_the_criteria_is_a_finding(self):
        result = self._assess(YAML, YAML.replace("version: 1", "version: 2"))
        assert _codes(result) == [("criteria-changed", None)]

    def test_a_deleted_file_is_a_finding(self):
        assert _codes(self._assess(YAML, None)) == [("definition-removed", None)]

    def test_a_file_that_can_no_longer_be_read_is_a_finding(self):
        assert _codes(self._assess(YAML, "criteria: [")) == [("definition-unreadable", None)]
        assert _codes(self._assess(YAML, "- a list\n")) == [("definition-unreadable", None)]

    def test_criteria_not_in_the_named_form_cannot_be_compared_item_by_item(self):
        data = "criteria:\n  - id: C1\n    predicate: rows are unique\n"
        result = self._assess(data, data + "  - id: C2\n    predicate: no nulls\n")
        assert _codes(result) == [("criteria-changed", None)]
        assert "item by item" in result.findings[0].message

    def test_a_base_that_cannot_be_read_is_unknown(self):
        result = self._assess("criteria: [", YAML)
        assert result.findings == () and len(result.unknown) == 1

    def test_duplicate_names_at_the_base_are_unknown(self):
        twice = "criteria:\n  - name: a\n    threshold: 1\n  - name: a\n    threshold: 0\n"
        result = self._assess(twice, "criteria:\n  - name: a\n    threshold: 0\n")
        assert result.findings == () and len(result.unknown) == 1


class TestContract:
    def test_every_code_is_listed(self):
        assert dc.CODES == (
            "scenario-removed",
            "scenario-altered",
            "shared-steps-changed",
            "criterion-removed",
            "criterion-altered",
            "criteria-changed",
            "definition-removed",
            "definition-unreadable",
        )

    def test_a_message_names_the_file_and_holds_no_step_text(self):
        result = _assess(FEATURE, FEATURE.replace("12000", "1"))
        message = result.findings[0].message
        assert ACCEPTANCE in message and "routing" in message
        assert "12000" not in message and "finance" not in message

    @pytest.mark.parametrize("size", [dc.MAX_BYTES + 1])
    def test_an_oversized_file_is_not_parsed(self, size):
        big = FEATURE + "#" * size
        assert len(_assess(big, FEATURE).unknown) == 1
        assert _codes(_assess(FEATURE, big)) == [("definition-unreadable", None)]


class TestReviewOfCriteriaComparison:
    def _assess(self, before, after):
        return _assess(before, after, path=CRITERIA)

    def test_the_same_number_written_another_way_is_not_a_change(self):
        base = "criteria:\n  - name: a\n    threshold: 1\n"
        assert self._assess(base, base.replace("threshold: 1", "threshold: 1.0")).findings == ()

    @pytest.mark.parametrize("value", ["true", '"1"'])
    def test_a_change_of_type_alone_is_an_alteration(self, value):
        """`True == 1` in Python, and a boolean threshold is no threshold at all."""
        base = "criteria:\n  - name: a\n    threshold: 1\n"
        result = self._assess(base, base.replace("threshold: 1", f"threshold: {value}"))
        assert _codes(result) == [("criterion-altered", "07_invoice#evaluation:a")]

    def test_a_change_of_type_outside_the_criteria_is_a_finding(self):
        base = "enabled: 1\ncriteria:\n  - name: a\n    threshold: 1\n"
        assert _codes(self._assess(base, base.replace("enabled: 1", "enabled: true"))) == [
            ("criteria-changed", None)
        ]

    def test_a_change_of_type_in_an_unnamed_criterion_is_a_finding(self):
        base = "criteria:\n  - id: C1\n    limit: 0\n"
        assert _codes(self._assess(base, base.replace("limit: 0", "limit: false"))) == [
            ("criteria-changed", None)
        ]

    def test_the_first_llm_criterion_may_be_added(self):
        base = "criteria:\n  - name: a\n    threshold: 1\n"
        added = base + "llm_evaluation:\n  criteria:\n    - name: b\n      threshold: 0.9\n"
        assert self._assess(base, added).findings == ()

    def test_other_llm_settings_stay_protected(self):
        base = "criteria:\n  - name: a\n    threshold: 1\n"
        added = base + "llm_evaluation:\n  judge: lenient\n  criteria: []\n"
        assert _codes(self._assess(base, added)) == [("criteria-changed", None)]

    def test_values_json_cannot_hold_are_still_compared(self):
        base = "reviewed: 2026-11-01\ncriteria:\n  - name: a\n    threshold: 1\n"
        assert self._assess(base, base).findings == ()
        assert _codes(self._assess(base, base.replace("11-01", "11-02"))) == [
            ("criteria-changed", None)
        ]


def test_adjacent_large_integers_are_different_thresholds():
    """A float cannot tell them apart; the comparison must."""
    base = "criteria:\n  - name: a\n    threshold: 9007199254740993\n"
    result = _assess(base, base.replace("0993", "0992"), path=CRITERIA)
    assert _codes(result) == [("criterion-altered", "07_invoice#evaluation:a")]
    assert _assess(base, base, path=CRITERIA).findings == ()


def test_a_value_that_is_not_a_number_equals_itself():
    base = "criteria:\n  - name: a\n    threshold: .nan\n    limit: .inf\n"
    assert _assess(base, base + "# a comment\n", path=CRITERIA).findings == ()
