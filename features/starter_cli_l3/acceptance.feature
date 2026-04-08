# INSTRUCTIONS
# Replace <feature_name> with your feature name throughout this file.
# Every populated NFR category in nfrs.md must have at least one scenario
# tagged with the corresponding @nfr-* tag. See docs/backend/architecture/GHERKIN_CONVENTIONS.md.
# If this feature produces a shared artifact (schema, API contract, event),
# include at least one @contract scenario.

Feature: <feature_name>

  As a <role>
  I want <capability>
  So that <outcome>

  Background:
    Given the CLI is installed

  # ── Happy path ──────────────────────────────────────────────────────────────

  Scenario: <primary happy path>
    Given <precondition>
    When I run "<command> <args>"
    Then the exit code is 0
    And stdout contains "<expected output>"

  # ── Failure / edge case ──────────────────────────────────────────────────────

  Scenario: <invalid input>
    When I run "<command> --invalid-flag"
    Then the exit code is 1
    And stderr contains "<error message>"

  Scenario: <missing required argument>
    When I run "<command>"
    Then the exit code is 1
    And stderr contains "Error: missing required argument"

  # ── NFR scenarios — add one per populated NFR category ───────────────────────
  # Uncomment and complete the tags that apply. Remove categories not in nfrs.md.

  # @nfr-performance
  # Scenario: <command completes within time budget>

  # @nfr-security
  # Scenario: <no secrets exposed in stdout or logs>

  # @nfr-availability
  # Scenario: <graceful degradation on external dependency failure>

  # @nfr-observability
  # Scenario: <structured log output in verbose mode>

  # ── Contract scenarios — required if this feature produces a shared artifact ──

  # @contract
  # Scenario: <contract scenario>
