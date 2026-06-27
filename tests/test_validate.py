"""Tests for cli/validate.py — all 7 check functions and run_validation."""

import json
import textwrap
from pathlib import Path

from cli.validate import (
    check_agent_topology_exists,
    check_agent_topology_sections,
    check_completeness,
    check_eval_criteria,
    check_gherkin_nfr_coverage,
    check_gherkin_syntax,
    check_nfrs_no_tbd,
    check_nfrs_sections,
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
    ## Repository Scope

    **Scope:** `single-repo`

    ## Out of scope
    - none declared yet

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
# check_nfrs_sections
# ---------------------------------------------------------------------------


class TestCheckNfrsSections:
    def test_full_contract(self, tmp_path):
        write(tmp_path / "nfrs.md", """\
            ## Repository Scope

            **Scope:** `single-repo`

            ## Out of scope
            - none declared yet

            ## Performance
            - Response time < 200ms
        """)
        result, msg = check_nfrs_sections(tmp_path)
        assert result is True
        assert "section contract OK" in msg

    def test_missing_out_of_scope_warns(self, tmp_path):
        write(tmp_path / "nfrs.md", """\
            ## Repository Scope

            **Scope:** `single-repo`

            ## Performance
            - Response time < 200ms
        """)
        result, msg = check_nfrs_sections(tmp_path)
        assert result is None  # WARN, not FAIL — plan will infer
        assert "Out of scope" in msg
        assert "infer" in msg

    def test_missing_repository_scope_warns(self, tmp_path):
        write(tmp_path / "nfrs.md", """\
            ## Out of scope
            - none declared yet

            ## Performance
            - Response time < 200ms
        """)
        result, msg = check_nfrs_sections(tmp_path)
        assert result is None  # WARN — hard-gated by repo-scope-check/preflight
        assert "Repository Scope" in msg

    def test_out_of_scope_with_suffix_matches(self, tmp_path):
        # starter_data uses "## Out of scope (this NFRs file)" — must still satisfy
        write(tmp_path / "nfrs.md", """\
            ## Repository Scope

            **Scope:** `single-repo`

            ## Out of scope (this NFRs file)
            - Source system reliability (owned elsewhere)
        """)
        result, msg = check_nfrs_sections(tmp_path)
        assert result is True
        assert "section contract OK" in msg

    def test_missing_file(self, tmp_path):
        tmp_path.mkdir(exist_ok=True)
        result, msg = check_nfrs_sections(tmp_path)
        assert result is False
        assert "not found" in msg


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
        result = run_validation(tmp_path, level="4")
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

    def test_missing_features_dir_returns_one_at_l4(self, tmp_path):
        # At L4 (Spec-Driven Add-On) a missing features/ dir is an error.
        # At L3 (Foundations) it is fine — see test_maturity_model.TestValidateNoOpAtL3.
        result = run_validation(tmp_path, level="4")
        assert result == 1

    def test_no_features_returns_zero(self, tmp_path):
        (tmp_path / "features").mkdir()
        result = run_validation(tmp_path)
        assert result == 0

    def test_explicit_level_overrides_marker(self, tmp_path):
        """Explicit level parameter takes precedence over .govkit marker.

        Regression guard: a project with marker `level: "3"` but only 3 artifacts per
        feature must still fail explicit `level="4"` validation. This is critical for
        the v0.6→v0.7 marker migration story (see plan §7.2): legacy L3 projects need
        to migrate to L4 and add the two missing artifacts.
        """
        features = tmp_path / "features"
        feature_dir = features / "my_feature"
        feature_dir.mkdir(parents=True)
        # 3-artifact feature (legacy v0.6 L3 shape)
        write(feature_dir / "acceptance.feature", VALID_FEATURE)
        write(feature_dir / "nfrs.md", VALID_NFRS)
        write(feature_dir / "plan.md", "# Plan\n\n## Increments\n\n### Increment 1\nGoal: implement\n")
        marker = tmp_path / ".govkit"
        marker.write_text(json.dumps({"level": "3"}), encoding="utf-8")
        # Explicit L4 must override the marker and fail (eval_criteria + arch_preflight missing)
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


# ---------------------------------------------------------------------------
# Multi-agent validation
# ---------------------------------------------------------------------------

VALID_AGENT_TOPOLOGY = """\
    # Agent Topology: my_feature

    ## Orchestrator
    - **Role:** Route queries to specialists
    - **System Prompt:** `src/agents/orchestrator/system_prompt.md`
    - **Model:** gpt-4o

    ## Specialist Agents

    ### analysis-agent
    - **Role:** Classify the input
    - **Input State:** query: str
    - **Output State:** classification: str
    - **System Prompt:** `src/agents/analysis/system_prompt.md`

    ## Routing Logic
    START → orchestrator
    orchestrator → analysis-agent (always)
    analysis-agent → END

    ## Failure Modes
    - Per-node timeout: 30s
    - Graph timeout: 120s
"""

MULTI_AGENT_EVAL_CRITERIA = """\
    version: 1
    mode: llm
    multi_agent: true
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
      dataset: tests/eval/my_feature/eval_sets/dataset.json
      fail_on_regression: true

    multi_agent_evaluation:
      topology_validated: true
      system_prompt_governed: true
"""


class TestMultiAgentValidation:
    def test_topology_exists_pass(self, tmp_path):
        """check_agent_topology_exists passes when agent_topology.md is present."""
        write(tmp_path / "eval_criteria.yaml", MULTI_AGENT_EVAL_CRITERIA)
        write(tmp_path / "agent_topology.md", VALID_AGENT_TOPOLOGY)
        ok, msg = check_agent_topology_exists(tmp_path)
        assert ok is True
        assert "agent_topology.md present" in msg

    def test_topology_exists_missing_fails(self, tmp_path):
        """check_agent_topology_exists fails when multi_agent: true but file missing."""
        write(tmp_path / "eval_criteria.yaml", MULTI_AGENT_EVAL_CRITERIA)
        ok, msg = check_agent_topology_exists(tmp_path)
        assert ok is False
        assert "missing" in msg

    def test_topology_exists_empty_fails(self, tmp_path):
        """check_agent_topology_exists fails when agent_topology.md is empty."""
        write(tmp_path / "eval_criteria.yaml", MULTI_AGENT_EVAL_CRITERIA)
        (tmp_path / "agent_topology.md").write_text("", encoding="utf-8")
        ok, msg = check_agent_topology_exists(tmp_path)
        assert ok is False
        assert "empty" in msg

    def test_topology_exists_not_declared_skips(self, tmp_path):
        """check_agent_topology_exists skips when multi_agent not declared."""
        write(tmp_path / "eval_criteria.yaml", "version: 1\nmode: llm\n")
        ok, msg = check_agent_topology_exists(tmp_path)
        assert ok is True
        assert "not applicable" in msg

    def test_topology_exists_no_eval_criteria_skips(self, tmp_path):
        """check_agent_topology_exists skips when eval_criteria.yaml is missing."""
        ok, msg = check_agent_topology_exists(tmp_path)
        assert ok is True
        assert "not applicable" in msg

    def test_topology_sections_pass(self, tmp_path):
        """check_agent_topology_sections passes when all four sections present."""
        write(tmp_path / "eval_criteria.yaml", MULTI_AGENT_EVAL_CRITERIA)
        write(tmp_path / "agent_topology.md", VALID_AGENT_TOPOLOGY)
        ok, msg = check_agent_topology_sections(tmp_path)
        assert ok is True
        assert "all required sections" in msg

    def test_topology_sections_missing_one_fails(self, tmp_path):
        """check_agent_topology_sections fails when a required section is absent."""
        write(tmp_path / "eval_criteria.yaml", MULTI_AGENT_EVAL_CRITERIA)
        write(tmp_path / "agent_topology.md", """\
            # Agent Topology

            ## Orchestrator
            - Role: route

            ## Specialist Agents
            ### agent-a
            - Role: analyse

            ## Routing Logic
            START → END

            # Missing Failure Modes section
        """)
        ok, msg = check_agent_topology_sections(tmp_path)
        assert ok is False
        assert "Failure Modes" in msg

    def test_topology_sections_not_declared_skips(self, tmp_path):
        """check_agent_topology_sections skips when multi_agent not declared."""
        write(tmp_path / "eval_criteria.yaml", "version: 1\nmode: llm\n")
        ok, msg = check_agent_topology_sections(tmp_path)
        assert ok is True
        assert "not applicable" in msg

    def test_topology_sections_file_missing_fails(self, tmp_path):
        """check_agent_topology_sections fails when file is missing (multi_agent declared)."""
        write(tmp_path / "eval_criteria.yaml", MULTI_AGENT_EVAL_CRITERIA)
        ok, msg = check_agent_topology_sections(tmp_path)
        assert ok is False
        assert "not found" in msg

    def test_l5_multi_agent_full_pass(self, tmp_path):
        """Full L5 validation passes for a multi-agent feature with topology present."""
        features = tmp_path / "features"
        make_l5_feature(
            features / "ma_feature",
            **{
                "eval_criteria.yaml": MULTI_AGENT_EVAL_CRITERIA,
                "agent_topology.md": VALID_AGENT_TOPOLOGY,
            },
        )
        result = run_validation(tmp_path, level="5")
        assert result == 0

    def test_l5_multi_agent_missing_topology_fails(self, tmp_path):
        """L5 validation fails when multi_agent: true but agent_topology.md is absent."""
        features = tmp_path / "features"
        make_l5_feature(
            features / "ma_feature",
            **{"eval_criteria.yaml": MULTI_AGENT_EVAL_CRITERIA},
        )
        result = run_validation(tmp_path, level="5")
        assert result == 1

    def test_l5_non_multi_agent_unaffected(self, tmp_path):
        """Standard L5 features without multi_agent: true are not affected."""
        features = tmp_path / "features"
        make_l5_feature(features / "single_agent_feature")
        result = run_validation(tmp_path, level="5")
        assert result == 0


# ---------------------------------------------------------------------------
# UI-shape validation (v0.8)
# ---------------------------------------------------------------------------


def _write_ui_marker(target: Path, level: str, ui_type: str = "ui-react") -> None:
    """Write a v0.8 .govkit marker for a UI-shape install."""
    marker = {
        "version": "0.8.0",
        "level": level,
        "agent": "claude-code",
        "options": {"type": ui_type, "ci": "github"},
        "applied_at": "2026-05-18T00:00:00+00:00",
    }
    (target / ".govkit").write_text(json.dumps(marker), encoding="utf-8")


class TestValidateUiShapes:
    """v0.8 UI shapes (--type ui-react / ui-angular) must validate identically to backend.

    Validate logic is stack-agnostic — the 5-artifact contract, FIRST/Virtue
    prediction, and Gherkin coverage rules apply regardless of `type`. These
    tests lock that in for UI markers per plan §8.2.
    """

    def test_ui_react_l3_no_op(self, tmp_path, monkeypatch):
        """L3 UI install validates clean — L3 short-circuits regardless of type."""
        monkeypatch.setenv("GOVKIT_NO_SHAPE_MIGRATION_WARNING", "1")
        _write_ui_marker(tmp_path, level="3", ui_type="ui-react")
        result = run_validation(tmp_path)
        assert result == 0, "L3 UI install must short-circuit and return 0"

    def test_ui_react_l4_5_artifact_passes(self, tmp_path, monkeypatch):
        """L4 UI install with a complete 5-artifact feature validates clean."""
        monkeypatch.setenv("GOVKIT_NO_SHAPE_MIGRATION_WARNING", "1")
        _write_ui_marker(tmp_path, level="4", ui_type="ui-react")
        features = tmp_path / "features"
        make_full_feature(features / "hello_world_ui", **{
            "nfrs.md": "## Performance\n- LCP under 2500ms on 4G\n",
            "acceptance.feature": """\
                Feature: Hello World UI Card

                  @e2e
                  Scenario: Render the default greeting
                    Given the hello card page is loaded
                    When the page finishes rendering
                    Then the card displays "hello, world"

                  @e2e @nfr-performance
                  Scenario: Page meets LCP target
                    Given the hello card page is loaded
                    When Core Web Vitals are measured
                    Then LCP is below 2500ms
            """,
        })
        result = run_validation(tmp_path)
        assert result == 0, "L4 UI install with 5-artifact feature must validate clean"

    def test_ui_angular_l4_5_artifact_passes(self, tmp_path, monkeypatch):
        """Same as the react case but with ui-angular marker — type is opaque to validate."""
        monkeypatch.setenv("GOVKIT_NO_SHAPE_MIGRATION_WARNING", "1")
        _write_ui_marker(tmp_path, level="4", ui_type="ui-angular")
        features = tmp_path / "features"
        make_full_feature(features / "hello_world_ui", **{
            "nfrs.md": "## Performance\n- LCP under 2500ms on 4G\n",
            "acceptance.feature": """\
                Feature: Hello World UI Card

                  @e2e
                  Scenario: Render
                    Given the page is loaded
                    When rendered
                    Then the card displays "hello, world"

                  @e2e @nfr-performance
                  Scenario: LCP target
                    Given the page is loaded
                    When measured
                    Then LCP is below 2500ms
            """,
        })
        result = run_validation(tmp_path)
        assert result == 0, "L4 UI install (angular) with 5-artifact feature must validate clean"

    def test_ui_marker_read_does_not_crash(self, tmp_path, monkeypatch):
        """`.govkit` carrying `type: ui-react` is read tolerantly by validate's marker path.

        Regression guard for the v0.8 marker shape — validate must not assume
        type ∈ {api, cli} when reading the marker.
        """
        monkeypatch.setenv("GOVKIT_NO_SHAPE_MIGRATION_WARNING", "1")
        _write_ui_marker(tmp_path, level="3", ui_type="ui-react")
        # No features/ dir — L3 still short-circuits cleanly via the marker level read.
        result = run_validation(tmp_path)
        assert result == 0

    def test_legacy_ui_option_in_marker_tolerated(self, tmp_path, monkeypatch):
        """Pre-v0.8 markers with `options.ui` must still be readable from validate's path.

        Locks in plan §7: legacy markers warn but never crash. The shape-migration
        warning is suppressed here so the test focuses on tolerance, not noise.
        """
        monkeypatch.setenv("GOVKIT_NO_SHAPE_MIGRATION_WARNING", "1")
        marker = {
            "version": "0.7.0",
            "level": "3",
            "agent": "claude-code",
            "options": {"type": "api", "ci": "github", "ui": "react"},  # legacy ui key
            "applied_at": "2026-04-01T00:00:00+00:00",
        }
        (tmp_path / ".govkit").write_text(json.dumps(marker), encoding="utf-8")
        result = run_validation(tmp_path)
        assert result == 0, "Legacy marker with options.ui must still validate (L3 short-circuit)"
