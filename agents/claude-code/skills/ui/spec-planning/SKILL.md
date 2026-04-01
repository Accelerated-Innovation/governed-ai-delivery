# Spec Planning — React UI

You are performing Spec Planning for a React UI feature. Read the following before proceeding:

- `features/$ARGUMENTS/acceptance.feature`
- `features/$ARGUMENTS/nfrs.md`
- `features/$ARGUMENTS/architecture_preflight.md`
- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/evaluation/eval_criteria.md`
- `governance/ui/templates/plan.md`
- `governance/ui/schemas/eval_criteria.schema.json`

---

Produce or update `features/$ARGUMENTS/plan.md` and `features/$ARGUMENTS/eval_criteria.yaml`.

## plan.md must include:

### 1. Feature Summary
One paragraph describing the feature from the user's perspective.

### 2. MVVM Breakdown
For each layer:
- Components to create (with props interface summary)
- Hooks to create (query keys, data shape, transform)
- Zustand store additions (if any)
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
