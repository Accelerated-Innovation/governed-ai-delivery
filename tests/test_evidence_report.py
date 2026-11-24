"""`govkit evidence --feature`: scenarios bound to test results, and the JSON report.

A feature is done when its own scenarios passed, so the report starts from the
scenarios in `acceptance.feature` and looks for a result for each one. A
scenario with no result is missing, which is not a pass.
"""

import json
from pathlib import Path

import pytest

from cli import evidence_report as er
from cli import paths, scenario_identity
from cli.evidence import Outcome
from cli.schema_validation import validate_document

FEATURE = "07_invoice_approval"
ACCEPTANCE = """Feature: Invoice approval routing

  @mvp @scenario:approval-routing-by-amount
  Scenario: Invoice amount decides the approval path
    Given an invoice of 12000
    Then it is routed to the finance manager

  Scenario Outline: Amount <amount> goes to <approver>
    Given an invoice of <amount>
    Then it goes to <approver>

    Examples:
      | amount | approver |
      | 100    | clerk    |
      | 20000  | manager  |

  @nfr-performance
  Scenario: Routing completes within 200 ms at p95
    Given 100 invoices
    Then routing takes at most 200 ms at p95
"""
BY_ID = f"{FEATURE}#scenario:approval-routing-by-amount"
OUTLINE = f"{FEATURE}#scenario:amount-amount-goes-to-approver"
NFR = f"{FEATURE}#scenario:routing-completes-within-200-ms-at-p95"
# The names pytest-bdd gives the three scenarios above.
PASSING = [
    ("test_invoice_amount_decides_the_approval_path", "pass", None),
    ("test_amount_amount_goes_to_approver[100-clerk]", "pass", None),
    ("test_amount_amount_goes_to_approver[20000-manager]", "pass", None),
    ("test_routing_completes_within_200_ms_at_p95", "pass", None),
]
_CHILD = {
    "pass": "",
    "fail": '<failure message="boom">trace</failure>',
    "error": '<error message="broke">trace</error>',
    "skip": '<skipped message="not today"/>',
}


def _project(tmp_path: Path, acceptance: str | None = ACCEPTANCE, feature: str = FEATURE) -> Path:
    directory = tmp_path / "features" / feature
    directory.mkdir(parents=True)
    if acceptance is not None:
        (directory / "acceptance.feature").write_text(acceptance, encoding="utf-8")
    return tmp_path


def _junit(tmp_path: Path, cases, name: str = "junit.xml", attributes: str = "") -> None:
    """cases = [(test name, "pass" | "fail" | "error" | "skip", govkit.scenario value or None)]"""
    body = ""
    for test, status, scenario in cases:
        properties = (
            f'<properties><property name="govkit.scenario" value="{scenario}"/></properties>'
            if scenario
            else ""
        )
        body += f'<testcase classname="tests.routing" name="{test}" time="0.01">'
        body += f"{properties}{_CHILD[status]}</testcase>"
    count = {s: sum(1 for _, status, _ in cases if status == s) for s in _CHILD}
    (tmp_path / name).write_text(
        f'<?xml version="1.0"?><testsuites><testsuite name="pytest" tests="{len(cases)}" '
        f'failures="{count["fail"]}" errors="{count["error"]}" skipped="{count["skip"]}"'
        f"{attributes}>{body}</testsuite></testsuites>",
        encoding="utf-8",
    )


def _report(target: Path, feature: str = FEATURE) -> dict:
    return er.build_report(target, feature)


def _result(report: dict, requirement: str) -> dict:
    return next(r for r in report["results"] if r["requirement_id"] == requirement)


