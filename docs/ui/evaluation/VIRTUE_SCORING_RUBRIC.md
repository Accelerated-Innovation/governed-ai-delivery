# 7 Code Virtues Scoring Rubric — UI Components

Each virtue is scored 1–5 per implementation increment. The minimum acceptable average across all seven virtues is **4.0**. Any individual score below 3 is a blocking failure regardless of average.

This rubric adapts the 7 Code Virtues for the UI context: MVVM separation, component composition, accessibility, and state management.

---

## Working

| Score | Criteria |
|-------|----------|
| 5 | All component tests pass. All E2E scenarios pass. Zero critical/serious axe-core violations. All interactive states (loading, error, empty, populated) handled. Keyboard navigation works for all interactive elements. |
| 4 | All tests pass. Zero critical axe violations. Most interactive states handled. Minor accessibility issues (e.g., missing `aria-describedby` on a non-critical element). |
| 3 | All tests pass. One or two minor axe violations (not critical or serious). Some interactive states handled implicitly (e.g., loading state exists but is minimal). |
| 2 | Most tests pass. One critical or serious axe violation. Incomplete state handling (e.g., error state missing). |
| 1 | Tests fail on core rendering. Critical accessibility violations. Missing interactive states cause user-visible errors. |

**Key question:** Does the component work correctly for all users, including those using assistive technology?

---

## Unique

| Score | Criteria |
|-------|----------|
| 5 | Zero duplicated component logic. Shared patterns extracted into hooks or utility components. No copy-paste JSX/template blocks. |
| 4 | No meaningful duplication. Minor structural similarities (e.g., similar layout wrappers) exist but logic is not duplicated. |
| 3 | One instance of duplicated logic (2 occurrences). Extraction into a shared hook or component is feasible but not urgent. |
| 2 | Multiple instances of duplicated logic (3+ occurrences). Clear candidates for shared components or hooks exist. |
| 1 | Pervasive copy-paste. Same rendering logic, event handlers, or data-fetching patterns repeated across components. |

**Key question:** If this UI pattern changes, how many components must be updated?

---

## Simple (Structural Simplicity)

| Score | Criteria |
|-------|----------|
| 5 | Components are views only — no fetch, transform, or business logic. All data transformation in ViewModel hooks. Maximum nesting depth <= 2 in JSX/templates. No conditional rendering chains > 2 branches. |
| 4 | Components are primarily views. ViewModel separation is clean. Occasional inline conditional (ternary) for simple UI branching. Maximum nesting depth <= 3. |
| 3 | Components are mostly views. One or two components contain minor data transformation inline. Nesting depth <= 4. |
| 2 | Some components mix view and logic concerns. Conditional rendering chains > 3 branches. Nested ternaries present. |
| 1 | Components contain business logic, direct API calls, or complex data transformation. Deeply nested JSX/templates. MVVM separation violated. |

**Key question:** Can a developer understand this component's rendering by reading the template/JSX alone?

---

## Clear

| Score | Criteria |
|-------|----------|
| 5 | Component, hook, and prop names are descriptive and domain-aligned. Component files do one thing. Props interface is minimal and well-typed. No explanatory comments needed. |
| 4 | Names are descriptive. Components are focused. Rare comments explain non-obvious accessibility or browser-specific decisions. |
| 3 | Most names are clear. One or two components accept too many props or have ambiguous names. Occasional abbreviations. |
| 2 | Some cryptic names. Components mix concerns. Props interface is unclear without reading the implementation. |
| 1 | Unclear naming. Large multi-purpose components. Props have generic names (e.g., `data`, `options`, `config`) without type clarity. |

**Key question:** Can a new team member understand what this component renders and what props it needs by reading its name and type signature?

---

## Easy (Maintainability)

| Score | Criteria |
|-------|----------|
| 5 | Clean MVVM separation — View (component) depends only on ViewModel (hook). ViewModel depends only on Model (API/domain). No cross-feature imports. Clear extension points (composition over configuration). |
| 4 | Good separation of concerns. Dependencies follow MVVM layering. Minor coupling within a feature vertical. |
| 3 | Mostly well-structured. One or two ViewModel hooks tightly coupled to specific component structure. Extension requires moderate effort. |
| 2 | Components depend directly on API clients or state stores, bypassing ViewModel. Changes in API shape require component changes. |
| 1 | No ViewModel separation. Components directly call APIs, manage global state, and contain business logic. Changes have unpredictable ripple effects. |

**Key question:** Can the API layer or state management approach change without modifying component rendering logic?

---

## Developed (Test Coverage & Hygiene)

| Score | Criteria |
|-------|----------|
| 5 | All components have tests. All hooks have tests. All `@e2e` scenarios have Playwright tests with axe scans. Dead code removed. Consistent file structure. No TODO markers. |
| 4 | All public components and hooks have tests. E2E coverage is complete. Style is consistent. Minor dead code or one TODO with a tracked issue. |
| 3 | Most components have tests. Some internal utility components lack coverage. E2E coverage exists but is incomplete. |
| 2 | Test coverage is partial. Significant components untested. E2E tests exist for happy path only. |
| 1 | Minimal or no component tests. No E2E tests. Dead code and unused imports present. |

**Key question:** Is this UI feature production-ready, or does it still need cleanup?

---

## Brief

| Score | Criteria |
|-------|----------|
| 5 | No redundant wrapper components. No speculative abstractions (e.g., generic component factory for one use). No unnecessary props. Every component serves the current requirement. |
| 4 | Minimal unnecessary code. One or two comments restating obvious rendering logic. |
| 3 | Some unnecessary code — an unused prop, a wrapper component that adds no value, or a premature abstraction. |
| 2 | Multiple unnecessary abstractions. Over-engineered component API with configuration options for hypothetical future use. |
| 1 | Significant bloat. Wrapper components that pass through all props unchanged. Complex configuration objects for simple UI. Code-to-value ratio is poor. |

**Key question:** If I removed this component/hook/prop, would any user-facing behavior change?

---

## Applying This Rubric

1. Score each virtue 1–5 for the implementation increment under review
2. Calculate the average across all seven virtues
3. **Pass:** average >= 4.0 AND no individual score below 3
4. **Fail:** average < 4.0 OR any individual score below 3
5. Record scores in the feature's `plan.md` evaluation_prediction block during planning, and validate against actuals during review

---

## Refactor Triggers

Any of these conditions should trigger an immediate refactor before proceeding to the next increment:

| Trigger | Related Virtue | Threshold |
|---------|---------------|-----------|
| Duplicated rendering logic (3+ occurrences) | Unique | Score drops to 2 |
| Component contains business logic or API calls | Simple | Score drops to 2 |
| Nesting depth > 4 in JSX/templates | Simple | Score drops to 3 |
| Nested ternaries in rendering | Simple | Score drops to 3 |
| Component accepts > 8 props | Clear | Score drops to 3 |
| Cross-feature import | Easy | Score drops to 3 |
| Public component without tests | Developed | Score drops to 3 |
| Wrapper component that passes all props through | Brief | Score drops to 3 |

---

See also: [UI Evaluation Standards](eval_criteria.md) | [FIRST Scoring Rubric](FIRST_SCORING_RUBRIC.md)
