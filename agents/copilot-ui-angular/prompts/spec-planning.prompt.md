---
description: "Generate or update plan.md and eval_criteria.yaml for an Angular UI feature"
agent: "ask"
---

# Spec Planning — Angular UI

You are producing the Spec Plan for an Angular UI feature.

Before proceeding, read:
- `features/<feature_name>/acceptance.feature`
- `features/<feature_name>/nfrs.md`
- `features/<feature_name>/architecture_preflight.md`
- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/architecture/angular/STATE_MANAGEMENT.md`
- `docs/ui/evaluation/eval_criteria.md`
- `governance/ui/templates/plan.md`
- `governance/ui/schemas/eval_criteria.schema.json`

Produce or update `features/<feature_name>/plan.md` and `features/<feature_name>/eval_criteria.yaml`.

## plan.md must include:

### 1. Feature Summary
One paragraph from the user's perspective.

### 2. MVVM Breakdown
Components (standalone, OnPush, inputs/outputs), query inject functions (query keys, transforms), signal store additions, API functions (endpoint, types).

### 3. Increment Breakdown
Ordered increments: API → ViewModel → View. Each independently testable.

### 4. Backend Contract Dependencies
All backend endpoints. Flag any not yet available.

### 5. Accessibility Plan
For each `@accessibility`-tagged scenario: WCAG criteria and test approach.

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
