Feature: Schema Contract Publication

  As a service that produces a shared schema
  I want to publish versioned schemas to a central registry
  So that downstream consumers can retrieve and validate against a stable contract

  Background:
    Given the schema registry is available
    And the publishing service has a valid token with scope "schema:publish"

  # ── Happy path ──────────────────────────────────────────────────────────────

  @contract
  Scenario: Successfully publish a new schema version
    Given a valid schema document with id "order-events" and version 1
    When the service publishes the schema to the registry
    Then the schema is stored with status 201 Created
    And the schema is retrievable by id "order-events" and version 1

  @contract
  Scenario: Downstream consumer retrieves a published schema by version
    Given the schema "order-events" version 1 has been published
    When a downstream consumer requests the schema by id and version
    Then the response is 200 OK
    And the response body contains the full schema document

  # ── Immutability ─────────────────────────────────────────────────────────────

  @contract
  Scenario: Published schema versions are immutable
    Given the schema "order-events" version 1 has been published
    When the service attempts to overwrite version 1 with a different schema body
    Then the response is 409 Conflict
    And the original schema version 1 is unchanged

  # ── Security ─────────────────────────────────────────────────────────────────

  @nfr-security
  Scenario: Unauthorized publish attempt is rejected
    Given a request with a token missing the "schema:publish" scope
    When the service attempts to publish a schema
    Then the response is 403 Forbidden
    And no schema is written to the registry

  @nfr-security
  Scenario: Unauthenticated retrieval attempt is rejected
    Given a request with no authentication token
    When a consumer attempts to retrieve a schema
    Then the response is 401 Unauthorized

  # ── Availability ─────────────────────────────────────────────────────────────

  @nfr-availability
  Scenario: Publication is retried on transient registry failure
    Given the schema registry returns a 503 on the first two attempts
    When the service publishes a schema
    Then the service retries up to 3 times
    And on the third attempt succeeding, the schema is published successfully

  # ── Performance ──────────────────────────────────────────────────────────────

  @nfr-performance
  Scenario: Schema retrieval meets latency target under load
    Given 100 concurrent consumers requesting schemas
    When all requests are processed
    Then p99 retrieval latency is below 100ms

  # ── Observability ────────────────────────────────────────────────────────────

  @nfr-observability
  Scenario: Publication emits a structured log event
    Given a valid schema is published
    When the publish operation completes
    Then a structured log entry is emitted containing schema id, version, publishing service identity, and timestamp
    And the log entry does not contain the full schema body

  # ── Compliance ───────────────────────────────────────────────────────────────

  @nfr-compliance
  Scenario: Schema lifecycle events are auditable
    Given a schema has been published and later deprecated
    When the audit log is queried for "order-events"
    Then both the publish and deprecate events are present with timestamps and actor identity

  # ── Scalability ──────────────────────────────────────────────────────────────

  @nfr-scalability
  Scenario: Schema registry adapter handles horizontal scaling
    Given multiple instances of the schema service are running
    When schemas are published and retrieved across different instances
    Then all instances return consistent results for the same schema id and version
