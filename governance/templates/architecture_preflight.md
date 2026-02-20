# Architecture Preflight: <feature_name>

This document validates architectural, security, and evaluation alignment
before implementation begins.

Preflight is required once per feature and must be updated if scope materially changes.

---

## 1. Artifact Review

Feature folder: `features/<feature_name>/`

- acceptance.feature reviewed: yes/no
- nfrs.md reviewed: yes/no
- eval_criteria.yaml exists: yes/no
- plan.md exists: yes/no

If any required artifact is missing, stop.

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

## 8. Preflight Conclusion

- Architecture alignment: compliant | requires ADR | blocked
- Security alignment: compliant | requires ADR | blocked
- Evaluation alignment: compliant | update required | blocked

Final status:
- Approved for planning
- Blocked pending ADR
- Blocked pending clarification