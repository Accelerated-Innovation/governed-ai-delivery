---
name: unit-testing-rubric
description: Standards for writing, reviewing, and evaluating unit tests. Use whenever writing new tests, reviewing existing tests, deciding what to test, assigning a test to a fast vs. full feedback loop, or diagnosing flaky, slow, or low-value tests. Covers structural fidelity, the FIRST properties, behavioral invariants, and coverage-as-diagnostic.
---

# Unit Testing Rubric

## Purpose

Create a trustworthy, deterministic, affordable test suite that protects
behavioral invariants, supports refactoring, and provides rapid feedback.

Flaky tests are defects in the feedback system and must be fixed, replaced, or
removed.

## Testing Integrity

**1. Fidelity Rule** — Tests must be structurally honest. The production
behavior under test must execute the same way in the test harness as in
production. Introduce seams around dependencies, not around behavior.
*Would production execute the same behavior if this test did not exist?*

**2. Documentation Rule** — A microtest is executable documentation. A developer
should understand the behavior, context, action, expected result, and important
edge cases without reading the implementation.
*Can a developer understand the behavior from the test alone?*

**3. Single Action Rule** — An Arrange–Act–Assert test performs exactly one
action in one context. Multiple assertions are acceptable when they examine
evidence from the same action.
*What is the single action being performed?*

## FIRST Properties

**4. Fast Rule** — Tests should support rapid feedback. The fast suite (however
the project invokes it) should complete in well under a minute; treat ~30
seconds as a reasonable default budget absent a project-specific one.
*Is this test worth spending part of the fast-feedback budget?*

**5. Isolation Rule** — Tests must not depend on execution order, shared mutable
state, hidden fixtures, or environmental assumptions.
*Can this test pass independently on any machine?*

**6. Repeatability Rule** — Accepted tests must be deterministic. Control time,
randomness, IDs, concurrency, and external dependencies.
*Will this test produce the same result every time?*

**7. Self-Verifying Rule** — Tests produce an automatic, unambiguous pass/fail
result.
*Does the test clearly determine success or failure without human
interpretation?*

**8. Timely Rule** — Tests are written alongside behavior, protect regressions,
and evolve with the product.
*Is this test protecting currently desired behavior?*

## Behavioral Quality

**9. Behavioral Invariant Rule** — Every permanent test specifies a behavior
that should remain true until the product no longer wants it. Tests exist to
lock down behavioral invariants.
*What invariant does this test protect?*

**10. Potency Rule** — A test must fail for a plausible violation of the
invariant it specifies. A test that cannot detect a realistic defect provides
little value.
*What bug would make this test fail?*

**11. Failure Clarity Rule** — When a test fails, it should clearly illuminate
the violated invariant and help localize the problem. Failures should be
specific, local, and diagnostic.
*If this test fails, will a developer know what invariant was violated?*

## Portfolio Quality

**12. Affordability Rule** — Confidence should be obtained at the cheapest
reliable test level. Prefer narrow deterministic tests over expensive broad
tests.
*Is there a cheaper deterministic test that provides the same confidence?*

**13. Feedback Loop Rule** — Assign each test to the earliest useful feedback
loop: a fast loop (e.g. `run_tests`) for deterministic feedback on every change,
and a full/slow loop (e.g. `full_test`) for additional deterministic confidence
that doesn't belong in the fast one (end-to-end, slow, or integration-heavy
cases) — name the two loops whatever the project calls them. Most confidence
should live in the fast loop.
*Why doesn't this confidence belong in the earlier feedback loop?*

**14. Coverage Diagnostic Rule** — Coverage is a diagnostic signal, not the
goal. Use it to discover unprotected decisions, transformations, and invariants.
Do not create tests merely to increase coverage percentages.
*What behavioral invariant is missing behind this uncovered code?*

## Lifecycle

**15. Prophet / Guide / Guard Rule** — Every permanent test serves three
purposes: **Prophet** (specifies a future invariant before implementation),
**Guide** (provides the target behavior during implementation), **Guard**
(protects behavior during maintenance and refactoring).
*Does this test successfully act as Prophet, Guide, and Guard?*

## Operational Expectations

- All accepted tests are deterministic.
- No retries, quarantines, reruns-until-pass, or tolerated failures.
- Prefer behavior assertions over implementation assertions.
- JSON object field order is not asserted unless contractually significant.
- Most confidence should come from the fast loop.
- Every test should justify its value against its cost.
- Refactor tests to reduce fragility, redundancy, and cost while preserving
  invariants.
- Delete tests only when the behavior is no longer desired, or when the test is
  redundant, flaky, or provides no unique confidence.

## Common Pitfalls

**Ambiguous fixture selection.** When a test needs to pick one item out of
several candidates that share a common identifying field (e.g. two functions,
signatures, or records with the same name/owner but a different shape),
filtering on that one shared field alone can silently bind to the wrong
candidate — the test then validates the wrong thing while still appearing to
pass. Filter on every field that actually distinguishes the candidates, not
just the most obvious one.

**Widening behavior without breaking coverage.** When an existing function's
behavior is being deliberately widened (recognizing more inputs, covering more
cases) without changing its signature, audit every existing test that asserts
on it *before* changing the implementation, to confirm none assumes the
narrower behavior. A widening change is verifiably non-breaking when no
existing assertion could contradict the new, broader behavior — don't rely on
a regression to reveal a conflict you could have checked for directly.
