# Architecture Preflight: <feature_name>

<!-- INSTRUCTIONS
     Complete every section before plan finalization.
     Status must be "Approved for planning" before implementation begins.
     See features/schema_contract_example/architecture_preflight.md for a complete worked example.
     Template source: governance/backend/templates/architecture_preflight.md
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

## 8.5 Architecture Uncertainty and Experiments

List each architectural assumption this design depends on and its basis.

| Assumption | Basis | Material? | Action |
|---|---|---|---|
|  | accepted contract / accepted ADR / current experiment (EXP-…) / untested | yes/no | none / ADR / experiment EXP-… / narrower scope |

- Supported by an accepted contract, an accepted ADR or a current passed and adopted experiment: no experiment needed.
- A known violation of an accepted boundary needs an ADR or an authorized narrower scope; an experiment cannot excuse it.
- A material, untested assumption needs an experiment. Record it in `features/<feature_name>/experiments.yaml` (schema: `governance/schemas/experiment-set.schema.json`) and set the outcome below to `experiment-required`.

Do not label an untested design approved in order to start a prototype. Experiments do not change accepted requirements.

---

## 9. Preflight Conclusion

- Architecture alignment: compliant | requires ADR | blocked
- Security alignment: compliant | requires ADR | blocked
- Evaluation alignment: compliant | update required | blocked

Final status:
- Approved for planning
- Experiment required
- Blocked pending ADR
- Blocked pending clarification

Record the outcome in this single machine-readable block (schema:
`governance/schemas/preflight-outcome.schema.json`). `govkit validate` checks it;
run `govkit validate --target . --strict` before declaring the feature complete.

```yaml
preflight_outcome:
  status: blocked   # approved-for-planning | experiment-required | adr-required | blocked
  reason: Preflight not yet completed.
  # experiments: [EXP-001]          # with experiment-required
  # relies_on:                      # passed, adopted experiments supporting approval
  #   - experiment: EXP-001
  #     result_digest: <result digest>
```
