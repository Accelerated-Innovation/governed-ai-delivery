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
- docs/architecture/ARCH_CONTRACT.md:
- docs/architecture/BOUNDARIES.md:
- docs/architecture/API_CONVENTIONS.md:
- docs/architecture/SECURITY_AUTH_PATTERNS.md:
- docs/evaluation/eval_criteria.md:

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

### Security and compliance

- AuthN/AuthZ considerations:
- Data classification and PII handling:
- Threats and mitigations:

---

## Evaluation Compliance Summary (MANDATORY)

Predicted BEFORE implementation begins.

### FIRST (0-5 per principle)

- Fast:
- Isolated:
- Repeatable:
- Self-verifying:
- Timely:

Predicted FIRST average:

### 7 Code Virtues (0-5 per virtue)

- Working:
- Unique:
- Simple:
- Clear:
- Easy:
- Developed:
- Brief:

Predicted Virtue average:

### Refactor Triggers Identified

- Structural complexity risks:
- Duplication risks:
- Boundary risks:
- Test fragility risks:

If predicted averages are below thresholds, this plan must be revised.

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