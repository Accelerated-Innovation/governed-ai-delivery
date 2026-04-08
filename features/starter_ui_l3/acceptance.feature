# INSTRUCTIONS
# Replace <feature_name> with your feature name throughout this file.
# Every populated NFR category in nfrs.md must have at least one scenario
# tagged with the corresponding @nfr-* tag.
# All user-facing scenarios must be tagged @e2e — these map to Playwright tests.
# Scenarios with accessibility-specific assertions must be tagged @accessibility.
# See docs/ui/architecture/MVVM_CONTRACT.md for layer boundary rules.

Feature: <feature_name>

  As a <role>
  I want <capability>
  So that <outcome>

  Background:
    Given <shared precondition>

  # ── Happy path ──────────────────────────────────────────────────────────────

  @e2e
  Scenario: <primary happy path>
    Given <precondition>
    When <action>
    Then <expected visible outcome>

  # ── Failure / edge case ──────────────────────────────────────────────────────

  @e2e
  Scenario: <error or empty state>
    Given <precondition>
    When <action>
    Then <expected error or empty state message>

  # ── Accessibility ─────────────────────────────────────────────────────────────
  # Required for any interactive element, form, modal, or dynamic content.

  @accessibility @e2e
  Scenario: <feature> is keyboard navigable
    Given the page is loaded
    When a keyboard-only user navigates the <feature>
    Then all interactive elements are reachable and operable via keyboard
    And focus is always visible

  @accessibility @e2e
  Scenario: <feature> has no critical accessibility violations
    Given the page is loaded
    When an automated axe scan is run
    Then there are zero critical or serious violations

  # ── NFR scenarios — add one per populated NFR category ───────────────────────
  # Uncomment and complete the tags that apply. Remove categories not in nfrs.md.

  # @nfr-performance @e2e
  # Scenario: <feature> meets Core Web Vitals thresholds
  #   Given the page is loaded on a standard connection
  #   When performance is measured
  #   Then LCP is under <threshold>ms and CLS is below 0.1

  # @nfr-security
  # Scenario: <feature> is protected against XSS
  #   Given <user input scenario>
  #   When malicious script content is submitted
  #   Then the content is escaped and not executed

  # @nfr-compatibility @e2e
  # Scenario: <feature> renders correctly in supported browsers
  #   Given the page is loaded in <browser>
  #   When the user views <feature>
  #   Then the layout and functionality are correct

  # @nfr-usability @e2e
  # Scenario: <usability scenario>
