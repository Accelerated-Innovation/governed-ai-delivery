# Testing Standards

This document defines the testing policy for this repository.

All tests must support:

- Spec-driven development
- Evaluation-driven delivery
- Hexagonal architecture boundaries
- Deterministic CI execution

Testing is not optional. Every feature must include automated verification aligned to the feature specification.

---

# 1. Testing Philosophy

Testing verifies that:

- Feature specifications are satisfied
- Architecture boundaries are respected
- Evaluation thresholds are achievable
- System behavior is stable and deterministic

All tests must be **automated, reproducible, and traceable to specifications**.

Every feature must maintain traceability between:

- `acceptance.feature`
- `nfrs.md`
- `eval_criteria.yaml`
- automated tests

## Relationship to LLM Evaluation

Testing verifies deterministic system behavior.

Examples:
- domain logic correctness
- API behavior
- integration flows
- interface contracts

LLM evaluation verifies AI system behavior quality.

Examples:
- groundedness
- hallucination resistance
- safety constraints
- response structure

Both are required for feature completion.

Testing ensures the system functions correctly.
LLM evaluation ensures the AI behaves correctly.

LLM evaluation rules are defined in:

docs/backend/evaluation/eval_criteria.md

---

# 2. Test Types

This repository uses three categories of tests.

## Unit Tests

Unit tests validate small units of behavior.

Typical targets:

- domain services
- pure functions
- validation logic
- adapter logic with mocked dependencies

Unit tests must satisfy **FIRST principles**.

---

## BDD Integration Tests

Integration tests must follow **BDD style** and map directly to Gherkin scenarios.

BDD tests validate:

- end-to-end feature behavior
- interaction across layers
- API behavior
- authorization flows
- cross-boundary logic

Each scenario in:
`features/<feature_name>/acceptance.feature`

should have a corresponding automated test.

BDD tests verify **observable system behavior**, not internal implementation details.

---

## Contract Tests

Contract tests verify interface stability.

Contract tests are required when:

- APIs are introduced or modified
- external services are integrated
- ports define integration contracts

Contract tests validate:

- request/response schemas
- error models
- backward compatibility
- port contract behavior

---

# 3. FIRST Principles for Unit Tests

All unit tests must follow FIRST.

## Fast

Tests must run quickly.

Unit tests must not:

- call real external services
- call real databases
- rely on long sleeps or timing dependencies

External dependencies must be mocked.

---

## Isolated

Each test must run independently.

Rules:

- no shared mutable state
- dependency injection must be used
- external systems must be mocked
- tests must pass regardless of execution order

---

## Repeatable

Tests must produce the same result in any environment.

Rules:

- control randomness via seeding
- freeze time when testing time-based logic
- avoid environment-specific assumptions

---

## Self-Verifying

Tests must automatically determine pass/fail.

Rules:

- explicit assertions are required
- no manual log inspection
- no manual verification steps

---

## Timely

Tests must be written **before or alongside implementation**.

Tests should describe behavior rather than internal implementation.

This enables the **Red → Green → Refactor** cycle.

---

# 4. Test-First Development (TDD)

All feature work must follow the **Red → Green → Refactor** cycle.

## Discipline

1. **Write the test first.** The test defines the specification before code exists.
2. **Confirm the test fails.** Red state proves the test can fail and the feature doesn't exist yet.
3. **Implement minimal code to pass the test.** Green state — no more, no less.
4. **Refactor while keeping tests passing.** Tests remain your safety net.

## Principle

**Tests are the specification. Code must conform to tests, not vice versa.**

Implementation adapts to satisfy the tests. Tests are immutable until the specification changes.

## Process

Each increment in `plan.md` lists tests before implementation:

```
## Increment 1: JWT validation

### Tests (write first)
- test_validate_token_with_valid_signature
- test_reject_token_with_invalid_signature
- test_reject_expired_token

### Implementation
- TokenValidator class
- RS256 signature verification
- Expiration check
```

Do not mark an increment complete until all listed tests pass.

---

# 5. Test Immutability and Prohibited Practices

Tests must **not** be rewritten to make failing code pass.

## Rule

If a test fails, the default response is: **fix the implementation**.

Tests may ONLY be changed when:
- The specification actually changed
- The Gherkin scenario was incorrect
- The original test did not represent the intended behavior
- A true design flaw was discovered (rare)

## Anti-Patterns (Forbidden)

These are violations of test-first discipline:

| Anti-Pattern | Why It's Wrong | What To Do Instead |
|---|---|---|
| "The test is too strict, let me loosen it" | Tests define the contract; code must meet it | Fix the implementation to be correct |
| "The test is hard to write, let me skip it" | Skipped tests mean untested code | Solve the design problem that makes the test hard |
| "The test fails, let me adjust expectations" | Changes the spec to fit broken code | Fix the code to meet the spec |
| "This test is flaky, let me add sleep/retry" | Masks real timing or concurrency bugs | Fix the actual race condition or non-determinism |
| "I'll disable this test until I have time to fix it" | Tests can't fail; they're requirements | Enable and fix it now, or defer the feature |
| "Let me rewrite the test to match my implementation" | Breaks traceability to the spec | Implement to match the test |

## When Tests Are Wrong

If you discover a test is genuinely incorrect:

1. Write a NEW test that clarifies the correct behavior
2. Do NOT modify the existing test
3. Fix implementation to pass both tests
4. Document the correction in a commit message

This preserves the history and intent of the original test.

---

# 6. BDD Integration Testing

BDD integration tests should be derived from Gherkin scenarios.

Example:

```gherkin
Scenario: user resets password
  Given a registered user
  When the user requests a password reset
  Then a reset email is sent
```

BDD tests validate:

- API endpoints
- domain orchestration
- adapter interactions
- authentication and authorization
- error scenarios

BDD tests focus on **behavior**, not internal structure.

---

# 7. Hexagonal Architecture Testing

Tests should align with architectural boundaries.

## Domain Layer

Test:

- business rules
- domain logic
- state transitions

Do not test:

- HTTP frameworks
- database drivers
- infrastructure logic

---

## Ports

Test:

- contract expectations
- interface behavior

Ports should remain simple and stable.

---

## Adapters

Test:

- translation between domain and infrastructure
- error handling
- external system interactions

External dependencies should be mocked unless running integration tests.

---

# 8. Test Structure

Recommended structure:
```
tests/
unit/
integration/
contract/
bdd/
```

Example:

```
tests/unit/test_user_service.py
tests/bdd/test_reset_password.py
tests/contract/test_user_api_contract.py
```


---

# 9. Continuous Integration Requirements

All pull requests must pass:

- unit tests
- BDD integration tests
- contract tests
- static analysis
- security scans
- evaluation gates

All tests must run automatically in CI.

---

# 10. Forbidden Testing Practices

The following are not allowed:

- tests requiring manual verification
- reliance on test ordering
- uncontrolled randomness
- real external systems in unit tests
- fragile timing-dependent tests
- tests tightly coupled to framework internals

---

# 11. Definition of Done

A feature is complete when:

- all acceptance scenarios are implemented
- NFR constraints are validated
- evaluation criteria pass
- CI pipeline passes
- architecture boundaries remain intact
