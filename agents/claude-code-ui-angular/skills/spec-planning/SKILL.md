# Spec Planning — Angular UI

You are performing Spec Planning for an Angular UI feature. Read the following before proceeding:

- `features/$ARGUMENTS/acceptance.feature`
- `features/$ARGUMENTS/nfrs.md`
- `features/$ARGUMENTS/architecture_preflight.md`
- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/architecture/angular/STATE_MANAGEMENT.md`
- `docs/ui/evaluation/eval_criteria.md`
- `governance/ui/templates/plan.md`
- `governance/ui/schemas/eval_criteria.schema.json`

---

Produce or update `features/$ARGUMENTS/plan.md` and `features/$ARGUMENTS/eval_criteria.yaml`.

## plan.md must include:

### 1. Feature Summary
One paragraph describing the feature from the user's perspective.

### 2. MVVM Breakdown
- Components (standalone, OnPush — with inputs/outputs summary)
- Query inject functions (query keys, data shape, select transform)
- Signal store additions (if any)
- API functions (endpoint, method, request/response types)

### 3. Increment Breakdown
Ordered increments following: API → ViewModel → View. Each increment independently testable.

### 4. Backend Contract Dependencies
List all backend endpoints. Flag any not yet available.

### 5. Accessibility Plan
For each `@accessibility`-tagged Gherkin scenario: WCAG criteria and test approach.

### 6. Evaluation Compliance Summary

```yaml
evaluation_prediction:
  component_tests:
    FIRST_scores:
      fast: { score: 0-5, rationale: "..." }
      isolated: { score: 0-5, rationale: "..." }
      repeatable: { score: 0-5, rationale: "..." }
      self_verifying: { score: 0-5, rationale: "..." }
      timely: { score: 0-5, rationale: "..." }
    predicted_average: 0.0
  accessibility:
    predicted_axe_violations: 0
    wcag_level: AA
  thresholds_met: true|false
```

Do not proceed to Implementation Planning if `thresholds_met` is false or predicted FIRST average is below 4.0.
