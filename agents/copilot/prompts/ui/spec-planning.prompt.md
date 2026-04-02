---
description: "Generate or update plan.md and eval_criteria.yaml for a React UI feature"
agent: "ask"
---

# Spec Planning — React UI

You are producing the Spec Plan for a React UI feature.

Before proceeding, read:
- `features/<feature_name>/acceptance.feature`
- `features/<feature_name>/nfrs.md`
- `features/<feature_name>/architecture_preflight.md`
- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/evaluation/eval_criteria.md`
- `governance/ui/templates/plan.md`
- `governance/ui/schemas/eval_criteria.schema.json`

Produce or update `features/<feature_name>/plan.md` and `features/<feature_name>/eval_criteria.yaml`.

## plan.md must include:

### 1. Feature Summary
One paragraph describing the feature from the user's perspective.

### 2. MVVM Breakdown
For each layer — components (with props summary), hooks (query keys, data shape, transforms), Zustand store additions, and API functions (endpoint, method, request/response types).

### 3. Increment Breakdown
Ordered list of independently testable increments. Sequence must follow: API → ViewModel → View.

### 4. Backend Contract Dependencies
List all backend endpoints this feature depends on. Flag any that are not yet available.

### 5. Accessibility Plan
For each `@accessibility`-tagged Gherkin scenario: describe the WCAG criteria and test approach.

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
