# Architecture Preflight: <feature_name>

<!-- INSTRUCTIONS
     Level 5 — GenAI Operations
     Complete every section before plan finalization.
     Sections 1-9 are standard L4 preflight.
     Sections 10-14 are L5 GenAI-specific checks.
     Status must be "Approved for planning" before implementation begins.
     Template source: governance/backend/templates/l5-architecture-preflight.md
-->

This document validates architectural, security, evaluation, and GenAI alignment
before implementation begins.

Preflight is required once per feature and must be updated if scope materially changes.

---

## 1. Artifact Review

Feature folder: `features/<feature_name>/`

- acceptance.feature reviewed: yes/no
- nfrs.md reviewed: yes/no — no TBD entries: yes/no
- eval_criteria.yaml exists: yes/no
- plan.md exists: yes/no
- Gherkin scenarios cover all populated NFR categories per `docs/backend/architecture/GHERKIN_CONVENTIONS.md`: yes/no
- `@contract` scenario present (if feature produces shared artifact): yes/no/n-a

If any required artifact is missing, stop.
If nfrs.md contains TBD entries, stop and request completion before proceeding.
If NFR tag coverage is incomplete, stop and request completion before proceeding.

---

## 2. Standards Referenced

List specific sections referenced from:

- `docs/backend/architecture/ARCH_CONTRACT.md`
- `docs/backend/architecture/BOUNDARIES.md`
- `docs/backend/architecture/API_CONVENTIONS.md`
- `docs/backend/architecture/SECURITY_AUTH_PATTERNS.md`
- `docs/backend/evaluation/eval_criteria.md`

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

Confirm compliance with `docs/backend/architecture/BOUNDARIES.md`.

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

From `eval_criteria.yaml` and `docs/backend/evaluation/eval_criteria.md`:

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

- Produces shared artifact: yes/no
- Artifact type:
- Artifact location (path or registry):
- Downstream consumers identified:
- Versioning strategy:
- Backward compatibility requirement: yes/no

If no shared artifact, state: "No shared contract produced."

---

## 9. Preflight Conclusion (L4)

- Architecture alignment: compliant | requires ADR | blocked
- Security alignment: compliant | requires ADR | blocked
- Evaluation alignment: compliant | update required | blocked

---

## 10. LLM Gateway Configuration (Level 5)

- LiteLLM configured as sole gateway: yes/no
- Model alias(es) used:
- Fallback chain defined: yes/no
- Cost budget defined in nfrs.md: yes/no
- Direct provider SDK imports present (prohibited): yes/no

Contract: `docs/backend/architecture/LLM_GATEWAY_CONTRACT.md`

---

## 11. Observability Configuration (Level 5)

- OpenLLMetry instrumentation configured: yes/no
- Langfuse trace export configured: yes/no
- Prompt versioning in Langfuse: yes/no/not-applicable
- Environment matrix confirmed: yes/no

Contract: `docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md`

---

## 12. Guardrails Configuration (Level 5)

- Guardrail mode: nemo | guardrails-ai | both | none
- NeMo rail definitions path (if applicable):
- Guardrails AI validators (if applicable):
- Justification (if mode is none):
- Bypass allowed: yes/no (if yes, ADR required)

Contract: `docs/backend/architecture/GUARDRAILS_CONTRACT.md`

---

## 13. Evaluation Strategy (Level 5)

- DeepEval metrics defined in eval_criteria.yaml: yes/no
- DeepEval metrics selected:
- Promptfoo required: yes/no
- Promptfoo adversarial scenarios defined: yes/no (if required)
- RAGAS required (feature uses retrieval): yes/no
- RAGAS metrics selected (if required):
- Evaluation dataset path:

Contract: `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md`

---

## 14. LLM NFR Validation (Level 5)

Confirm these NFR categories are populated in nfrs.md (no TBD entries):

- LLM Latency: populated/TBD
- LLM Cost: populated/TBD
- LLM Fallback: populated/TBD
- LLM Safety: populated/TBD

If any LLM NFR is TBD, stop and request completion.

---

## 15. Final Status

- L4 preflight status: approved | blocked
- L5 GenAI status: approved | blocked
- Combined status: **Approved for planning** | **Blocked pending resolution**