class TestBinding:
    def test_every_scenario_is_listed_in_source_order(self, tmp_path):
        report = _report(_project(tmp_path))
        assert [r["requirement_id"] for r in report["results"]] == [BY_ID, OUTLINE, NFR]

    def test_a_scenario_with_no_result_is_missing(self, tmp_path):
        report = _report(_project(tmp_path))
        assert {r["outcome"] for r in report["results"]} == {"missing"}
        assert {r["binding"] for r in report["results"]} == {"none"}

    def test_a_test_is_bound_by_its_title(self, tmp_path):
        _junit(tmp_path, PASSING)
        result = _result(_report(_project(tmp_path)), BY_ID)
        assert (result["outcome"], result["binding"]) == ("passed", "title")

    def test_an_outline_binds_every_example(self, tmp_path):
        _junit(tmp_path, PASSING)
        result = _result(_report(_project(tmp_path)), OUTLINE)
        assert result["outcome"] == "passed"
        assert len(result["tests"]) == 2

    def test_a_scenario_takes_the_worst_of_its_tests(self, tmp_path):
        cases = list(PASSING)
        cases[2] = ("test_amount_amount_goes_to_approver[20000-manager]", "fail", None)
        _junit(tmp_path, cases)
        assert _result(_report(_project(tmp_path)), OUTLINE)["outcome"] == "failed"

    @pytest.mark.parametrize(
        "statuses, expected",
        [
            (("pass", "skip"), "skipped"),
            (("skip", "fail"), "failed"),
            (("fail", "error"), "error"),
            (("pass", "pass"), "passed"),
        ],
    )
    def test_worst_is_error_then_failed_then_skipped(self, tmp_path, statuses, expected):
        _junit(
            tmp_path,
            [
                (f"test_amount_amount_goes_to_approver[{n}]", s, None)
                for n, s in enumerate(statuses)
            ],
        )
        assert _result(_report(_project(tmp_path)), OUTLINE)["outcome"] == expected

    def test_a_property_with_the_full_id_binds(self, tmp_path):
        _junit(tmp_path, [("test_anything_at_all", "pass", BY_ID)])
        result = _result(_report(_project(tmp_path)), BY_ID)
        assert (result["outcome"], result["binding"]) == ("passed", "id")

    def test_a_property_with_the_tag_binds(self, tmp_path):
        _junit(tmp_path, [("test_anything", "pass", "@scenario:approval-routing-by-amount")])
        result = _result(_report(_project(tmp_path)), BY_ID)
        assert (result["outcome"], result["binding"]) == ("passed", "tag")

    def test_a_property_is_preferred_to_a_title(self, tmp_path):
        """A project that states the scenario is believed over a name that happens to match."""
        _junit(
            tmp_path,
            [
                ("test_invoice_amount_decides_the_approval_path", "pass", None),
                ("test_the_real_one", "fail", BY_ID),
            ],
        )
        result = _result(_report(_project(tmp_path)), BY_ID)
        assert (result["outcome"], result["binding"]) == ("failed", "id")
        assert [t["name"] for t in result["tests"]] == ["test_the_real_one"]

    def test_a_test_that_names_another_scenario_is_not_bound_by_title(self, tmp_path):
        other = "99_other#scenario:something-else"
        _junit(tmp_path, [("test_invoice_amount_decides_the_approval_path", "pass", other)])
        assert _result(_report(_project(tmp_path)), BY_ID)["outcome"] == "missing"

    def test_another_features_id_does_not_bind(self, tmp_path):
        _junit(tmp_path, [("test_x", "pass", "99_other#scenario:approval-routing-by-amount")])
        assert _result(_report(_project(tmp_path)), BY_ID)["outcome"] == "missing"

    def test_titles_that_reduce_to_the_same_name_are_not_bound_by_title(self, tmp_path):
        acceptance = (
            "Feature: F\n  Scenario: Re-send the invoice\n    Then ok\n"
            "  Scenario: Resend the invoice\n    Then ok\n"
        )
        _junit(tmp_path, [("test_resend_the_invoice", "pass", None)])
        report = _report(_project(tmp_path, acceptance))
        assert {r["outcome"] for r in report["results"]} == {"missing"}
        assert all("same test name" in r["note"] for r in report["results"])

    def test_a_leading_number_in_a_title_is_ignored_as_pytest_bdd_does(self, tmp_path):
        acceptance = "Feature: F\n  Scenario: 100% coverage (v2)\n    Then ok\n"
        _junit(tmp_path, [("test_coverage_v2", "pass", None)])
        assert _report(_project(tmp_path, acceptance))["results"][0]["outcome"] == "passed"

    def test_results_are_read_from_every_report_file(self, tmp_path):
        _junit(tmp_path, PASSING[:1], name="junit-unit.xml")
        _junit(tmp_path, PASSING[1:], name="junit-acceptance.xml")
        report = _report(_project(tmp_path))
        assert {r["outcome"] for r in report["results"]} == {"passed"}
        assert sorted(s["path"] for s in report["sources"]) == [
            "junit-acceptance.xml",
            "junit-unit.xml",
        ]


