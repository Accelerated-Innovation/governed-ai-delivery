# ADR-001: Schema Contract Ownership and Versioning Strategy

## Status
Accepted

## Date
2026-03-20

## Authors
- Platform Architect

---

## 1. Context

The `schema_contract_example` feature introduces the first service in this repository that produces a shared schema consumed by other services (order-processing, audit). Without an explicit ownership and versioning model, downstream consumers face:

- No guarantee that a schema will remain stable once published
- No mechanism to distinguish breaking from non-breaking changes
- No clear authority for who may publish or retire a schema version

Relevant constraints:
- `docs/backend/architecture/BOUNDARIES.md`: shared artifacts must not create hidden coupling between services
- `docs/backend/architecture/ARCH_CONTRACT.md`: inter-service contracts must be explicit and versioned
- ADR trigger: "A shared schema, API contract, event definition, or data model is introduced or modified that will be consumed by other features, services, or agents"

References:
- `features/schema_contract_example/plan.md`
- `features/schema_contract_example/architecture_preflight.md` Section 8

---

## 2. Decision

> Schemas produced for shared consumption are published to a central registry under an integer version. Published versions are immutable. Breaking changes require a new version number. The producing service owns the schema; consuming services are notified before a version is deprecated.

Ownership rule: the service that first publishes a schema ID owns it. Other services may not publish to the same schema ID without an ADR.

---

## 3. Architectural Impact

### 3.1 Boundaries
- Layers/services affected: schema publication domain service; schema registry outbound port and adapter
- Dependency direction changes: none — adapter continues to depend on port
- New modules introduced: `SchemaRegistryPort`, `HttpSchemaRegistryAdapter`, `SchemaContractService`

Confirmed: no forbidden cross-layer access. Dependency direction complies with `BOUNDARIES.md`.

### 3.2 API Impact
- Route changes: `POST /schemas/{id}/versions`, `GET /schemas/{id}/versions/{version}` (new)
- Versioning impact: new routes only; no existing routes modified
- Error model impact: 409 Conflict added for immutability violation
- OpenAPI updates required: yes — Increment 2

### 3.3 Security Impact
- Auth pattern used: token scope `schema:publish` for publish; any valid token for retrieval
- Authorization changes: new scope `schema:publish` introduced
- Token handling implications: actor identity extracted for audit logging; token not stored
- Data classification considerations: schema content is not PII; schema IDs must be opaque
- Logging/redaction implications: schema body must not be logged — schema ID and version only

---

## 4. Alternatives Considered

### Option A: Schema files committed to the repository only
- Description: schemas live as files in `governance/backend/schemas/`; no runtime registry
- Pros: simple; no new infrastructure; version history via git
- Cons: consuming services cannot retrieve schemas at runtime; no enforcement of immutability at publish time; no health check or availability guarantee
- Why rejected: runtime consumers need reliable retrieval; git is not a service dependency

### Option B: Schemas embedded in OpenAPI specs
- Description: shared schemas defined inline in each service's OpenAPI spec; no separate registry
- Pros: no new infrastructure; tooling already in place
- Cons: duplication across specs; no single source of truth; drift inevitable; breaking changes invisible to consumers
- Why rejected: creates the hidden coupling problem this ADR exists to prevent

---

## 5. Evaluation Impact

This decision does not affect LLM evaluation criteria. The feature uses `mode: deterministic`.

Affected eval criteria: none. FIRST and Virtue thresholds unchanged.

No evaluation impact.

---

## 6. Risks and Tradeoffs

- Technical risks: schema registry external service availability — mitigated by retry logic and health check endpoint
- Operational risks: schema ID ownership is enforced by convention, not code, until a registry-level ownership model is implemented — document in registry runbook
- Security risks: `schema:publish` scope is new — ensure token issuance process is updated
- Performance implications: schema retrieval adds one external call per consumer startup — acceptable given 100ms p99 target and local caching by consumers

Mitigations:
- Retry logic (3 attempts, exponential backoff) in `SchemaContractService`
- Import-linter boundary check in CI
- Contract compatibility check in CI for `@contract`-tagged scenarios

---

## 7. Plan Alignment

- Feature plan increments impacted: all three increments reference this ADR
- New increment required: no — existing three increments cover the decision
- Scope adjustments required: no

`plan.md` references ADR-001 under Architecture Alignment > ADRs.

---

## 8. Consequences

### Positive
- Downstream consumers have a stable, versioned contract they can depend on
- Breaking changes are surfaced explicitly via a version bump
- Immutability prevents silent breakage of deployed consumers

### Negative
- Adds a runtime dependency on the schema registry service
- Schema owners must coordinate deprecation with consumers before retiring a version

### Neutral
- Integer versioning is simple but coarse — semantic versioning is not used (YAGNI)

---

## 9. Follow-Up Actions

- Code changes required: implement `SchemaRegistryPort`, `HttpSchemaRegistryAdapter`, `SchemaContractService` per plan increments
- Documentation updates required: add schema registry to `docs/backend/architecture/TECH_STACK.md`; update OpenAPI spec in Increment 2
- CI updates required: contract compatibility check in `ci/github/quality-gate.yml` (already configured)
- Security review required: yes — new scope `schema:publish` requires token issuance process update

---

## 10. Approval

Approved by:
- Architect: Platform Architect — 2026-03-20
- Security: required before Increment 2 deployment (new auth scope)
- Product: no scope impact
