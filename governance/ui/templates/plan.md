# Plan — [Feature Name]

**Feature:** [feature name]
**Date:** [YYYY-MM-DD]
**Status:** Draft | Approved

---

## 1. Feature Summary

[One paragraph describing the feature from the user's perspective.]

---

## 2. MVVM Breakdown

### Components (View)

| Component | Location | Props Summary |
|---|---|---|
| `ComponentName` | `features/<feature>/components/` | [key props] |

### Hooks (ViewModel — Server State)

| Hook | Query Key | Data Shape | Transform |
|---|---|---|---|
| `useFeatureName` | `['feature', id]` | [API response shape] | [ViewModel shape] |

### Store (ViewModel — Client State)

[State fields and actions, or "None required."]

### API Functions (Model)

| Function | Endpoint | Method | Request | Response |
|---|---|---|---|---|
| `fetchFeature` | `/api/feature/{id}` | GET | — | `FeatureResponse` |

---

## 3. Increment Breakdown

Each increment must be independently testable.

**Increment 1:** [description]
- [ ] Task
- [ ] Task

**Increment 2:** [description]
- [ ] Task
- [ ] Task

---

## 4. Backend Contract Dependencies

| Endpoint | Status | Blocker |
|---|---|---|
| `GET /api/...` | Available / Pending | Yes / No |

---

## 5. Accessibility Plan

[For each `@accessibility`-tagged Gherkin scenario: WCAG criteria and test approach.]

---

## 6. Evaluation Compliance Summary

```yaml
evaluation_prediction:
  component_tests:
    FIRST_scores:
      fast: { score: 0, rationale: "" }
      isolated: { score: 0, rationale: "" }
      repeatable: { score: 0, rationale: "" }
      self_verifying: { score: 0, rationale: "" }
      timely: { score: 0, rationale: "" }
    predicted_average: 0.0
  accessibility:
    predicted_axe_violations: 0
    wcag_level: AA
  thresholds_met: false
```
