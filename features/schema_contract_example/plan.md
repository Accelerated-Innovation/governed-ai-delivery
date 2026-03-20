# Feature Plan: schema_contract_example

---

## Objective

- A schema publication service that writes versioned schemas to a central registry and allows downstream consumers to retrieve them by id and version
- Platform teams and dependent services benefit by having a single authoritative source for shared schemas, reducing integration drift
- Success: all acceptance scenarios pass; schema immutability enforced; auth gates verified; p99 retrieval < 100ms under 100 concurrent requests

---

## Scope Boundaries

### In scope
- Schema publication port and adapter (outbound)
- Schema retrieval port and adapter (outbound)
- Domain service orchestrating publish/retrieve with retry logic
- Auth enforcement at the inbound API boundary
- Structured logging of lifecycle events

### Out of scope
- Schema validation tooling for consumers (separate feature)
- Schema deprecation and retirement workflows (future increment)
- Schema search or discovery UI

### Assumptions
- The schema registry external service is available and documented in `docs/backend/architecture/TECH_STACK.md`
- Auth token validation follows the approved pattern in `docs/backend/architecture/SECURITY_AUTH_PATTERNS.md`
- Schema documents are JSON Schema Draft 2020-12

---

## Architecture Alignment

### Relevant contracts
- docs/backend/architecture/ARCH_CONTRACT.md: hexagonal architecture, inbound/outbound port rules
- docs/backend/architecture/BOUNDARIES.md: no cross-layer imports; adapters depend on ports, not vice versa
- docs/backend/architecture/API_CONVENTIONS.md: REST naming, versioning, error response structure
- docs/backend/architecture/SECURITY_AUTH_PATTERNS.md: token scope enforcement at inbound port
- docs/backend/evaluation/eval_criteria.md: FIRST principles, 7 Virtues, deterministic mode

### ADRs

- New ADRs required:
  - ADR-001: Schema contract ownership and versioning strategy
- Existing ADRs referenced:
  - None

### Interfaces and dependencies

- Inbound ports: `SchemaPublicationPort` (publish), `SchemaRetrievalPort` (retrieve)
- Domain services: `SchemaContractService` (orchestrates publish with retry, enforces immutability)
- Outbound ports: `SchemaRegistryPort` (external registry adapter)
- Adapters: `HttpSchemaRegistryAdapter` implements `SchemaRegistryPort`
- Data stores/events touched: external schema registry (via HTTP adapter)
- External dependencies: schema registry service

### Shared contract artifacts

- Shared artifacts produced: `governance/backend/schemas/order-events.schema.json` (example schema published by this feature)
- Artifact type(s): JSON Schema
- Downstream consumers: order-processing service, audit service
- Versioning strategy: integer version increments; new version required for breaking changes
- Breaking change policy: backward-incompatible changes require a new version — existing versions are immutable
- ADR reference: ADR-001

### Security and compliance

- AuthN/AuthZ: token scope `schema:publish` enforced at inbound API layer; unauthenticated requests return 401; unauthorized scope returns 403
- Data classification and PII handling: schema metadata only — no PII in schema identifiers or publication logs
- Threats and mitigations: schema injection via metadata fields — validate schema structure before acceptance; internal service name exposure — use opaque schema IDs

---

## Evaluation Compliance Summary (MANDATORY)

Predicted BEFORE implementation begins. All score and evidence fields must be populated — null values are not permitted at plan finalization.

```yaml
evaluation_prediction:
  first:
    fast:           { score: 5, evidence: "Registry adapter is mocked in unit tests; no real HTTP calls" }
    isolated:       { score: 5, evidence: "Dependency injection for all ports; no shared mutable state between tests" }
    repeatable:     { score: 5, evidence: "No time-dependent logic in domain service; retry logic uses injected clock" }
    self_verifying: { score: 5, evidence: "All scenarios have explicit assertions; no log-inspection required" }
    timely:         { score: 4, evidence: "Tests written per increment before implementation; minor risk on retry edge cases" }
    average: 4.8
  virtues:
    working:   { score: 5, evidence: "All acceptance scenarios covered; immutability and auth edge cases handled" }
    unique:    { score: 5, evidence: "Retry logic extracted to shared utility; no duplication across adapters" }
    simple:    { score: 4, evidence: "Retry loop adds minor branching; kept to single method with clear exit conditions" }
    clear:     { score: 5, evidence: "Port interfaces named by intent; domain service methods map 1:1 to scenarios" }
    easy:      { score: 5, evidence: "Domain service depends only on port interfaces; adapter is swappable" }
    developed: { score: 5, evidence: "All tests written; no dead code; consistent error response structure" }
    brief:     { score: 4, evidence: "Retry utility is generalized but genuinely reused; not speculative" }
    average: 4.71
  thresholds_met: true
```

### Refactor Triggers Identified

