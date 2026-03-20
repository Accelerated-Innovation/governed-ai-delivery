# Non-Functional Requirements: Schema Contract Publication

## Performance
- Schema publication must complete within 500ms under normal load
- Schema retrieval by downstream consumers must respond within 100ms at p99
- The schema registry adapter must support at least 100 concurrent read requests without degradation

## Availability
- The schema registry must be available 99.9% of the time during business hours
- Schema publication failures must be retried up to 3 times with exponential backoff before raising an error
- A published schema version must remain retrievable for the lifetime of any active consumer

## Security
- Only authenticated services with the `schema:publish` scope may publish schemas
- All schema registry API calls must be authenticated via the approved token pattern defined in `docs/architecture/SECURITY_AUTH_PATTERNS.md`
- Schema content must be validated before publication to prevent injection via schema metadata fields
- Schema identifiers must not expose internal service names or infrastructure details

## Compliance
- All schema publication events must be logged with the publishing service identity, timestamp, schema ID, and version
- Logs must not include the full schema body — only the schema ID and version
- Schema lifecycle events (publish, deprecate, retire) must be auditable

## Scalability
- The schema registry adapter must be stateless to allow horizontal scaling
- Schema versions must be immutable once published — no in-place updates permitted

## Observability
- Schema publication and retrieval operations must emit structured logs with correlation IDs
- The schema registry adapter must expose a health check endpoint
- Publication failures must emit an error event with schema ID, version, and failure reason

## Dependencies
- Depends on the schema registry service (external adapter) defined in `docs/architecture/TECH_STACK.md`
- Depends on the auth token validation pattern in `docs/architecture/SECURITY_AUTH_PATTERNS.md`
- Downstream consumers depend on the published schema — breaking changes require a new version, not an update

## Testing Requirements
- All NFR categories must have at least one tagged Gherkin scenario per `docs/architecture/GHERKIN_CONVENTIONS.md`
- Contract tests must verify that the published schema is retrievable and structurally valid
- Performance tests must verify p99 retrieval latency under simulated concurrent load
