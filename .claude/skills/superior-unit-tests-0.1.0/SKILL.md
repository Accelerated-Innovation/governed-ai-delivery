---
name: superior-unit-tests
description: Write or improve unit tests following a strict determinism, F.I.R.S.T., and fast-feedback-budget discipline. Use when asked to write tests, improve tests, review test quality, classify tests, or assess a test suite against a 30-second fast-feedback budget. Invokes a structured output protocol that identifies behaviors under protection, classifies each test by level and feedback loop, and flags nondeterminism risks.
---

# Superior Unit Tests

## Goal

Produce a small, fast, deterministic, valuable test suite that gives high confidence at low cost. Do not maximize test count.

## Non-Negotiable Test Policy

All accepted tests must be deterministic.

Do not write, preserve, recommend, quarantine, retry, rerun, tolerate, or normalize flaky tests. A flaky test teaches developers to ignore failures, and that is unacceptable.

If an existing test is nondeterministic, there are only three acceptable outcomes:

1. Fix it so it is deterministic.
2. Delete it.
3. Replace it with a different deterministic test that provides the desired confidence.

A smaller trustworthy suite is better than a larger suite with failures people learn to ignore.

## Test Execution Policy

This project uses two test-running scripts:

- `./run_tests`: Runs the fast tests. Use this for feedback after small changes, tweaks, refactorings, and incremental feature development.
- `./full_test`: First runs `./run_tests`, then runs all additional tests. Use this periodically, before integration, and especially after a fresh `git pull`.

Because `./full_test` starts by running `./run_tests`, do not classify any test as "both." A test belongs either in the fast feedback loop or in the additional full-suite layer.

## Fast Feedback Budget

The entire `./run_tests` suite must complete within 30 seconds.

This is a hard usability constraint. If the fast suite takes longer than 30 seconds, developers will often choose speed of development over safety and stop running it routinely.

When proposing or writing tests:

- Prefer tests that can belong in `./run_tests`.
- Protect the 30-second total budget for the whole script, not just the individual test.
- Treat additions to `./run_tests` as spending from a limited feedback budget.
- Do not add broad, slow, highly integrated, or expensive tests to `./run_tests` unless their value justifies their cost and the total suite still remains under 30 seconds.
- If an important confidence signal cannot fit inside the 30-second budget, look first for a cheaper deterministic test design.
- If it still cannot fit, classify it as `full_test_only` and explain why.

## Feedback Loop Classification

For every proposed test, classify it as one of:

- `run_tests`
- `full_test_only`

Use `run_tests` for tests that should run constantly during development. These must be fast, deterministic, independent, cheap, and valuable enough to justify spending part of the 30-second fast-feedback budget.

Use `full_test_only` for deterministic tests that are still valuable but too broad, slow, integrated, or costly for the tight development loop.

When a test belongs only in `full_test_only`, explain:

- What extra confidence it provides beyond the fast suite.
- Why that confidence cannot be achieved by a cheaper deterministic test in `run_tests`.
- What design, isolation, or dependency changes would allow the confidence to move into `run_tests`.

## Principles

### 1. Tests must be F.I.R.S.T.

- Fast: run quickly enough to support frequent local execution.
- Independent: no test depends on another test or shared mutable state.
- Repeatable: same result every run, every machine, every time.
- Self-validating: pass/fail is automatic and unambiguous.
- Timely: tests are written close to the behavior they protect.

### 2. Prevent nondeterminism by construction

Do not use real clocks, sleeps, uncontrolled randomness, live networks, real external services, shared databases, filesystem assumptions, test-order dependencies, global mutable state, or timing guesses unless explicitly required and safely isolated.

### 3. Prefer deterministic design

When code depends on time, randomness, IDs, environment variables, concurrency, external services, or IO, inject those dependencies so tests can control them.

### 4. Test behavior, not implementation trivia

Verify observable outcomes, state changes, return values, emitted domain events, or interactions at meaningful boundaries. Avoid tests that merely duplicate implementation details.

### 5. Use the cheapest reliable test level

Prefer microtests/unit tests for pure logic and domain rules. Use contract or component tests for boundaries. Do not create broad end-to-end tests when a narrower deterministic test would provide the same confidence.

### 6. Cover meaningful cases

Include:

- the normal happy path,
- important edge cases,
- invalid inputs,
- boundary values,
- empty/null/missing cases where relevant,
- failure paths,
- important business rules,
- regression cases for known defects.

### 7. Keep each test focused

Each test should explain one behavior clearly. Avoid large scenario tests with many unrelated assertions.

### 8. Use clear test names

Prefer names that describe behavior and condition.

### 9. Keep test data minimal and expressive

Use builders, factories, or literals that make the relevant detail obvious. Do not bury the point of the test in noisy setup.

### 10. Avoid unnecessary mocks

Use real objects for simple collaborators. Use fakes/stubs for external boundaries. Use mocks mainly when interaction itself is the behavior being specified.

### 11. Make failures diagnostic

Assertions should make it obvious what behavior failed and why.

### 12. Preserve maintainability

Do not write brittle tests that fail on harmless refactoring. Do not assert private methods, internal call order, generated timestamps, random IDs, log formatting, or incidental collection ordering unless those are contractual behavior.

### 13. Check for affordability

Before finalizing the tests, ask:

- Are these tests fast?
- Are they deterministic?
- Are they independent?
- Are they easy to understand?
- Do they protect behavior users or downstream systems care about?
- Could the same confidence be achieved with fewer or cheaper tests?
- Does the proposed `run_tests` set preserve the 30-second total-suite budget?

### 14. Review the test portfolio

For every proposed test, classify it as one of:

- Unit (Microtest)
- Contract Test
- Component Test
- End-to-End Test

For each classification:

- Explain why that level is appropriate.
- Explain why a lower-cost level would not provide sufficient confidence.
- If the test is Component or End-to-End, explicitly justify why it cannot reasonably be replaced by Unit or Contract tests.
- Prefer the lowest-cost test level that provides adequate confidence.
- Treat unnecessary movement upward in the test pyramid as a design smell.

### 15. Assign tests to the earliest useful feedback loop

For every proposed test, assign it to one of:

- `run_tests`
- `full_test_only`

Assign each test to the earliest feedback loop that can economically provide its confidence signal.

If a test can reasonably run in `run_tests` while preserving the 30-second total-suite budget, it should not be classified as `full_test_only`.

When a test is classified as `full_test_only`, explain:

- Why it cannot fit into the 30-second `run_tests` budget.
- Why its confidence cannot be obtained by a cheaper deterministic test.
- What would need to change to move that confidence into `run_tests`.

## Workflow

Given production code, requirements, or a bug report:

1. Briefly identify the behaviors that need protection.
2. List any nondeterminism risks in the current design or tests.
3. Propose the test cases before writing code.
4. Classify each proposed test as Unit, Contract, Component, or End-to-End and justify the classification.
5. Assign each proposed test to `run_tests` or `full_test_only`, and justify that assignment against the 30-second fast-feedback budget.
6. Write the tests.
7. Explain any dependency seams, fakes, stubs, builders, or fixtures used.
8. Note any production-code changes needed to make the tests deterministic, fast, or affordable.
9. Identify tests that could be moved to a cheaper level while preserving confidence.
10. Identify tests that could be moved from `full_test_only` into `run_tests` by improving design, isolation, or determinism.
11. Do not add sleeps, retries, real network calls, real clocks, uncontrolled randomness, tolerated failures, quarantine lists, or order-dependent assumptions.