class TestOutcome:
    def test_pass_when_every_scenario_passed(self, tmp_path):
        _junit(tmp_path, PASSING)
        report = _report(_project(tmp_path))
        assert report["outcome"] == "PASS", report["detail"]
        assert report["summary"] == {
            "scenarios": 3,
            "passed": 3,
            "failed": 0,
            "error": 0,
            "skipped": 0,
            "missing": 0,
        }

    def test_fail_when_a_scenario_failed(self, tmp_path):
        cases = list(PASSING)
        cases[0] = (cases[0][0], "fail", None)
        _junit(tmp_path, cases)
        assert _report(_project(tmp_path))["outcome"] == "FAIL"

    def test_error_is_reported_ahead_of_fail(self, tmp_path):
        cases = list(PASSING)
        cases[0] = (cases[0][0], "fail", None)
        cases[3] = (cases[3][0], "error", None)
        _junit(tmp_path, cases)
        assert _report(_project(tmp_path))["outcome"] == "ERROR"

    def test_fail_is_reported_ahead_of_missing(self, tmp_path):
        _junit(tmp_path, [(PASSING[0][0], "fail", None)])
        assert _report(_project(tmp_path))["outcome"] == "FAIL"

    @pytest.mark.parametrize("status", ["skip", None])
    def test_inconclusive_when_a_scenario_is_skipped_or_missing(self, tmp_path, status):
        cases = list(PASSING[:3])
        if status:
            cases.append((PASSING[3][0], status, None))
        _junit(tmp_path, cases)
        report = _report(_project(tmp_path))
        assert report["outcome"] == "INCONCLUSIVE"
        assert "routing-completes-within-200-ms-at-p95" in report["detail"]

    def test_inconclusive_when_there_is_no_test_report(self, tmp_path):
        report = _report(_project(tmp_path))
        assert report["outcome"] == "INCONCLUSIVE"
        assert report["sources"] == []

    def test_inconclusive_when_the_feature_has_no_acceptance_file(self, tmp_path):
        report = _report(_project(tmp_path, acceptance=None))
        assert report["outcome"] == "INCONCLUSIVE"
        assert "acceptance.feature" in report["detail"]
        assert report["results"] == []

    def test_inconclusive_when_the_feature_has_no_scenarios(self, tmp_path):
        report = _report(_project(tmp_path, "Feature: Empty\n"))
        assert report["outcome"] == "INCONCLUSIVE"

    def test_error_when_the_feature_file_cannot_be_identified(self, tmp_path):
        acceptance = "Feature: F\n  @scenario:Bad_Slug\n  Scenario: S\n    Then ok\n"
        report = _report(_project(tmp_path, acceptance))
        assert report["outcome"] == "ERROR"
        assert "invalid_identifier" in report["detail"]

    def test_error_when_a_test_report_cannot_be_parsed(self, tmp_path):
        (tmp_path / "junit.xml").write_text("<not-xml", encoding="utf-8")
        report = _report(_project(tmp_path))
        assert report["outcome"] == "ERROR"
        assert "junit.xml" in report["detail"]

    def test_unmarked_skips_cannot_produce_a_pass(self, tmp_path):
        """A suite that counts a skip no test case shows could be hiding it
        behind any of the cases that look passed."""
        _junit(tmp_path, PASSING)
        text = (tmp_path / "junit.xml").read_text(encoding="utf-8")
        (tmp_path / "junit.xml").write_text(
            text.replace('skipped="0"', 'skipped="1"'), encoding="utf-8"
        )
        report = _report(_project(tmp_path))
        assert report["outcome"] == "INCONCLUSIVE"
        assert "not marked" in report["detail"]

    def test_a_symlinked_acceptance_file_is_not_read(self, tmp_path):
        target = _project(tmp_path, acceptance=None)
        outside = tmp_path / "elsewhere.feature"
        outside.write_text(ACCEPTANCE, encoding="utf-8")
        (target / "features" / FEATURE / "acceptance.feature").symlink_to(outside)
        report = _report(target)
        assert report["outcome"] == "ERROR"
        assert "symbolic link" in report["detail"]


