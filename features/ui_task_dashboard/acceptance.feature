Feature: Task Dashboard

  As an authenticated user
  I want to view and manage tasks assigned to me
  So that I can track my work status from a single dashboard

  Background:
    Given I am authenticated as a user with assigned tasks
    And the task API is available at "/api/tasks"

  # ── View ──────────────────────────────────────────────────────────────────────

  @e2e
  Scenario: User views all assigned tasks on load
    Given I have 3 open tasks and 1 completed task assigned to me
    When I navigate to the task dashboard
    Then I see a list of all 4 tasks
    And the open task count badge displays "3"
    And each task card shows the task title and current status

  @e2e
  Scenario: User marks a task as complete
    Given the task dashboard displays at least one open task
    When I click the "Mark complete" button on an open task
    Then the task status updates to "Done"
    And the open task count badge decreases by one
    And a status announcement is made to assistive technology

  @e2e
  Scenario: User filters tasks by status
    Given the task dashboard displays tasks with mixed statuses
    When I select the "Open" filter
    Then only open tasks are visible
    And completed tasks are not rendered in the list

  @e2e
  Scenario: Task list displays a graceful error state when the API is unavailable
    Given the task API returns a 503 response
    When the task dashboard loads
    Then an error message is displayed to the user
    And no unhandled exception is thrown
    And the page remains interactive

  # ── Accessibility ─────────────────────────────────────────────────────────────

  @accessibility
  Scenario: Task list is keyboard navigable
    Given the task dashboard is displayed with tasks
    When I navigate the task list using Tab and Enter keys
    Then focus moves sequentially through each task card
    And I can activate "Mark complete" without using a mouse
    And focus is not trapped unexpectedly

  @accessibility
  Scenario: Open task count badge is announced to screen readers
    Given I have 3 open tasks
    When the task dashboard loads
    Then the open task count badge has an accessible label readable by screen readers

  @accessibility
  Scenario: Task status change is announced via live region
    Given the task dashboard is displayed with an open task
    When I mark a task as complete
    Then the status change is announced via an aria-live region
    And the announcement does not require a page reload

  @accessibility
  Scenario: No critical accessibility violations on initial render
    Given the task dashboard renders with task data
    When an automated accessibility scan (axe-core) is run against the page
    Then zero critical violations are reported
    And zero serious violations are reported

  # ── Security ─────────────────────────────────────────────────────────────────

  @nfr-security
  Scenario: Unauthenticated users cannot access the task dashboard
    Given I am not authenticated
    When I navigate to the task dashboard
    Then I am redirected to the login page
    And no task data is fetched or exposed

  @nfr-security
  Scenario: Task data is scoped to the authenticated user
    Given I am authenticated as user A
    When the task dashboard loads
    Then the API request includes the authenticated user's credentials
    And only tasks assigned to user A are rendered

  # ── Performance ───────────────────────────────────────────────────────────────

  @nfr-performance
  Scenario: Task list renders within the LCP performance budget
    Given the task API responds within 200ms
    When the task dashboard loads
    Then the task list is visible within 1000ms (LCP target)
    And the Cumulative Layout Shift score is below 0.1

  @nfr-performance
  Scenario: Optimistic update provides immediate feedback on task completion
    Given the task dashboard displays an open task
    When I click "Mark complete"
    Then the task card visually updates to "Done" before the API mutation resolves

  # ── Availability ──────────────────────────────────────────────────────────────

  @nfr-availability
  Scenario: Stale task data remains visible during a background refetch
    Given the task dashboard has previously loaded task data
    When a background refetch is in progress
    Then the previously loaded tasks remain visible
    And a loading indicator is shown without hiding existing content
