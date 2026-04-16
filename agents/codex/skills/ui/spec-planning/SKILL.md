---
name: ui-spec-planning
description: Generate a UI feature plan (plan.md) and eval_criteria.yaml from NFRs, acceptance scenarios, and architecture preflight
---

# Spec Planning — UI

You are performing Spec Planning for a UI feature. Determine the feature name from the user's request; if it is not provided, ask before proceeding.

Read the following before proceeding:

- `features/<feature_name>/acceptance.feature`
- `features/<feature_name>/nfrs.md`
- `features/<feature_name>/architecture_preflight.md`
- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/evaluation/eval_criteria.md`
- `governance/ui/templates/plan.md`
- `governance/ui/schemas/eval_criteria.schema.json`

---

Produce or update `features/<feature_name>/plan.md` and `features/<feature_name>/eval_criteria.yaml`.

## plan.md must include:

### 1. Feature Summary
One paragraph describing the feature from the user's perspective.

### 2. MVVM Breakdown
For each layer:
- Components to create (with props interface summary)
- Hooks / query inject functions to create (query keys, data shape, transform)
- Client state additions (Zustand store / Signal store)
- API functions to create (endpoint, method, request/response types)

### 3. Increment Breakdown
Ordered list of implementation increments. Each increment must be independently testable and deployable.

### 4. Backend Contract Dependencies
List any backend endpoints this feature depends on. Flag any that are not yet available.

### 5. Accessibility Plan
For each Gherkin scenario tagged `@accessibility`: describe the WCAG criteria and test approach.

### 6. Evaluation Compliance Summary

```yaml
evaluation_prediction:
  first:
    fast:           { score: 0-5, evidence: "..." }
    isolated:       { score: 0-5, evidence: "..." }
    repeatable:     { score: 0-5, evidence: "..." }
    self_verifying: { score: 0-5, evidence: "..." }
    timely:         { score: 0-5, evidence: "..." }
    average: 0.0
  virtues:
    working:   { score: 0-5, evidence: "..." }
    unique:    { score: 0-5, evidence: "..." }
    simple:    { score: 0-5, evidence: "..." }
    clear:     { score: 0-5, evidence: "..." }
    easy:      { score: 0-5, evidence: "..." }
    developed: { score: 0-5, evidence: "..." }
    brief:     { score: 0-5, evidence: "..." }
    average: 0.0
  accessibility:
    predicted_axe_violations: 0
    wcag_level: AA
  thresholds_met: true|false
```

Scoring rubrics: `docs/ui/evaluation/FIRST_SCORING_RUBRIC.md` and `docs/ui/evaluation/VIRTUE_SCORING_RUBRIC.md`

Do not proceed to Implementation Planning if `thresholds_met` is false, predicted FIRST average is below 4.0, or predicted Virtue average is below 4.0.
