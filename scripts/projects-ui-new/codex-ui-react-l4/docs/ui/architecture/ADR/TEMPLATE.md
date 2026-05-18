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

- The feature or UI area impacted
- Relevant architectural constraints
- Existing MVVM rules or contracts that apply
- The problem this decision addresses

Reference:
- `features/<feature_name>/plan.md`
- `docs/ui/architecture/MVVM_CONTRACT.md`
- Framework-specific conventions (`docs/ui/architecture/react/` or `docs/ui/architecture/angular/`)

---

## 2. Decision

State the decision clearly and concisely.

Avoid narrative here. This section must stand alone.

Example:

> We will promote the `DateRangePicker` component from `features/reporting/components/` to `src/shared/components/` to support reuse across the reporting and dashboard features.

---

## 3. MVVM Impact

### 3.1 Layer Boundaries
- Layers affected (View / ViewModel / Model):
- Dependency direction changes:
- New shared modules introduced:

Confirm:
- No forbidden cross-layer imports are introduced
- No component directly calls API functions
- No store directly calls API services

### 3.2 State Management Impact
If applicable:
- Does this introduce cross-feature state? (requires justification)
- Does this change the server state / client state boundary?
- React Query or TanStack Query cache implications:

### 3.3 Backend Contract Impact
If applicable:
- New endpoints required:
- Existing contract changes:
- Contract negotiation needed before implementation:

---

## 4. Alternatives Considered

### Option A
- Description
- Pros
- Cons
- Why rejected

### Option B
- Description
- Pros
- Cons
- Why rejected

---

## 5. Accessibility Impact

Does this decision affect:
- WCAG 2.1 AA compliance?
- Focus management or keyboard navigation?
- Screen reader behaviour?

If yes: describe the impact and how compliance is maintained.
If no: state "No accessibility impact."

---

## 6. Evaluation Impact

Does this decision affect:
- Component test coverage or FIRST compliance?
- Accessibility evaluation thresholds?
- E2E Playwright coverage?

If yes:
- List affected criteria from `features/<feature_name>/eval_criteria.yaml`
- Describe changes required

If no: state "No evaluation impact."

---

## 7. Risks and Tradeoffs

- Technical risks:
- Performance implications:
- Bundle size implications:
- Operational risks:

Mitigations:

---

## 8. Plan Alignment

Reference:
- Feature plan increments impacted:
- New increment required?
- Scope adjustments required?

If the decision changes scope: `plan.md` must be updated.

---

## 9. Consequences

### Positive
-

### Negative
-

### Neutral
-

---

## 10. Follow-Up Actions

- Code changes required:
- Documentation updates required:
- CI updates required:
- Accessibility review required:

---

## 11. Approval

Approved by:
- Architect:
- Product (if scope impact):