- Structural complexity risks: retry loop in domain service — extract to a dedicated retry utility if it exceeds 3 callers
- Duplication risks: auth token validation — must use shared middleware, not inline per route
- Boundary risks: adapter must not be imported directly by domain service — enforce via import-linter
- Test fragility risks: retry tests depend on mock call counts — use explicit state assertions instead where possible

---

## Increments

### Increment 1: Ports and domain service

**Goal**
- Define `SchemaRegistryPort`, `SchemaPublicationPort`, `SchemaRetrievalPort`
- Implement `SchemaContractService` with publish, retrieve, and retry logic

**Deliverables**
- `src/ports/schema_registry_port.py`
- `src/ports/schema_publication_port.py`
- `src/ports/schema_retrieval_port.py`
- `src/services/schema_contract_service.py`

**Implementation notes**
- Immutability check: on publish, call retrieve first; if version exists and body differs, raise `SchemaConflictError`
- Retry: up to 3 attempts with exponential backoff; configurable via injected settings

**Architecture impact**
- Ports affected: three new outbound ports
- Adapters affected: none yet
- Boundary risks: none in this increment

**Tests**
- Unit (FIRST compliant): publish happy path, immutability conflict, retry exhaustion, retry success on third attempt
- Integration: none in this increment
- Contract: none in this increment

**Evaluation impact**
- LLM eval required? no
- Criteria names impacted: none
- Threshold impact: none
- Eval dataset reference: n/a

**Definition of Done**
- All unit tests pass
- FIRST average >= 4.0
- No boundary violations
- Retry logic covered by tests

---

### Increment 2: HTTP adapter and API layer

**Goal**
- Implement `HttpSchemaRegistryAdapter`
- Implement inbound API routes for publish and retrieve with auth enforcement

**Deliverables**
- `src/adapters/http_schema_registry_adapter.py`
- `src/api/schema_routes.py`

**Implementation notes**
- Auth enforcement at route level using middleware from `SECURITY_AUTH_PATTERNS.md`
- Adapter maps HTTP responses to port errors — no business logic in adapter
- OpenAPI spec updated with new routes

**Architecture impact**
- Ports affected: `HttpSchemaRegistryAdapter` implements `SchemaRegistryPort`
- Adapters affected: new adapter
- Boundary risks: must not import domain service directly — routes call port, not adapter

**Tests**
- Unit (FIRST compliant): adapter maps 201/409/503 to correct port types; auth middleware rejects missing/invalid tokens
- Integration: publish then retrieve via HTTP; 409 on duplicate version
- Contract: retrieve returns schema matching published document byte-for-byte

**Evaluation impact**
- LLM eval required? no
- Criteria names impacted: none
- Threshold impact: none
- Eval dataset reference: n/a

**Definition of Done**
- All unit and integration tests pass
- OpenAPI spec updated
- Auth scenarios from `acceptance.feature` automated
- FIRST and Virtue averages >= 4.0
- import-linter boundary check passes

---

### Increment 3: Observability and compliance

**Goal**
- Add structured logging for lifecycle events (publish, retrieve, conflict, retry)
- Verify audit log completeness

**Deliverables**
- Structured log calls in `SchemaContractService`
- Log format aligned with `docs/backend/architecture/ARCH_CONTRACT.md` logging standards

**Implementation notes**
- Logs must include: correlation ID, schema ID, version, actor identity, timestamp
- Logs must NOT include schema body

**Architecture impact**
- Ports affected: none
- Adapters affected: none
- Boundary risks: none

**Tests**
- Unit (FIRST compliant): log output verified via log capture; schema body absent from logs
- Integration: end-to-end publish emits expected log fields
- Contract: none

**Evaluation impact**
- LLM eval required? no
- Criteria names impacted: none
- Threshold impact: none
- Eval dataset reference: n/a

**Definition of Done**
- All observability and compliance Gherkin scenarios automated
- Log format verified by unit tests
- No schema body in any log output

---

## Risks

- Risk: schema registry external service is unavailable in test environments
  - Impact: integration tests cannot run against real registry
  - Mitigation: use a local stub (e.g., WireMock or a simple in-memory fake) for integration tests; document in `docs/backend/architecture/TECH_STACK.md`

- Risk: breaking change detection relies on manual versioning discipline
  - Impact: a developer could publish a structurally incompatible schema as a new version without bumping the version
  - Mitigation: CI contract compatibility check in `ci/quality-gate-example.yml` validates schema diff against base branch

---

## Definition of Done (Feature-Level)

- Acceptance criteria satisfied (`acceptance.feature`) — all scenarios automated
- NFRs satisfied (`nfrs.md`) — no TBD entries; all categories covered by tagged Gherkin scenarios
- Evaluation criteria satisfied (`eval_criteria.yaml`) — schema-validated
- FIRST principles satisfied — average >= 4.0
- 7 Virtue thresholds satisfied — average >= 4.0
- CI passes (tests, quality, eval gates)
- No boundary violations (import-linter clean)
- ADR-001 Accepted and referenced in PR description
- OpenAPI spec updated
- PR includes links to plan, preflight, and ADR-001
