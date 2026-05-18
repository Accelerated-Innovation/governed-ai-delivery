Feature: Hello World UI Card

  As a developer smoke-testing the govkit install
  I want a minimal greeting card on a page
  So that I can confirm UI scaffolding and validation work end to end

  @e2e
  Scenario: Render the default greeting
    Given the hello card page is loaded
    When the page finishes rendering
    Then the card displays the text "hello, world"

  @e2e @nfr-performance
  Scenario: Page meets the LCP target on a standard connection
    Given the hello card page is loaded on a standard 4G profile
    When Core Web Vitals are measured
    Then Largest Contentful Paint is below 2500ms