class TestReportContent:
    def test_a_result_carries_identity_revision_and_tags(self, tmp_path):
        _junit(tmp_path, PASSING)
        result = _result(_report(_project(tmp_path)), BY_ID)
        expected = scenario_identity.read_scenarios(FEATURE, ACCEPTANCE.encode())[0]
        assert result["revision_digest"] == expected.revision_digest
        assert result["kind"] == "test"
        assert result["id_source"] == "tag"
        assert result["tags"] == ["@mvp", "@scenario:approval-routing-by-amount"]
        assert result["title"] == "Invoice amount decides the approval path"

    def test_a_bound_test_names_its_report_file(self, tmp_path):
        _junit(tmp_path, PASSING)
        test = _result(_report(_project(tmp_path)), BY_ID)["tests"][0]
        assert test == {
            "name": "test_invoice_amount_decides_the_approval_path",
            "classname": "tests.routing",
            "outcome": "passed",
            "source": "junit.xml",
        }

    def test_the_feature_names_its_definition_and_digest(self, tmp_path):
        import hashlib

        report = _report(_project(tmp_path))
        assert report["feature"] == {
            "name": FEATURE,
            "definition": "features/07_invoice_approval/acceptance.feature",
            "content_digest": hashlib.sha256(ACCEPTANCE.encode()).hexdigest(),
        }

    def test_a_source_carries_its_digest(self, tmp_path):
        import hashlib

        _junit(tmp_path, PASSING)
        source = _report(_project(tmp_path))["sources"][0]
        assert source["tool"] == "junit"
        assert (
            source["content_digest"]
            == hashlib.sha256((tmp_path / "junit.xml").read_bytes()).hexdigest()
        )

    @pytest.mark.parametrize("scenario", ["passing", "empty", "refused", "no-definition"])
    def test_every_report_validates_against_the_bundled_schema(self, tmp_path, scenario):
        acceptance = {
            "passing": ACCEPTANCE,
            "empty": ACCEPTANCE,
            "refused": "Feature: One\nFeature: Two\n",
            "no-definition": None,
        }[scenario]
        if scenario == "passing":
            _junit(tmp_path, PASSING)
        validate_document(_report(_project(tmp_path, acceptance)), er.SCHEMA)

    def test_the_bundled_example_validates_and_is_a_real_report(self, tmp_path):
        """The example is what this code prints for the example's own inputs."""
        example_dir = paths.GOVERNANCE_DIR / "examples" / "evidence-report"
        example = json.loads((example_dir / "evidence-report.json").read_text(encoding="utf-8"))
        validate_document(example, er.SCHEMA)
        directory = tmp_path / "features" / example["feature"]["name"]
        directory.mkdir(parents=True)
        (directory / "acceptance.feature").write_bytes(
            (example_dir / "acceptance.feature").read_bytes()
        )
        (tmp_path / "junit.xml").write_bytes((example_dir / "test-run.xml").read_bytes())
        assert _report(tmp_path, example["feature"]["name"]) == example

    def test_the_report_is_the_same_on_a_second_run(self, tmp_path):
        _junit(tmp_path, PASSING)
        target = _project(tmp_path)
        assert _report(target) == _report(target)


class TestSelection:
    def test_an_unknown_feature_is_an_error_that_lists_the_features(self, tmp_path):
        _project(tmp_path)
        with pytest.raises(er.SelectionError) as error:
            er.build_report(tmp_path, "nope")
        assert "nope" in str(error.value) and FEATURE in str(error.value)

    def test_a_project_without_features_is_an_error(self, tmp_path):
        with pytest.raises(er.SelectionError):
            er.build_report(tmp_path, FEATURE)

    @pytest.mark.parametrize("name", ["../features/07_invoice_approval", ".", ""])
    def test_a_name_is_a_directory_name_not_a_path(self, tmp_path, name):
        _project(tmp_path)
        with pytest.raises(er.SelectionError):
            er.build_report(tmp_path, name)


