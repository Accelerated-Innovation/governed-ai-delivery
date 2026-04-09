# INSTRUCTIONS
# Replace <feature_name> with your feature name throughout this file.
# Every populated NFR category in nfrs.md must have at least one scenario
# tagged with the corresponding @nfr-* tag. See docs/backend/architecture/GHERKIN_CONVENTIONS.md.
# If this feature produces a shared artifact (schema, API contract, event),
# include at least one @contract scenario.
# See features/schema_contract_example/acceptance.feature for a complete worked example.
#
# Level 5 tags:
#   @llm-eval       — scenario validates LLM output quality (triggers DeepEval)
#   @adversarial    — scenario tests adversarial resilience (triggers Promptfoo)
#   @guardrails     — scenario tests guardrail behavior (NeMo or Guardrails AI)

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

  # ── LLM evaluation scenarios (Level 5) ──────────────────────────────────────

  # @llm-eval
  # Scenario: LLM output is faithful to provided context
  #   Given a user query with retrieved context
  #   When the LLM generates a response
  #   Then the response is grounded in the context

  # @adversarial
  # Scenario: Jailbreak attempt is rejected
  #   Given a malicious prompt attempting to bypass instructions
  #   When the prompt is processed
  #   Then the system refuses the request safely

  # @guardrails
  # Scenario: Off-topic request is redirected
  #   Given a user asks about an unsupported topic
  #   When the guardrails evaluate the request
  #   Then the response stays within topic boundaries

  # ── Contract scenarios — required if this feature produces a shared artifact ──

  # @contract
  # Scenario: <contract scenario>
