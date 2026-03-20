# Feature Plan: <feature_name>

<!-- INSTRUCTIONS
     Complete this plan before implementation begins.
     The Evaluation Compliance Summary is mandatory — all score and evidence
     fields must be populated (no null values) before proceeding to code.
     Template source: governance/ui/templates/plan.md
-->

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
- `docs/ui/architecture/MVVM_CONTRACT.md`:
- `docs/ui/architecture/react/COMPONENT_CONVENTIONS.md` or `docs/ui/architecture/angular/COMPONENT_CONVENTIONS.md`:
- `docs/ui/evaluation/eval_criteria.md`:

### ADRs

- New ADRs required:
  - ADR-XXX: <title>
- Existing ADRs referenced:
  - ADR-XXX: <title>

---

## MVVM Breakdown

### Components (View)

| Component | Location | Props Summary |
|---|---|---|
| `ComponentName` | `src/features/<feature>/components/` | |

### Query Layer (ViewModel — Server State)

| Hook / Inject fn | Query Key | API Endpoint | ViewModel Shape |
|---|---|---|---|
| `useFeatureName` / `injectFeatureName` | `['feature', id]` | `GET /api/...` | |

### Store (ViewModel — Client State)

<!-- Describe signal store or Zustand store fields and actions, or state "None required." -->

### API Functions (Model)

| Function | Endpoint | Method | Request | Response |
|---|---|---|---|---|
| `fetchFeature` | `/api/feature/{id}` | GET | — | `FeatureResponse` |

---

## Backend Contract Dependencies

| Endpoint | Status | Blocker |
|---|---|---|
| `GET /api/...` | Available / Pending | Yes / No |

---

## Increments

### Increment 1: <name>

Implementation must follow MVVM layer order: API → ViewModel → View.

**Goal**
-

**Deliverables**
- [ ] API functions + types
- [ ] Query hooks / inject functions
- [ ] Store (if needed)
- [ ] Components
- [ ] Component tests (FIRST compliant + jest-axe)
- [ ] Playwright E2E tests

**Accessibility impact**
-

**Definition of Done**
-

---

### Increment 2: <name>

(repeat structure)

---

## Accessibility Plan

For each `@accessibility`-tagged Gherkin scenario:

| Scenario | WCAG Criteria | Test Approach |
|---|---|---|
| Keyboard navigation | 2.1.1 Keyboard | Playwright tab/enter flow + axe |
| No violations | 4.1.2 Name, Role, Value | jest-axe in component test + Playwright axe scan |

---

## Evaluation Compliance Summary (MANDATORY)

Predicted BEFORE implementation begins. All score and evidence fields must be populated.

```yaml
evaluation_prediction:
  component_tests:
    FIRST_scores:
      fast:           { score: null, rationale: "" }
      isolated:       { score: null, rationale: "" }
      repeatable:     { score: null, rationale: "" }
      self_verifying: { score: null, rationale: "" }
      timely:         { score: null, rationale: "" }
    predicted_average: null
  accessibility:
    predicted_axe_violations: null
    wcag_level: AA
  thresholds_met: null   # true | false — false requires plan revision
```

If `thresholds_met` is false or predicted FIRST average is below 4.0, revise this plan before implementation begins.

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
- FIRST average ≥ 4.0
- Zero critical axe-core violations
- All `@e2e` scenarios have passing Playwright tests
- CI gates pass (type check, ESLint, component tests, Playwright, eval prediction check)
- ADRs updated/added (if required)
