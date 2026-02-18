# ADR-XXX: <Short Decision Title>

## Status
Proposed | Accepted | Rejected | Superseded

## Date
YYYY-MM-DD

## Authors
- <Name / Role>

---

## 1. Context

Describe:

- The feature or system area impacted
- Relevant architectural constraints
- Existing standards or contracts that apply
- The problem this decision addresses

Reference:
- `features/<feature_name>/plan.md`
- Relevant sections of `ARCH_CONTRACT.md`
- Relevant boundary rules in `BOUNDARIES.md`

---

## 2. Decision

State the decision clearly and concisely.

Avoid narrative here. This section must stand alone.

Example:

> We will introduce a domain service layer between the API and persistence layer to enforce boundary separation and isolate business logic.

---

## 3. Architectural Impact

### 3.1 Boundaries
- Layers/services affected:
- Dependency direction changes:
- New modules introduced:

Confirm:
- No forbidden cross-layer access is introduced
- Dependency direction complies with `BOUNDARIES.md`

### 3.2 API Impact
If applicable:
- Route changes:
- Versioning impact:
- Error model impact:
- OpenAPI updates required:

### 3.3 Security Impact
- Auth pattern used:
- Authorization changes:
- Token handling implications:
- Data classification considerations:
- Logging/redaction implications:

---

## 4. Alternatives Considered

For each alternative:

### Option A
- Description
- Pros
- Cons
- Why rejected

Keep this section concise but explicit.

---

## 5. Evaluation Impact

Does this decision affect:

- LLM evaluation criteria?
- Deterministic evaluation checks?
- CI enforcement rules?

If yes:
- List affected criteria from `features/<feature_name>/eval_criteria.yaml`
- Describe changes required

If no:
- State: “No evaluation impact.”

---

## 6. Risks and Tradeoffs

- Technical risks:
- Operational risks:
- Security risks:
- Performance implications:

Mitigations:

---

## 7. Plan Alignment

Reference:

- Feature plan increments impacted:
- New increment required?
- Scope adjustments required?

If the decision changes scope:
- `plan.md` must be updated.

---

## 8. Consequences

### Positive
- 

### Negative
- 

### Neutral
- 

---

## 9. Follow-Up Actions

- Code changes required:
- Documentation updates required:
- CI updates required:
- Security review required:

---

## 10. Approval

Approved by:
- Architect:
- Security (if applicable):
- Product (if scope impact):
