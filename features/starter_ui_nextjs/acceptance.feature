# Replace <feature_name> and complete every scenario before implementation.
# User-facing scenarios map to Playwright tests.

Feature: <feature_name>

  As a <role>
  I want <capability>
  So that <outcome>

  @e2e
  Scenario: <primary server-rendered or interactive flow>
    Given <precondition>
    When <action>
    Then <visible outcome>

  @e2e
  Scenario: <API failure, empty, or unavailable state>
    Given <backend API condition>
    When <action>
    Then <accessible recovery experience>

  @accessibility @e2e
  Scenario: <feature> is keyboard navigable
    Given the page is loaded
    When a keyboard-only user navigates the feature
    Then all interactive elements are reachable and operable
    And focus remains visible

  @accessibility @e2e
  Scenario: <feature> has no serious accessibility violations
    Given the page is loaded
    When an automated axe scan is run
    Then there are zero critical or serious violations
