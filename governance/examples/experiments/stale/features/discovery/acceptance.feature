Feature: Discovery skill selection

  Scenario: The team receives a discovery result from an admitted skill
    Given three discovery skills are admitted for the team's workspace
    When the team starts a discovery task
    Then exactly one admitted skill release is activated or none is chosen
    And the team can revisit discovery later
