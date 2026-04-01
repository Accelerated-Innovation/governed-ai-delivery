# Architecture Preflight: schema_contract_example

This document validates architectural, security, and evaluation alignment
before implementation begins.

Preflight is required once per feature and must be updated if scope materially changes.

---

## 1. Artifact Review

Feature folder: `features/schema_contract_example/`

- acceptance.feature reviewed: yes
- nfrs.md reviewed: yes — no TBD entries: yes
- eval_criteria.yaml exists: yes
- plan.md exists: yes
- Gherkin scenarios cover all populated NFR categories per `docs/backend/architecture/GHERKIN_CONVENTIONS.md`: yes
  - @nfr-performance: yes (1 scenario)
  - @nfr-security: yes (2 scenarios)
  - @nfr-availability: yes (1 scenario)
  - @nfr-scalability: yes (1 scenario)
  - @nfr-observability: yes (1 scenario)
  - @nfr-compliance: yes (1 scenario)
- `@contract` scenario present (feature produces shared artifact): yes (3 scenarios)

---

## 2. Standards Referenced

- `docs/backend/architecture/ARCH_CONTRACT.md`: hexagonal architecture; inbound/outbound port separation; structured logging standards
- `docs/backend/architecture/BOUNDARIES.md`: adapters depend on ports; domain service must not import adapters
- `docs/backend/architecture/API_CONVENTIONS.md`: REST route naming; HTTP error codes; OpenAPI update requirement
- `docs/backend/architecture/SECURITY_AUTH_PATTERNS.md`: token scope enforcement; 401/403 response behavior
- `docs/backend/evaluation/eval_criteria.md`: FIRST principles; 7 Virtues; deterministic mode; thresholds (4.0 average)
- `docs/backend/architecture/GHERKIN_CONVENTIONS.md`: NFR tagging; @contract tag requirement; coverage rules
- `docs/backend/architecture/DESIGN_PRINCIPLES.md`: SOLID/DRY/YAGNI mapping to 7 Virtues

---

## 3. Boundary Analysis

- Inbound ports impacted: `SchemaPublicationPort`, `SchemaRetrievalPort` (new)
- Domain services impacted: `SchemaContractService` (new)
- Outbound ports impacted: `SchemaRegistryPort` (new)
- Adapters impacted: `HttpSchemaRegistryAdapter` (new, implements `SchemaRegistryPort`)
- Dependency direction: API → domain service via inbound port; domain service → registry via outbound port; adapter implements outbound port — all inward
- Cross-layer violations introduced: no
- Boundary risks identified: risk that API route imports adapter directly (bypassing port)
- Mitigations: import-linter rule added to `ci/github/quality-gate.yml`

Compliant with `BOUNDARIES.md`.

---

## 4. API Impact

- API changes required: yes
- Routes affected: `POST /schemas/{id}/versions`, `GET /schemas/{id}/versions/{version}`
- Versioning impact: new routes — no existing routes modified; no breaking change
- Request/response structure changes: new request/response schemas
- Error model impact: 409 Conflict added for immutability violation; follows existing error model
- OpenAPI updates required: yes — to be completed in Increment 2

---

## 5. Security Impact

- Auth pattern used: token scope enforcement per `SECURITY_AUTH_PATTERNS.md` — `schema:publish` scope required for publish routes; retrieval routes require authenticated token (any valid scope)
- Authorization enforcement points: inbound API middleware; enforced before request reaches domain service
- Identity propagation impact: publishing actor identity extracted from token and passed to domain service for logging
- Token handling implications: no token stored or logged — actor identity only
- Logging/redaction considerations: schema body must not appear in logs; actor identity and schema ID are logged
- Threat considerations: schema injection via metadata — schema structure validated before acceptance; internal service name exposure — opaque schema IDs enforced

---

## 6. Evaluation Impact

From `eval_criteria.yaml` and `docs/backend/evaluation/eval_criteria.md`:

- Mode: deterministic
- FIRST enforcement required: yes — minimum average 4.0
- 7 Virtue enforcement required: yes — minimum average 4.0
- LLM criteria affected: none (mode is deterministic)
- Threshold implications: predicted averages 4.8 (FIRST) and 4.71 (Virtues) — both above threshold
- CI evaluation gate impact: `ci/github/eval-gate.yml` will check prediction block completeness; `ci/github/quality-gate.yml` will validate eval_criteria.yaml against schema
- Refactor risk areas identified: retry logic branching; import-linter boundary enforcement

Evaluation thresholds are achievable given the architecture design.

---

## 7. ADR Determination

ADR required: yes

- Proposed title: ADR-001: Schema Contract Ownership and Versioning Strategy
- Scope: Establishes schema ownership model, immutability rule, versioning strategy, and downstream consumer contract for schemas produced by this feature
- Trigger condition: shared schema produced by this feature consumed by other services — ADR trigger per `CLAUDE.md` and `copilot-instructions.md`

---

## 8. Shared Contract Analysis

- Produces shared artifact: yes
- Artifact type: JSON Schema (Draft 2020-12)
- Artifact location: `governance/backend/schemas/<schema-id>.schema.json`; registered in schema registry
- Downstream consumers identified: order-processing service, audit service
- Versioning strategy:
  - Initial version: 1
  - Breaking change policy: breaking changes require a new integer version; existing versions are immutable
- Backward compatibility requirement: yes — consumers must not be broken by a new publish
- Contract validation mechanism: CI contract compatibility check in `ci/github/quality-gate.yml`; triggered by `@contract` tagged scenarios
- ADR required for contract ownership: yes — ADR-001

---

## 9. Preflight Conclusion

- Architecture alignment: compliant
- Security alignment: compliant
- Evaluation alignment: compliant

Final status: **Approved for planning** — pending ADR-001 Accepted before implementation begins
