# FIRST Scoring Rubric — Backend

Each FIRST principle is scored 1–5 per test file or test suite. The minimum acceptable average across all five principles is **4.0**. Any individual score below 3 is a blocking failure regardless of average.

---

## Fast

| Score | Criteria |
|-------|----------|
| 5 | All tests execute in < 10 ms each. No I/O, no network, no disk, no sleep. |
| 4 | All tests execute in < 50 ms each. No real network or database calls. Occasional disk I/O for fixtures is acceptable if fast. |
| 3 | Most tests execute in < 200 ms. One or two tests use controlled I/O (e.g., SQLite in-memory). No real external service calls. |
| 2 | Some tests take 200 ms–1 s. Real database or file system access present but not dominant. |
| 1 | Tests regularly exceed 1 s. Real network calls, uncontrolled sleeps, or heavy I/O present. |

**Key question:** Can the full test suite run in CI on every commit without slowing the feedback loop?

---

## Isolated

| Score | Criteria |
|-------|----------|
| 5 | Zero shared mutable state. Every test constructs its own dependencies via injection. Tests can run in any order or in parallel without interference. |
| 4 | No shared mutable state. Dependency injection used consistently. Minor use of module-level constants (immutable) is acceptable. |
| 3 | Mostly isolated. One or two tests share a fixture that is reset in setup/teardown. No order-dependent tests. |
| 2 | Some shared state between tests. Setup/teardown partially manages it but order sensitivity exists. |
| 1 | Tests depend on execution order, global singletons, or shared mutable state that is not reset between tests. |

**Key question:** Can any single test be run alone, in any order, and produce the same result?

---

## Repeatable

| Score | Criteria |
|-------|----------|
| 5 | Deterministic in all environments. Randomness seeded, time frozen, no environment-specific paths, no flaky assertions. |
| 4 | Deterministic in practice. Time-dependent logic uses controlled clocks. No observed flakiness in CI. |
| 3 | Mostly deterministic. Rare flakiness (< 1 in 100 runs) traced to timing or ordering, with known workaround. |
| 2 | Occasional flakiness (1–5% of runs). Some tests depend on system clock, locale, or environment variables. |
| 1 | Frequently flaky. Tests pass locally but fail in CI (or vice versa). Uncontrolled randomness or environment assumptions. |

**Key question:** Does this test produce the same result every time, on every machine, without any manual intervention?

---

## Self-Verifying

| Score | Criteria |
|-------|----------|
| 5 | Every test has explicit, precise assertions on expected outcomes. Failure messages are descriptive. No manual log inspection needed. |
| 4 | All tests have explicit assertions. Failure messages exist but could be more descriptive in edge cases. |
| 3 | Most tests have explicit assertions. One or two tests assert on broad conditions (e.g., "result is not None") rather than specific values. |
| 2 | Some tests lack assertions or rely on "no exception thrown" as the success criterion. |
| 1 | Tests require manual inspection of logs or output to determine pass/fail. Print-based debugging left in tests. |

**Key question:** Does the test unambiguously report pass or fail without human interpretation?

---

## Timely

| Score | Criteria |
|-------|----------|
| 5 | Tests written before implementation (TDD). Test file committed in the same increment as the code it covers. |
| 4 | Tests written alongside implementation in the same increment. All new code has corresponding tests before the increment is committed. |
| 3 | Tests written in the same PR/feature branch but in a separate increment after the implementation increment. |
| 2 | Tests added as a follow-up after the feature is merged. Coverage gaps exist temporarily. |
| 1 | Tests written significantly after implementation, or not written at all. Retroactive test-writing with no coverage tracking. |

**Key question:** Were tests written close enough to implementation that they influenced the design?

---

## Applying This Rubric

1. Score each principle 1–5 for the test suite under review
2. Calculate the average across all five principles
3. **Pass:** average >= 4.0 AND no individual score below 3
4. **Fail:** average < 4.0 OR any individual score below 3
5. Record scores in the feature's `plan.md` evaluation_prediction block during planning, and validate against actuals during review

---

See also: [Evaluation Standards](eval_criteria.md) | [Virtue Scoring Rubric](VIRTUE_SCORING_RUBRIC.md)
