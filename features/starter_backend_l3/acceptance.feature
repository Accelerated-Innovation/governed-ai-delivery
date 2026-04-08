# INSTRUCTIONS
# Replace <feature_name> with your feature name throughout this file.
# Every populated NFR category in nfrs.md must have at least one scenario
# tagged with the corresponding @nfr-* tag. See docs/backend/architecture/GHERKIN_CONVENTIONS.md.
# If this feature produces a shared artifact (schema, API contract, event),
# include at least one @contract scenario.
# See features/schema_contract_example/acceptance.feature for a complete worked example.

Feature: <feature_name>

  As a <role>
  I want <capability>
  So that <outcome>

  Background:
    Given <shared precondition>

  # ── Happy path ──────────────────────────────────────────────────────────────

  Scenario: <primary happy path>
    Given <precondition>
    When <action>
    Then <expected outcome>

  # ── Failure / edge case ──────────────────────────────────────────────────────

  Scenario: <significant failure or edge case>
    Given <precondition>
    When <action>
    Then <expected outcome>

  # ── NFR scenarios — add one per populated NFR category ───────────────────────
  # Uncomment and complete the tags that apply. Remove categories not in nfrs.md.

  # @nfr-performance
  # Scenario: <performance scenario>

  # @nfr-security
  # Scenario: <security scenario>

  # @nfr-availability
  # Scenario: <availability scenario>

  # @nfr-scalability
  # Scenario: <scalability scenario>

  # @nfr-observability
  # Scenario: <observability scenario>

  # @nfr-compliance
  # Scenario: <compliance scenario>

  # ── Contract scenarios — required if this feature produces a shared artifact ──

  # @contract
  # Scenario: <contract scenario>
