# Feature Plan: <feature_name>

<!-- INSTRUCTIONS
     Level 5 — GenAI Operations
     Complete this plan before implementation begins.
     The Evaluation Compliance Summary is mandatory — all score and evidence
     fields must be populated (no null values) before proceeding to code.
     The LLM evaluation section is required for mode: llm features.
     Template source: governance/backend/templates/l5-plan.md
-->

---

## Objective

- What outcome will exist when this feature is done?
- Who benefits and how?
- What measurable success criteria apply?

---

## Scope Boundaries

### In scope
-

### Out of scope
-

### Assumptions
-

---

## Architecture Alignment

### Relevant contracts
- docs/backend/architecture/ARCH_CONTRACT.md:
- docs/backend/architecture/BOUNDARIES.md:
- docs/backend/architecture/API_CONVENTIONS.md:
- docs/backend/architecture/SECURITY_AUTH_PATTERNS.md:
- docs/backend/architecture/LLM_GATEWAY_CONTRACT.md:
- docs/backend/architecture/GUARDRAILS_CONTRACT.md:
- docs/backend/architecture/EVALUATION_LLM_CONTRACT.md:
- docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md:
- docs/backend/evaluation/eval_criteria.md:

### ADRs

- New ADRs required:
  - ADR-XXX: <title>
- Existing ADRs referenced:
  - ADR-XXX: <title>

### Interfaces and dependencies

- Inbound ports:
- Domain services:
- Outbound ports:
- Adapters:
- Data stores/events touched:
- External dependencies:

### Shared contract artifacts

- Shared artifacts produced: none | <list>
- Artifact type(s):
- Downstream consumers:

### Security and compliance

- AuthN/AuthZ considerations:
- Data classification and PII handling:
- Threats and mitigations:

---

## LLM Gateway Configuration

- LiteLLM model alias:
- Fallback chain:
- Cost budget (per-request / monthly):
- Retry policy:

---

## Guardrails Configuration

- Guardrail mode: nemo | guardrails-ai | both | none
- NeMo rail definitions: <path or n/a>
- Guardrails AI validators: <list or n/a>
- Justification (if mode is none):

---

## Evaluation Compliance Summary (MANDATORY)

Predicted BEFORE implementation begins. All score and evidence fields must be populated — null values are not permitted at plan finalization.

```yaml
evaluation_prediction:
  first:
    fast:           { score: null, evidence: "" }
    isolated:       { score: null, evidence: "" }
    repeatable:     { score: null, evidence: "" }
    self_verifying: { score: null, evidence: "" }
    timely:         { score: null, evidence: "" }
    average: null
  virtues:
    working:   { score: null, evidence: "" }
    unique:    { score: null, evidence: "" }
    simple:    { score: null, evidence: "" }
    clear:     { score: null, evidence: "" }
    easy:      { score: null, evidence: "" }
    developed: { score: null, evidence: "" }
    brief:     { score: null, evidence: "" }
    average: null
  llm_evaluation:
    deepeval_metrics:
      - { metric: "faithfulness", predicted_score: null, threshold: 0.8 }
      - { metric: "answer_relevancy", predicted_score: null, threshold: 0.85 }
    promptfoo_required: null     # true | false
    guardrail_mode: null         # nemo | guardrails-ai | both | none
    ragas_required: null         # true | false
  thresholds_met: null   # true | false — set to false triggers plan revision
```

### Refactor Triggers Identified

- Structural complexity risks:
- Duplication risks:
- Boundary risks:
- Test fragility risks:
- LLM quality regression risks:

If `thresholds_met` is false or any average is below 4.0, this plan must be revised before implementation begins.

---

## Increments

### Increment 1: <name>

**Goal**
-

**Deliverables**
-

**Implementation notes**
-

**Architecture impact**
- Ports affected:
- Adapters affected:
- Boundary risks:

**Tests**
- Unit (FIRST compliant):
- Integration:
- Contract:

**LLM impact**
- Gateway changes:
- Guardrail changes:
- Evaluation changes:

**Evaluation impact**
- LLM eval required? (yes/no)
- Criteria names impacted:
- Threshold impact:
- Eval dataset reference:

**Definition of Done**
-

---

### Increment 2: <name>

(repeat structure)

---

## Risks

- Risk:
  - Impact:
  - Mitigation:

---

## Definition of Done (Feature-Level)

- Acceptance criteria satisfied (`acceptance.feature`)
- NFRs satisfied (`nfrs.md`) — including LLM latency, cost, fallback, safety
- Evaluation criteria satisfied (`eval_criteria.yaml`)
- FIRST principles satisfied
- 7 Virtue thresholds satisfied
- DeepEval metrics pass thresholds
- Promptfoo adversarial suite passes (if required)
- RAGAS metrics pass thresholds (if required)
- Guardrails tested and functional (if applicable)
- CI passes (tests, quality, eval gates, deepeval-gate, promptfoo-gate)
- No boundary violations
- ADRs updated/added (if required)
- PR includes links to plan/spec artifacts
