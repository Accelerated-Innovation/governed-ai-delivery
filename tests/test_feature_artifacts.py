"""Feature artifact checks chosen from the accepted profile, not a level (L07b)."""

import pytest

from cli import feature_artifacts as fa
from cli import validate
from cli.check_models import State
from tests.test_validate import make_full_feature
from tests.test_validate_scope import GOOD_ACCEPTANCE

FEATURE = "07_good"
BASE = ("application-governance", "gherkin-delivery")
CRITERIA = """version: 1
mode: deterministic
unit_tests:
  enforce_FIRST: true
  minimum_FIRST_average: 4
code_quality:
  enforce_virtues: true
  minimum_virtue_average: 4
"""


def _project(tmp_path, **files):
    files.setdefault("acceptance.feature", GOOD_ACCEPTANCE)
    files.setdefault("eval_criteria.yaml", CRITERIA)
    make_full_feature(tmp_path / "features" / FEATURE, **files)
    return tmp_path


def _run(target, capabilities=BASE, project_type="api"):
    return {
        name: (required, check(None))
        for name, required, check in fa.checks(target, FEATURE, capabilities, project_type)
    }


def _states(results):
    return {name: outcome.state for name, (_, outcome) in results.items()}


class TestSelection:
    def test_nothing_without_the_capability(self, tmp_path):
        assert fa.checks(_project(tmp_path), FEATURE, ("application-governance",), "api") == []

    def test_gherkin_delivery_selects_the_level_4_checks(self, tmp_path):
        names = list(_run(_project(tmp_path)))
        assert names == [f"feature:{name}" for name in validate._L4_CHECK_IDS]

    def test_llm_evaluation_adds_the_level_5_checks(self, tmp_path):
        names = list(_run(_project(tmp_path), (*BASE, "llm-evaluation")))
        assert names == [
            f"feature:{name}" for name in (*validate._L4_CHECK_IDS, *validate._L5_CHECK_IDS)
        ]

    def test_llm_evaluation_alone_selects_nothing(self, tmp_path):
        assert fa.checks(_project(tmp_path), FEATURE, ("llm-evaluation",), "api") == []

    def test_only_the_forecast_is_advisory(self, tmp_path):
        results = _run(_project(tmp_path))
        assert [name for name, (required, _) in results.items() if not required] == [
            "feature:eval-prediction"
        ]


class TestOutcomes:
    def test_a_complete_feature_passes_everything_but_the_forecast(self, tmp_path):
        states = _states(_run(_project(tmp_path)))
        assert states.pop("feature:eval-prediction") is State.UNKNOWN
        assert set(states.values()) == {State.PASS}

    def test_a_failure_fails_with_the_identifier_as_its_code(self, tmp_path):
        target = _project(tmp_path)
        (target / "features" / FEATURE / "plan.md").unlink()
        _, outcome = _run(target)["feature:completeness"]
        assert outcome.state is State.FAIL
        finding = outcome.findings[0]
        assert (finding.code, finding.severity, finding.category) == (
            "completeness",
            "error",
            "feature",
        )
        assert finding.location == f"features/{FEATURE}"

    def test_a_bad_forecast_is_reported_and_never_fails(self, tmp_path):
        target = _project(tmp_path, **{"plan.md": "# Plan\nNo forecast here.\n"})
        assert validate.check_plan_eval_prediction(target / "features" / FEATURE)[0] is (
            validate.CheckStatus.FAIL
        )
        _, outcome = _run(target)["feature:eval-prediction"]
        assert outcome.state is State.UNKNOWN
        assert outcome.evidence[0].origin == "agent-assertion"
        assert outcome.summary.startswith("forecast, not evidence")

    def test_a_check_that_raises_is_unknown(self, tmp_path, monkeypatch):
        def broken(_):
            raise RuntimeError("boom")

        monkeypatch.setattr(validate, "check_gherkin_syntax", broken)
        _, outcome = _run(_project(tmp_path))["feature:gherkin-syntax"]
        assert outcome.state is State.UNKNOWN and "RuntimeError" in outcome.summary
        assert "boom" not in outcome.summary


class TestCriteriaSchema:
    @pytest.mark.parametrize("project_type", ["api", "cli"])
    def test_the_profile_project_type_picks_the_bundled_schema(self, tmp_path, project_type):
        _, outcome = _run(_project(tmp_path), project_type=project_type)["feature:eval-criteria"]
        assert outcome.state is State.PASS and "backend schema" in outcome.summary

    def test_an_instance_the_schema_rejects_fails(self, tmp_path):
        target = _project(tmp_path, **{"eval_criteria.yaml": CRITERIA + "mode_extra: [\n"})
        _, outcome = _run(target)["feature:eval-criteria"]
        assert outcome.state is State.FAIL

    def test_a_value_the_schema_rejects_fails(self, tmp_path):
        target = _project(
            tmp_path, **{"eval_criteria.yaml": CRITERIA.replace("deterministic", "sometimes")}
        )
        _, outcome = _run(target)["feature:eval-criteria"]
        assert outcome.state is State.FAIL and "backend eval_criteria schema" in outcome.summary

    def test_without_a_project_type_validation_is_unknown_and_says_why(self, tmp_path):
        _, outcome = _run(_project(tmp_path), project_type=None)["feature:eval-criteria"]
        assert outcome.state is State.UNKNOWN
        assert "repository.project_type" in outcome.summary

    def test_an_unknown_project_type_is_unknown(self, tmp_path):
        _, outcome = _run(_project(tmp_path), project_type="mainframe")["feature:eval-criteria"]
        assert outcome.state is State.UNKNOWN and "mainframe" in outcome.summary

    def test_a_missing_structure_key_fails_whatever_the_project_type(self, tmp_path):
        target = _project(tmp_path, **{"eval_criteria.yaml": "mode: deterministic\n"})
        _, outcome = _run(target, project_type=None)["feature:eval-criteria"]
        assert outcome.state is State.FAIL

    def test_a_schema_copy_in_the_inspected_tree_is_not_used(self, tmp_path):
        target = _project(
            tmp_path, **{"eval_criteria.yaml": CRITERIA.replace("deterministic", "sometimes")}
        )
        permissive = target / "governance/backend/schemas/eval_criteria.schema.json"
        permissive.parent.mkdir(parents=True)
        permissive.write_text("{}")
        _, outcome = _run(target)["feature:eval-criteria"]
        assert outcome.state is State.FAIL

    def test_a_data_project_keeps_the_data_rules(self, tmp_path):
        results = _run(_project(tmp_path), project_type="data")
        _, forecast = results["feature:eval-prediction"]
        assert forecast.state is State.UNKNOWN
        assert results["feature:eval-criteria"][1].summary.count("data") >= 1


def test_the_legacy_check_is_unchanged_without_a_schema_argument(tmp_path):
    target = _project(tmp_path)
    status, message = validate.check_eval_criteria(target / "features" / FEATURE)
    assert status is validate.CheckStatus.WARN and "instance validation skipped" in message
