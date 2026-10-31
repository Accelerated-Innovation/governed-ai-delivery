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

## 9. Preflight Conclusion (L4)

- Architecture alignment: compliant | requires ADR | blocked
- Security alignment: compliant | requires ADR | blocked
- Evaluation alignment: compliant | update required | blocked

---

## 10. LLM Gateway Configuration (Level 5)

- `llm-application` extension installed: yes/no
- Typed model gateway port and adapter paths:
- Logical capability or model alias(es):
- Routing policy/configuration identity:
- Timeout, cancellation, bounded retry, fallback, and degraded behavior:
- Data classification, residency, retention, and provider-use policy:
- Rate, concurrency, token, and financial budgets:
- Tool-call proposal/validation/authorization boundary:
- Direct provider or gateway SDK imports outside adapters (prohibited): yes/no

Contract: `extensions/llm-application/docs/backend/architecture/LLM_GATEWAY_CONTRACT.md`

---

## 11. Observability Configuration (Level 5)

- Observability port and model telemetry adapter paths:
- Required events, usage, latency, failures, and trace correlations:
- Immutable model, prompt, routing, guardrail, retrieval, and configuration identities:
- Raw content capture disabled by default: yes/no
- Redaction-before-export, access, residency, retention, and deletion policy:
- Sampling, bounded cardinality, exporter failure, and evidence-required behavior:

Contract: `extensions/llm-application/docs/backend/architecture/LLM_OBSERVABILITY_CONTRACT.md`

---

## 12. Guardrails Configuration (Level 5)

- Risk categories, users, data classes, and trusted/untrusted sources:
- Required input, context, structural, semantic, content, grounding, and tool-call controls:
- Policy, rule, schema, detector, and threshold identities:
- Refusal, escalation, quarantine, repair, degraded, and fail-closed behavior:
- Fresh tool authorization and approval boundary:
- Inapplicable control points and risk-based justification:
- Bypass allowed: yes/no (if yes, ADR required)

Contract: `extensions/llm-application/docs/backend/architecture/MODEL_GUARDRAILS_CONTRACT.md`

---

## 13. Evaluation Strategy (Level 5)

- Applicable evaluation families and justified omissions:
- Versioned criteria, datasets, provenance, separation rules, and sensitive-data controls:
- Required slices, negative cases, and boundary cases:
- Oracle and evaluator adapter for each criterion:
- Model-judge rubric, configuration, calibration, and inconclusive behavior (if applicable):
- Per-case, per-slice, and aggregate thresholds declared before execution:
- Missing, stale, invalid, ambiguous, and insufficient-evidence behavior:
- Evaluation evidence path:

Contract: `extensions/llm-application/docs/backend/architecture/LLM_EVALUATION_CONTRACT.md`

---

## 14. LLM NFR Validation (Level 5)

Confirm these NFR categories are populated in nfrs.md (no TBD entries):

- LLM Latency: populated/TBD
- LLM Cost: populated/TBD
- LLM Fallback: populated/TBD
- LLM Safety: populated/TBD

If any LLM NFR is TBD, stop and request completion.

---

## 15. Agent Architecture

### 15a. SOAA applicability (one or more agents)

Applies when the feature uses governed runtime skills, an adaptive agent loop, or their control boundaries, including a single agent with fixed skills. Agent count does not decide this.

If **not applicable**: "Section 15a: Not applicable — no governed runtime skills or adaptive agent loop."

If **applicable**, complete each item:

- [ ] `skill-oriented-agent-architecture` extension installed (`govkit extension list --installed --target .`)
- [ ] Accountable principal, accepted task boundary, one runtime owner, and completion authority declared
- [ ] Components classified; each agent run has a bounded responsibility and authority ceiling
- [ ] Typed runtime state, authoritative writers, legal transitions, ports, and handoffs declared
- [ ] Time, token, cost, tool, retry, loop, and delegation budgets declared
- [ ] External operations have fresh authorization, idempotency, recovery, and evidence
- [ ] Completion requires independent evidence and a trusted controller transition

### 15b. Agent topology (multi-agent features only)

Check `eval_criteria.yaml` for `multi_agent: true`.

If **not declared**: "Section 15b: Not applicable — multi_agent not declared."

If **declared**, complete Section 15a and each item:

- [ ] `agent_topology.md` exists — run the `govkit-multi-agent-design` skill if missing
- [ ] ADR required? (Yes for new multi-agent feature or topology change)

**Section 15 Status:** Approved / Blocked / Not applicable

---

## 16. Final Status

- L4 preflight status: approved | blocked
- L5 GenAI status: approved | blocked
- SOAA status (if applicable): approved | blocked | n/a
- Multi-agent status (if applicable): approved | blocked | n/a
- Combined status: **Approved for planning** | **Experiment required** | **Blocked pending resolution**

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
