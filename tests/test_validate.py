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

    def test_skips_l3_starters(self, tmp_path):
        features = tmp_path / "features"
        make_full_feature(features / "starter_backend_l3")
        make_full_feature(features / "starter_cli_l3")
        make_full_feature(features / "starter_ui_l3")
        result = run_validation(tmp_path)
        assert result == 0  # no real features, so passes


# ---------------------------------------------------------------------------
# Level 3 validation
# ---------------------------------------------------------------------------


def make_l3_feature(feature_dir: Path, **overrides) -> None:
    """Create a valid Level 3 feature directory (3 artifacts)."""
    defaults = {
        "acceptance.feature": VALID_FEATURE,
        "nfrs.md": VALID_NFRS,
        "plan.md": "# Plan\n\n## Increments\n\n### Increment 1\nGoal: implement feature\n",
    }
    defaults.update(overrides)
    feature_dir.mkdir(parents=True, exist_ok=True)
    for name, content in defaults.items():
        write(feature_dir / name, content)


class TestL3Validation:
    def test_l3_three_artifacts_pass(self, tmp_path):
        """L3 validation passes with only 3 artifacts."""
        from cli.validate import L3_REQUIRED_ARTIFACTS

        features = tmp_path / "features"
        make_l3_feature(features / "my_feature", **{
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
        result = run_validation(tmp_path, level="3")
        assert result == 0

    def test_l3_missing_artifact_fails(self, tmp_path):
        """L3 validation fails when one of the 3 required artifacts is missing."""
        features = tmp_path / "features"
        feature_dir = features / "incomplete_feature"
        feature_dir.mkdir(parents=True)
        write(feature_dir / "acceptance.feature", VALID_FEATURE)
        write(feature_dir / "nfrs.md", VALID_NFRS)
        # Missing plan.md
        result = run_validation(tmp_path, level="3")
        assert result == 1

    def test_l3_completeness_checks_three(self, tmp_path):
        """L3 check_completeness only expects 3 artifacts."""
        from cli.validate import L3_REQUIRED_ARTIFACTS

        make_l3_feature(tmp_path)
        ok, msg = check_completeness(tmp_path, artifacts=L3_REQUIRED_ARTIFACTS)
        assert ok is True
        assert "3/3" in msg

    def test_l3_skips_eval_checks(self, tmp_path):
        """L3 validation passes without eval_criteria.yaml or evaluation_prediction."""
        features = tmp_path / "features"
        make_l3_feature(features / "simple_feature", **{
            "acceptance.feature": """\
                Feature: Simple

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
        result = run_validation(tmp_path, level="3")
        assert result == 0

    def test_l3_still_checks_gherkin(self, tmp_path):
        """L3 validation still checks Gherkin syntax."""
        features = tmp_path / "features"
        make_l3_feature(features / "bad_gherkin", **{
            "acceptance.feature": "No gherkin here\n",
        })
        result = run_validation(tmp_path, level="3")
        assert result == 1

    def test_l3_still_checks_nfr_tbd(self, tmp_path):
        """L3 validation still checks for TBD in nfrs.md."""
        features = tmp_path / "features"
        make_l3_feature(features / "tbd_feature", **{
            "nfrs.md": "## Performance\n- TBD\n",
        })
        result = run_validation(tmp_path, level="3")
        assert result == 1

    def test_level_from_govkit_marker(self, tmp_path):
        """Validation auto-detects level from .govkit marker."""
        import json

        features = tmp_path / "features"
        make_l3_feature(features / "my_feature", **{
            "acceptance.feature": """\
                Feature: My feature

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
        # Write .govkit marker for level 3
        marker = tmp_path / ".govkit"
        marker.write_text(json.dumps({"level": "3"}), encoding="utf-8")
        # Don't pass level explicitly — should auto-detect from marker
        result = run_validation(tmp_path)
        assert result == 0

    def test_explicit_level_overrides_marker(self, tmp_path):
        """Explicit level parameter takes precedence over .govkit marker."""
        import json

        features = tmp_path / "features"
        # Create L3 feature (no eval_criteria, no architecture_preflight)
        make_l3_feature(features / "my_feature", **{
            "acceptance.feature": """\
                Feature: My feature

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
        # Marker says level 3
        marker = tmp_path / ".govkit"
        marker.write_text(json.dumps({"level": "3"}), encoding="utf-8")
        # But we explicitly validate as level 4 — should fail (missing artifacts)
        result = run_validation(tmp_path, level="4")
        assert result == 1


# ---------------------------------------------------------------------------
# Level 5 validation
# ---------------------------------------------------------------------------


VALID_L5_NFRS = """\
    ## Performance
    - Response time < 200ms

    ## Security
    - Auth required

    ## LLM Latency
    - p50 < 500ms, p95 < 2s

    ## LLM Cost
    - per-request < $0.05

    ## LLM Fallback
    - fallback to secondary model within 3s

    ## LLM Safety
    - guardrail mode = nemo, zero jailbreak passes
"""

VALID_L5_EVAL_CRITERIA = """\
    version: 1
    mode: llm
    owner: team-ai

    unit_tests:
      enforce_FIRST: true
      minimum_FIRST_average: 4

    code_quality:
      enforce_virtues: true
      minimum_virtue_average: 4

    llm_evaluation:
      criteria:
        - name: faithfulness
          eval_class: deepeval_faithfulness
          threshold: 0.8
          fail_on: below_threshold
          tool: deepeval
        - name: adversarial
          eval_class: promptfoo_adversarial
          threshold: 1.0
          fail_on: below_threshold
          tool: promptfoo
      dataset: tests/eval/my_feature/eval_sets/dataset.json
      fail_on_regression: true
"""

VALID_L5_PREFLIGHT = """\
    # Architecture Preflight: my_feature

    ## 1. Artifact Review
    All present.

    ## 2. Standards Referenced
    ARCH_CONTRACT, BOUNDARIES

    ## 3. Boundary Analysis
    No violations.

    ## 4. API Impact
    No API impact.

    ## 5. Security Impact
    No security impact.

    ## 6. Evaluation Impact
    Mode: llm

    ## 7. ADR Determination
    ADR required: no

    ## 8. Shared Contract Analysis
    No shared contract produced.

    ## 9. Preflight Conclusion
    Approved.

    ## 10. LLM Gateway Configuration
    LiteLLM configured: yes

    ## 11. Observability Configuration
    OpenLLMetry: yes, Langfuse: yes

    ## 12. Guardrails Configuration
    Mode: nemo

    ## 13. Evaluation Strategy
    DeepEval: yes, Promptfoo: yes

    ## 14. LLM NFR Validation
    All populated.
"""


def make_l5_feature(feature_dir: Path, **overrides) -> None:
    """Create a valid Level 5 feature directory."""
    defaults = {
        "acceptance.feature": """\
            Feature: L5 feature

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
        "nfrs.md": VALID_L5_NFRS,
        "eval_criteria.yaml": VALID_L5_EVAL_CRITERIA,
        "plan.md": VALID_PLAN,
        "architecture_preflight.md": VALID_L5_PREFLIGHT,
    }
    defaults.update(overrides)
    feature_dir.mkdir(parents=True, exist_ok=True)
    for name, content in defaults.items():
        write(feature_dir / name, content)


class TestL5Validation:
    def test_l5_passes_with_all_checks(self, tmp_path):
        """Full valid L5 feature passes all 9 checks."""
        features = tmp_path / "features"
        make_l5_feature(features / "genai_feature")
        result = run_validation(tmp_path, level="5")
        assert result == 0

    def test_l5_missing_llm_nfrs_fails(self, tmp_path):
        """L5 fails when LLM NFR categories are TBD."""
        features = tmp_path / "features"
        make_l5_feature(features / "bad_nfrs", **{
            "nfrs.md": """\
                ## Performance
                - Response < 200ms

                ## Security
                - Auth required

                ## LLM Latency
                - TBD

                ## LLM Cost
                - TBD

                ## LLM Fallback
                - TBD

                ## LLM Safety
                - TBD
            """,
        })
        result = run_validation(tmp_path, level="5")
        assert result == 1

    def test_l5_missing_deepeval_criteria_fails(self, tmp_path):
        """L5 fails when eval_criteria.yaml has no deepeval/promptfoo eval_class."""
        features = tmp_path / "features"
        make_l5_feature(features / "no_deepeval", **{
            "eval_criteria.yaml": """\
                version: 1
                mode: llm
                unit_tests:
                  enforce_FIRST: true
                  minimum_FIRST_average: 4
                code_quality:
                  enforce_virtues: true
                  minimum_virtue_average: 4
                llm_evaluation:
                  criteria:
                    - name: groundedness
                      eval_class: retrieval_match
                      threshold: 0.9
                      fail_on: below_threshold
                  dataset: eval_sets/test.json
                  fail_on_regression: true
            """,
        })
        result = run_validation(tmp_path, level="5")
        assert result == 1

    def test_l5_missing_preflight_sections_fails(self, tmp_path):
        """L5 fails when architecture_preflight.md is missing L5 sections."""
        features = tmp_path / "features"
        make_l5_feature(features / "no_l5_sections", **{
            "architecture_preflight.md": """\
                # Architecture Preflight
                ## 1. Artifact Review
                All present.
                ## 9. Preflight Conclusion
                Approved.
            """,
        })
        result = run_validation(tmp_path, level="5")
        assert result == 1

    def test_l5_backward_compatible_with_l4(self, tmp_path):
        """L4 features still validate at L4 even when L5 exists."""
        features = tmp_path / "features"
        make_full_feature(features / "l4_feature", **{
            "acceptance.feature": """\
                Feature: L4 feature

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
        result = run_validation(tmp_path, level="4")
        assert result == 0

    def test_l5_skips_llm_checks_for_deterministic(self, tmp_path):
        """L5 LLM checks are skipped when mode is deterministic."""
        features = tmp_path / "features"
        make_l5_feature(features / "deterministic_feature", **{
            "eval_criteria.yaml": VALID_EVAL_CRITERIA,  # mode: deterministic
        })
        result = run_validation(tmp_path, level="5")
        assert result == 0

    def test_l5_skips_l5_starters(self, tmp_path):
        """L5 starters are skipped during validation."""
        features = tmp_path / "features"
        make_l5_feature(features / "starter_backend_l5")
        make_l5_feature(features / "starter_cli_l5")
        result = run_validation(tmp_path, level="5")
        assert result == 0

    def test_level_5_from_govkit_marker(self, tmp_path):
        """Validation auto-detects level 5 from .govkit marker."""
        import json

        features = tmp_path / "features"
        make_l5_feature(features / "genai_feature")
        marker = tmp_path / ".govkit"
        marker.write_text(json.dumps({"level": "5"}), encoding="utf-8")
        result = run_validation(tmp_path)
        assert result == 0
