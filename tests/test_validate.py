"""Tests for cli/validate.py — all 6 check functions and run_validation."""

import textwrap
from pathlib import Path

import pytest

from cli.validate import (
    check_completeness,
    check_eval_criteria,
    check_gherkin_nfr_coverage,
    check_gherkin_syntax,
    check_nfrs_no_tbd,
    check_plan_eval_prediction,
    run_validation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


VALID_FEATURE = """\
    Feature: Sample feature

      Scenario: Happy path
        Given something exists
        When I do something
        Then it succeeds
"""

VALID_NFRS = """\
    ## Performance
    - Response time < 200ms

    ## Security
    - Auth required
"""

VALID_EVAL_CRITERIA = """\
    version: "1"
    mode: deterministic
    criteria:
      - name: output_structure
        type: structure_validator
"""

VALID_PLAN = """\
    # Plan

    ```yaml
    evaluation_prediction:
      first:
        fast: {score: 5, evidence: "unit tests < 50ms"}
        isolated: {score: 5, evidence: "no shared state"}
        repeatable: {score: 5, evidence: "deterministic"}
        self_verifying: {score: 4, evidence: "assertions"}
        timely: {score: 4, evidence: "written before code"}
        average: 4.6
      virtues:
        working: {score: 5, evidence: "passes"}
        unique: {score: 4, evidence: "no duplication"}
        simple: {score: 5, evidence: "minimal"}
        clear: {score: 4, evidence: "readable"}
        easy: {score: 4, evidence: "standard patterns"}
        developed: {score: 5, evidence: "complete"}
        brief: {score: 4, evidence: "concise"}
        average: 4.4
    ```
"""


def make_full_feature(feature_dir: Path, **overrides) -> None:
    """Create a complete valid feature directory, with optional file overrides."""
    defaults = {
        "acceptance.feature": VALID_FEATURE,
        "nfrs.md": VALID_NFRS,
        "eval_criteria.yaml": VALID_EVAL_CRITERIA,
        "plan.md": VALID_PLAN,
        "architecture_preflight.md": "# Architecture Preflight\nAll checks passed.\n",
    }
    defaults.update(overrides)
    feature_dir.mkdir(parents=True, exist_ok=True)
    for name, content in defaults.items():
        write(feature_dir / name, content)


# ---------------------------------------------------------------------------
# check_completeness
# ---------------------------------------------------------------------------


class TestCheckCompleteness:
    def test_all_present(self, tmp_path):
        make_full_feature(tmp_path)
        ok, msg = check_completeness(tmp_path)
        assert ok is True
        assert "5/5" in msg

    def test_missing_artifact(self, tmp_path):
        make_full_feature(tmp_path)
        (tmp_path / "plan.md").unlink()
        ok, msg = check_completeness(tmp_path)
        assert ok is False
        assert "missing: plan.md" in msg

    def test_empty_artifact(self, tmp_path):
        make_full_feature(tmp_path)
        (tmp_path / "nfrs.md").write_text("", encoding="utf-8")
        ok, msg = check_completeness(tmp_path)
        assert ok is False
        assert "empty: nfrs.md" in msg

    def test_multiple_missing(self, tmp_path):
        make_full_feature(tmp_path)
        (tmp_path / "plan.md").unlink()
        (tmp_path / "nfrs.md").unlink()
        ok, msg = check_completeness(tmp_path)
        assert ok is False
        assert "3/5" in msg


# ---------------------------------------------------------------------------
# check_gherkin_syntax
# ---------------------------------------------------------------------------


class TestCheckGherkinSyntax:
    def test_valid_gherkin(self, tmp_path):
        write(tmp_path / "acceptance.feature", VALID_FEATURE)
        ok, msg = check_gherkin_syntax(tmp_path)
        assert ok is True

    def test_missing_file(self, tmp_path):
        tmp_path.mkdir(exist_ok=True)
        ok, msg = check_gherkin_syntax(tmp_path)
        assert ok is False
        assert "not found" in msg

    def test_missing_feature_keyword(self, tmp_path):
        write(tmp_path / "acceptance.feature", """\
            Scenario: Something
              Given a thing
              When I act
              Then result
        """)
        ok, msg = check_gherkin_syntax(tmp_path)
        assert ok is False
        assert "Feature:" in msg

    def test_missing_scenario_keyword(self, tmp_path):
        write(tmp_path / "acceptance.feature", """\
            Feature: Something
              Given a thing
              When I act
              Then result
        """)
        ok, msg = check_gherkin_syntax(tmp_path)
        assert ok is False
        assert "Scenario:" in msg

    def test_missing_steps(self, tmp_path):
        write(tmp_path / "acceptance.feature", """\
            Feature: Something
              Scenario: Empty scenario
        """)
        ok, msg = check_gherkin_syntax(tmp_path)
        assert ok is False
        assert "Given/When/Then" in msg

    def test_comments_ignored_for_steps(self, tmp_path):
        write(tmp_path / "acceptance.feature", """\
            Feature: Something
              Scenario: Commented out
                # Given a thing
                # When I act
                # Then result
        """)
        ok, msg = check_gherkin_syntax(tmp_path)
        assert ok is False
        assert "Given/When/Then" in msg


# ---------------------------------------------------------------------------
# check_nfrs_no_tbd
# ---------------------------------------------------------------------------


class TestCheckNfrsNoTbd:
    def test_no_tbd(self, tmp_path):
        write(tmp_path / "nfrs.md", VALID_NFRS)
        ok, msg = check_nfrs_no_tbd(tmp_path)
        assert ok is True

    def test_has_tbd(self, tmp_path):
        write(tmp_path / "nfrs.md", """\
            ## Performance
            - TBD
        """)
        ok, msg = check_nfrs_no_tbd(tmp_path)
        assert ok is False
        assert "TBD" in msg

    def test_missing_file(self, tmp_path):
        tmp_path.mkdir(exist_ok=True)
        ok, msg = check_nfrs_no_tbd(tmp_path)
        assert ok is False
        assert "not found" in msg

    def test_tbd_in_word_ignored(self, tmp_path):
        write(tmp_path / "nfrs.md", """\
            ## Performance
            - The TBDATA format is used
        """)
        ok, msg = check_nfrs_no_tbd(tmp_path)
        assert ok is True  # \bTBD\b won't match TBDATA


# ---------------------------------------------------------------------------
# check_eval_criteria
# ---------------------------------------------------------------------------


class TestCheckEvalCriteria:
    def test_valid_criteria(self, tmp_path):
        write(tmp_path / "eval_criteria.yaml", VALID_EVAL_CRITERIA)
        result, msg = check_eval_criteria(tmp_path)
        # Result is True or None depending on check-jsonschema availability
        assert result is not False

    def test_missing_version(self, tmp_path):
        write(tmp_path / "eval_criteria.yaml", """\
            mode: deterministic
        """)
        ok, msg = check_eval_criteria(tmp_path)
        assert ok is False
        assert "version" in msg

    def test_missing_mode(self, tmp_path):
        write(tmp_path / "eval_criteria.yaml", """\
            version: "1"
        """)
        ok, msg = check_eval_criteria(tmp_path)
        assert ok is False
        assert "mode" in msg

    def test_missing_file(self, tmp_path):
        tmp_path.mkdir(exist_ok=True)
        ok, msg = check_eval_criteria(tmp_path)
        assert ok is False
        assert "not found" in msg


# ---------------------------------------------------------------------------
# check_plan_eval_prediction
# ---------------------------------------------------------------------------


class TestCheckPlanEvalPrediction:
    def test_valid_prediction(self, tmp_path):
        write(tmp_path / "plan.md", VALID_PLAN)
        ok, msg = check_plan_eval_prediction(tmp_path)
        assert ok is True
        assert "4.6" in msg
        assert "4.4" in msg

    def test_missing_prediction_block(self, tmp_path):
        write(tmp_path / "plan.md", "# Plan\nNo prediction here.\n")
        ok, msg = check_plan_eval_prediction(tmp_path)
        assert ok is False
        assert "missing evaluation_prediction" in msg

    def test_null_values(self, tmp_path):
        write(tmp_path / "plan.md", """\
            # Plan

            ```yaml
            evaluation_prediction:
              first:
                fast: {score: null, evidence: null}
                average: 4.0
            ```
        """)
        ok, msg = check_plan_eval_prediction(tmp_path)
        assert ok is False
        assert "null" in msg

    def test_below_threshold(self, tmp_path):
        write(tmp_path / "plan.md", """\
            # Plan

            ```yaml
            evaluation_prediction:
              first:
                average: 3.5
              virtues:
                average: 4.2
            ```
        """)
        ok, msg = check_plan_eval_prediction(tmp_path)
        assert ok is False
        assert "3.5" in msg

    def test_missing_file(self, tmp_path):
        tmp_path.mkdir(exist_ok=True)
        ok, msg = check_plan_eval_prediction(tmp_path)
        assert ok is False
        assert "not found" in msg

    def test_missing_averages(self, tmp_path):
        write(tmp_path / "plan.md", """\
            # Plan

            ```yaml
            evaluation_prediction:
              first:
                fast: {score: 5, evidence: "fast"}
            ```
        """)
        ok, msg = check_plan_eval_prediction(tmp_path)
        assert ok is False
        assert "missing average" in msg


# ---------------------------------------------------------------------------
# check_gherkin_nfr_coverage
# ---------------------------------------------------------------------------


class TestCheckGherkinNfrCoverage:
    def test_matching_coverage(self, tmp_path):
        write(tmp_path / "nfrs.md", VALID_NFRS)
        write(tmp_path / "acceptance.feature", """\
            Feature: Sample

              @nfr-performance
              Scenario: Performance test
                Given load
                When request
                Then fast

              @nfr-security
              Scenario: Security test
                Given auth
                When request
                Then authorized
        """)
        ok, msg = check_gherkin_nfr_coverage(tmp_path)
        assert ok is True

    def test_missing_nfr_tag(self, tmp_path):
        write(tmp_path / "nfrs.md", VALID_NFRS)
        write(tmp_path / "acceptance.feature", """\
            Feature: Sample

              @nfr-performance
              Scenario: Performance test
                Given load
                When request
                Then fast
        """)
        ok, msg = check_gherkin_nfr_coverage(tmp_path)
        assert ok is False
        assert "@nfr-security" in msg

    def test_no_populated_nfrs(self, tmp_path):
        write(tmp_path / "nfrs.md", """\
            ## Performance
            - TBD
        """)
        write(tmp_path / "acceptance.feature", VALID_FEATURE)
        ok, msg = check_gherkin_nfr_coverage(tmp_path)
        assert ok is True  # no populated categories, so coverage not required

    def test_missing_files(self, tmp_path):
        tmp_path.mkdir(exist_ok=True)
        ok, msg = check_gherkin_nfr_coverage(tmp_path)
        assert ok is False
        assert "missing" in msg


# ---------------------------------------------------------------------------
# run_validation
# ---------------------------------------------------------------------------


class TestRunValidation:
    def test_valid_project_returns_zero(self, tmp_path):
        features = tmp_path / "features"
        make_full_feature(features / "my_feature", **{
            "acceptance.feature": """\
                Feature: My feature

                  @nfr-performance
                  Scenario: Fast response
                    Given a request
                    When processed
                    Then response is fast

                  @nfr-security
                  Scenario: Auth required
                    Given no credentials
                    When request made
                    Then rejected
            """,
        })
        result = run_validation(tmp_path)
        assert result == 0

    def test_invalid_feature_returns_one(self, tmp_path):
        features = tmp_path / "features"
        feature_dir = features / "bad_feature"
        feature_dir.mkdir(parents=True)
        # Only create one artifact — most checks will fail
        write(feature_dir / "acceptance.feature", VALID_FEATURE)
        result = run_validation(tmp_path)
        assert result == 1

    def test_skips_starters(self, tmp_path):
        features = tmp_path / "features"
        # Create a starter — should be skipped
        make_full_feature(features / "starter_backend")
        # Create a valid feature
        make_full_feature(features / "real_feature", **{
            "acceptance.feature": """\
                Feature: Real feature

                  @nfr-performance
                  Scenario: Fast
                    Given a request
                    When processed
                    Then fast

                  @nfr-security
                  Scenario: Secure
                    Given auth
                    When request
                    Then ok
            """,
        })
        result = run_validation(tmp_path)
        assert result == 0

    def test_missing_target_returns_one(self, tmp_path):
        result = run_validation(tmp_path / "nonexistent")
        assert result == 1

    def test_missing_features_dir_returns_one(self, tmp_path):
        result = run_validation(tmp_path)
        assert result == 1

    def test_no_features_returns_zero(self, tmp_path):
        (tmp_path / "features").mkdir()
        result = run_validation(tmp_path)
        assert result == 0
