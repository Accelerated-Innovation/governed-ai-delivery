# FIRST Scoring Rubric — UI Components

Each FIRST principle is scored 1–5 per component test file or hook test suite. The minimum acceptable average across all five principles is **4.0**. Any individual score below 3 is a blocking failure regardless of average.

This rubric adapts backend FIRST principles for the UI context: component rendering, hook behavior, accessibility, and user interaction testing.

---

## Fast

| Score | Criteria |
|-------|----------|
| 5 | All tests execute in < 10 ms each. No real network calls — MSW intercepts all requests. No real timers — `vi.useFakeTimers()` or equivalent used throughout. |
| 4 | All tests execute in < 50 ms each. MSW used for all API calls. Occasional `waitFor` calls resolve within one tick. |
| 3 | Most tests execute in < 100 ms. One or two tests use `waitFor` with short timeouts. No real network or timer calls. |
| 2 | Some tests take 100–500 ms. Real timer delays or uncontrolled async resolution present. |
| 1 | Tests regularly exceed 500 ms. Real API calls, uncontrolled timers, or heavy DOM operations present. |

**Key question:** Can the full component test suite run on every save during development without noticeable delay?

---

## Isolated

| Score | Criteria |
|-------|----------|
| 5 | Each test renders its own component instance. No shared mutable state. MSW handlers reset between tests. Query cache cleared between tests. Tests can run in any order or in parallel. |
| 4 | Each test renders its own instance. MSW handlers reset in `afterEach`. Minor use of shared immutable fixtures. |
| 3 | Mostly isolated. One or two tests share a wrapper provider that is reset between tests. No order-dependent tests. |
| 2 | Some shared state between tests. Component instances or store state bleeds between tests without full cleanup. |
| 1 | Tests depend on execution order. Global store state or MSW handlers persist across tests. |

**Key question:** Can any single test be run alone and produce the same result?

---

## Repeatable

| Score | Criteria |
|-------|----------|
| 5 | Deterministic in all environments. Time frozen for date rendering. Locale-independent assertions. No flaky assertions on animation frames or async timing. |
| 4 | Deterministic in practice. Controlled clocks and locales. No observed flakiness in CI. |
| 3 | Mostly deterministic. Rare flakiness (< 1 in 100 runs) traced to async timing, with known workaround. |
| 2 | Occasional flakiness (1–5% of runs). Some tests depend on viewport size, system fonts, or animation timing. |
| 1 | Frequently flaky. Tests pass locally but fail in CI. Uncontrolled async, animation, or environment dependencies. |

**Key question:** Does this test produce the same result every time, on every machine?

---

## Self-Verifying

| Score | Criteria |
|-------|----------|
| 5 | All assertions query by accessible role, label, or text — not by CSS class or test ID. Failure messages describe what was expected. Accessibility assertions (axe-core) included per component. |
| 4 | Assertions use accessible queries. Failure messages exist but could be more descriptive. Accessibility assertions present for interactive components. |
| 3 | Most assertions use accessible queries. One or two tests assert on `data-testid` where accessible queries are impractical. Accessibility assertions present but not comprehensive. |
| 2 | Some tests assert on implementation details (CSS classes, internal state). Limited accessibility assertions. |
| 1 | Tests assert on snapshots, CSS selectors, or internal component state. No accessibility assertions. Manual inspection needed to interpret results. |

**Key question:** Does the test assert on what the user sees and interacts with, not on internal implementation?

---

## Timely

| Score | Criteria |
|-------|----------|
| 5 | Component tests written before component implementation. Hook tests written before hook implementation. Test file committed in the same increment as the component. |
| 4 | Tests written alongside implementation in the same increment. All new components and hooks have tests before the increment is committed. |
| 3 | Tests written in the same PR but in a separate increment after the component increment. |
| 2 | Tests added as a follow-up after the component is merged. Coverage gaps exist temporarily. |
| 1 | Tests written significantly after implementation, or not written at all. |

**Key question:** Were tests written close enough to implementation that they influenced component API design?

---

## Applying This Rubric

1. Score each principle 1–5 for the test suite under review
2. Calculate the average across all five principles
3. **Pass:** average >= 4.0 AND no individual score below 3
4. **Fail:** average < 4.0 OR any individual score below 3
5. Record scores in the feature's `plan.md` evaluation_prediction block during planning, and validate against actuals during review

---

See also: [UI Evaluation Standards](eval_criteria.md) | [Virtue Scoring Rubric](VIRTUE_SCORING_RUBRIC.md)