class TestText:
    def test_the_text_lists_each_scenario_and_the_outcome(self, tmp_path):
        cases = list(PASSING[:3])
        _junit(tmp_path, cases)
        text = er.render_text(_report(_project(tmp_path)))
        assert "approval-routing-by-amount" in text
        assert "missing" in text.lower()
        assert "INCONCLUSIVE" in text

    def test_the_text_says_what_a_passing_nfr_scenario_does_not_show(self, tmp_path):
        _junit(tmp_path, PASSING)
        text = er.render_text(_report(_project(tmp_path)))
        assert "@nfr-performance" in text
        assert "asserts the value" in text

    def test_no_nfr_note_without_nfr_scenarios(self, tmp_path):
        text = er.render_text(
            _report(_project(tmp_path, "Feature: F\n  Scenario: S\n    Then ok\n"))
        )
        assert "asserts the value" not in text

    def test_exit_code_is_zero_only_on_pass(self, tmp_path):
        target = _project(tmp_path)
        assert er.exit_code(_report(target)) == 1
        _junit(tmp_path, PASSING)
        assert er.exit_code(_report(target)) == 0
        assert Outcome(_report(target)["outcome"]) is Outcome.PASS


class TestReviewCases:
    def test_id_and_tag_bindings_are_combined(self, tmp_path):
        """Both tests name the scenario, so the failing one cannot be dropped."""
        _junit(
            tmp_path,
            [
                ("test_one", "pass", BY_ID),
                ("test_two", "fail", "@scenario:approval-routing-by-amount"),
            ],
        )
        result = _result(_report(_project(tmp_path)), BY_ID)
        assert (result["outcome"], result["binding"]) == ("failed", "id")
        assert len(result["tests"]) == 2

    def test_a_marked_skip_in_one_suite_does_not_hide_an_unmarked_one_in_another(self, tmp_path):
        (tmp_path / "junit.xml").write_text(
            '<testsuites><testsuite name="a" tests="1" skipped="1">'
            '<testcase name="test_target" time="0.0"/></testsuite>'
            '<testsuite name="b" tests="1"><testcase name="test_other" time="0.0">'
            "<skipped/></testcase></testsuite></testsuites>",
            encoding="utf-8",
        )
        report = _report(_project(tmp_path, "Feature: F\n  Scenario: Target\n    Then ok\n"))
        assert report["sources"][0]["unidentified_skipped"] == 1
        assert report["outcome"] == "INCONCLUSIVE", report["detail"]

    def test_the_bundled_example_is_not_discovered_as_a_test_result(self):
        """A checked-in example must not read as this repository's own evidence."""
        from cli.evidence import _JUNIT_GLOBS, _find

        found = _find(paths.GOVERNANCE_DIR / "examples" / "evidence-report", _JUNIT_GLOBS)
        assert found == []


def test_an_unmarked_skip_in_a_nested_suite_under_a_suite_root_is_seen(tmp_path):
    (tmp_path / "junit.xml").write_text(
        '<testsuite name="outer" tests="1"><testsuite name="inner" tests="1" skipped="1">'
        '<testcase name="test_target" time="0.0"/></testsuite></testsuite>',
        encoding="utf-8",
    )
    report = _report(_project(tmp_path, "Feature: F\n  Scenario: Target\n    Then ok\n"))
    assert report["sources"][0]["unidentified_skipped"] == 1
    assert report["outcome"] == "INCONCLUSIVE", report["detail"]


def test_suites_nested_too_deeply_are_an_error_in_the_feature_report(tmp_path):
    depth = 20000
    (tmp_path / "junit.xml").write_text(
        '<testsuite tests="1">' * depth + '<testcase name="a"/>' + "</testsuite>" * depth,
        encoding="utf-8",
    )
    report = _report(_project(tmp_path))
    assert report["outcome"] == "ERROR"
    assert "nested" in report["detail"]
