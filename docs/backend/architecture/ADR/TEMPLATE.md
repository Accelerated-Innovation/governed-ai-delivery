# ADR-XXX: <Short Decision Title>

## Status
Proposed | Accepted | Rejected | Superseded

Write `Proposed`. `Accepted` is a **derived** state, not a word an author types
— see the Approval section at the end of this template for what makes it true.

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

`Accepted` in the Status section is a **derived** state. It is true because an
approver named in `governance/approval_policy.yaml` submitted an approving
review of the commit carrying this decision — nothing written in this section
makes it true, and the `adr-approval-check` CI gate fails a pull request whose
ADR claims `Accepted` without that review.

So this section records **which decision authority this ADR needs**, not who
gave it. Leave no name, date, or signature here as though the decision were
already made: a reviewer assesses evidence or content, an approver commits the
decision, and the approval itself lives where it cannot be typed.

Decision authority required:

- Architect:
- Security (if applicable):
- Product (if scope impact):
