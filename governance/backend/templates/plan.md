# Feature Plan: <feature_name>

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

Artifacts produced by this feature that other features, services, or agents will consume.

- Shared artifacts produced: none | <list>
- Artifact type(s):
- Downstream consumers:
- Versioning strategy:
- Breaking change policy:
- ADR reference (if required):

### Security and compliance

- AuthN/AuthZ considerations:
- Data classification and PII handling:
- Threats and mitigations:

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
  thresholds_met: null   # true | false — set to false triggers plan revision
```

### Refactor Triggers Identified

- Structural complexity risks:
- Duplication risks:
- Boundary risks:
- Test fragility risks:

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
- NFRs satisfied (`nfrs.md`)
- Evaluation criteria satisfied (`eval_criteria.yaml`)
- FIRST principles satisfied
- 7 Virtue thresholds satisfied
- CI passes (tests, quality, eval gates)
- No boundary violations
- ADRs updated/added (if required)
- PR includes links to plan/spec artifacts