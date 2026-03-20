# UI Evaluation Standards

This document defines the quality and evaluation contract for all React UI features governed by this kit.

---

## 1. Component Testing — FIRST Principles

All component and hook tests must satisfy FIRST:

### Fast
- No real network calls — use MSW to mock at the service worker boundary
- No real timers — use `vi.useFakeTimers()`
- Tests must run in under 100ms each

### Isolated
- No shared mutable state between tests
- Each test renders its own component instance
- MSW handlers reset between tests

### Repeatable
- No environment-specific assumptions
- No reliance on system clock — freeze time for date-dependent rendering
- Deterministic across CI and local environments

### Self-Verifying
- Explicit assertions on rendered output, not implementation details
- Query by accessible role, label, or text — not by CSS class or test ID unless unavoidable
- Clear pass/fail — no manual inspection of output

### Timely
- Component tests written before or alongside component implementation
- Hook tests written before hook implementation

---

## 2. Accessibility

Standard: WCAG 2.1 Level AA

- Zero critical or serious axe-core violations permitted in any component test
- Zero axe violations permitted in any Playwright E2E flow
- Every interactive component must pass keyboard navigation test
- Every form must pass label association test

---

## 3. E2E Coverage

Every Gherkin scenario tagged `@e2e` must have a corresponding Playwright test. Each Playwright test must:
- Complete the scenario from a user's perspective (no internal wiring)
- Run an axe accessibility scan on the page
- Assert on visible output — not on network requests

---

## 4. Scoring Model

### Component Tests
- FIRST score: 0–5 per principle
- Minimum average: 4.0
- Blocking: yes — implementation must not merge below threshold

### Accessibility
- Critical violations: 0 permitted
- Serious violations: 0 permitted
- Blocking: yes

### E2E
- All `@e2e` scenarios must have passing Playwright tests
- Blocking: yes

---

## 5. Feature-Level Eval YAML Schema

Each feature must include `features/<feature>/eval_criteria.yaml` conforming to `governance/ui/schemas/eval_criteria.schema.json`.

**mode: ui** (standard for all UI features):

```yaml
version: 1
feature: <feature_name>
mode: ui
owner: <team-or-role>

component_tests:
  enforce_FIRST: true
  minimum_FIRST_average: 4

accessibility:
  standard: WCAG_2_1_AA
  max_critical_violations: 0
  max_serious_violations: 0

e2e:
  enforce_gherkin_coverage: true
  run_axe_on_each_flow: true
```

**mode: none** (only when evaluation is explicitly not applicable):

```yaml
version: 1
feature: <feature_name>
mode: none
rationale: "This feature contains no rendered UI components."
```
