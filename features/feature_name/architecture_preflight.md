# Architecture Preflight: <feature_name>

<!-- INSTRUCTIONS
     Complete every section before plan finalization.
     Status must be "Approved for planning" before implementation begins.
     See features/schema_contract_example/architecture_preflight.md for a complete worked example.
     Template source: governance/templates/architecture_preflight.md
-->

This document validates architectural, security, and evaluation alignment
before implementation begins.

Preflight is required once per feature and must be updated if scope materially changes.

---

## 1. Artifact Review

Feature folder: `features/<feature_name>/`

- acceptance.feature reviewed: yes/no
- nfrs.md reviewed: yes/no — no TBD entries: yes/no
- eval_criteria.yaml exists: yes/no
- plan.md exists: yes/no
- Gherkin scenarios cover all populated NFR categories per `docs/architecture/GHERKIN_CONVENTIONS.md`: yes/no
- `@contract` scenario present (if feature produces shared artifact): yes/no/n-a

If any required artifact is missing, stop.
If nfrs.md contains TBD entries, stop and request completion before proceeding.
If NFR tag coverage is incomplete, stop and request completion before proceeding.

---

## 2. Standards Referenced

List specific sections referenced from:

- `docs/architecture/ARCH_CONTRACT.md`
- `docs/architecture/BOUNDARIES.md`
- `docs/architecture/API_CONVENTIONS.md`
- `docs/architecture/SECURITY_AUTH_PATTERNS.md`
- `docs/evaluation/eval_criteria.md`

Cite file names and section headings.

---

## 3. Boundary Analysis

- Inbound ports impacted:
- Domain services impacted:
- Outbound ports impacted:
- Adapters impacted:
- Dependency direction:
- Cross-layer violations introduced: yes/no
- Boundary risks identified:
- Mitigations:

Confirm compliance with `BOUNDARIES.md`.

---

## 4. API Impact

- API changes required: yes/no
- Routes affected:
- Versioning impact:
- Request/response structure changes:
- Error model impact:
- OpenAPI updates required: yes/no

If no API impact, state: "No API impact."

---

## 5. Security Impact

- Auth pattern used:
- Authorization enforcement points:
- Identity propagation impact:
- Token handling implications:
- Logging/redaction considerations:
- Threat considerations:

If no security impact, state: "No security impact."

---

## 6. Evaluation Impact

From `eval_criteria.yaml` and `docs/evaluation/eval_criteria.md`:

- Mode: llm | deterministic | none
- FIRST enforcement required: yes/no
- 7 Virtue enforcement required: yes/no
- LLM criteria affected:
- Threshold implications:
- CI evaluation gate impact:
- Refactor risk areas identified:

If mode is `none`, confirm documented rationale exists.

Confirm evaluation thresholds are achievable given architecture design.

---

## 7. ADR Determination

ADR required: yes/no

If yes:
- Proposed title:
- Scope:
- Trigger condition:

If no:
- Justification:

---

## 8. Shared Contract Analysis

Does this feature produce an artifact consumed by other features, services, or agents?

Examples: JSON schema, OpenAPI spec, event definition, message contract, shared data model.

- Produces shared artifact: yes/no
- Artifact type:
- Artifact location (path or registry):
- Downstream consumers identified:
- Versioning strategy:
  - Initial version:
  - Breaking change policy:
- Backward compatibility requirement: yes/no
- Contract validation mechanism:
- ADR required for contract ownership: yes/no

If yes and ADR is not required, justify:

If no shared artifact, state: "No shared contract produced."

---

## 9. Preflight Conclusion

- Architecture alignment: compliant | requires ADR | blocked
- Security alignment: compliant | requires ADR | blocked
- Evaluation alignment: compliant | update required | blocked

Final status:
- Approved for planning
- Blocked pending ADR
- Blocked pending clarification
