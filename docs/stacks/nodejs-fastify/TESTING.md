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

Testing verifies deterministic system behavior. LLM evaluation verifies AI system behavior quality. Both are required for feature completion.

LLM evaluation rules are defined in:

docs/backend/evaluation/eval_criteria.md

---

# 2. Test Types

## Unit Tests

Unit tests validate small units of behavior.

Typical targets:

- domain services
- pure functions
- validation logic
- adapter logic with mocked dependencies

Unit tests must satisfy **FIRST principles**.

**Tooling:** Vitest + `vi.fn()` for mocking.

---

## BDD Integration Tests

Integration tests must follow **BDD style** and map directly to Gherkin scenarios.

BDD tests validate:

- end-to-end feature behavior
- interaction across layers
- API behavior
- authorization flows
- cross-boundary logic

Each scenario in `features/<feature_name>/acceptance.feature` should have a corresponding step definition.

**Tooling:** Cucumber.js (`@cucumber/cucumber`) with Vitest assertions.

---

## Contract Tests

Contract tests verify interface stability.

Required when:

- APIs are introduced or modified
- external services are integrated
- ports define integration contracts

**Tooling:** `supertest` or Fastify `inject()` + Vitest.

---

# 3. FIRST Principles for Unit Tests

## Fast

Unit tests must not call real external services, databases, or rely on timing. External dependencies must be mocked with **`vi.fn()`** or `vi.spyOn()`.

## Isolated

Each test must run independently — no shared mutable state, all dependencies injected and mocked, tests pass regardless of execution order.

## Repeatable

- Control randomness via fixed seeds (`vi.spyOn(Math, 'random').mockReturnValue(0.5)`)
- Freeze time using `vi.setSystemTime(new Date('2026-01-01'))` / `vi.useRealTimers()`
- Avoid environment-specific assumptions

## Self-Verifying

- Explicit assertions required — `expect(result).toBe(expected)`
- No manual log inspection or manual verification steps

## Timely

Tests must be written **before or alongside implementation** following the **Red → Green → Refactor** cycle.

---

# 4. Test-First Development (TDD)

All feature work must follow the **Red → Green → Refactor** cycle.

1. **Write the test first.** The test defines the specification.
2. **Confirm the test fails.** Red state proves the feature doesn't exist yet.
3. **Implement minimal code to pass.** Green state — no more, no less.
4. **Refactor while keeping tests passing.**

Each increment in `plan.md` lists tests before implementation:

```
## Increment 1: JWT validation

### Tests (write first)
- validateToken_withValidSignature_returnsUserContext
- validateToken_withInvalidSignature_throwsAuthError
- validateToken_whenExpired_throwsAuthError

### Implementation
- TokenValidator class
- RS256 signature verification
- Expiration check
```

Do not mark an increment complete until all listed tests pass.

---

# 5. Test Immutability and Prohibited Practices

Tests must **not** be rewritten to make failing code pass.

## Anti-Patterns (Forbidden)

| Anti-Pattern | Why It's Wrong | What To Do Instead |
|---|---|---|
| "The test is too strict, let me loosen it" | Tests define the contract | Fix the implementation |
| "The test is hard to write, let me skip it" | Skipped tests mean untested code | Solve the design problem |
| "The test fails, let me adjust expectations" | Changes spec to fit broken code | Fix the code |
| "This test is flaky, let me add `sleep`/retry" | Masks real timing bugs | Fix the race condition |
| "I'll skip this test until I have time" | Tests are requirements | Enable and fix now |

---

# 6. BDD Integration Testing

BDD integration tests should be derived from Gherkin scenarios using **Cucumber.js**.

Example step definition:

```typescript
import { Given, When, Then } from '@cucumber/cucumber'
import { expect } from 'vitest'
import request from 'supertest'
import { buildApp } from '../../src/app.js'

let response: request.Response

Given('a registered user', async function () {
  // seed test data via test helper
})

When('the user requests a password reset', async function () {
  const app = await buildApp()
  response = await request(app.server)
    .post('/v1/users/reset-password')
    .send({ email: 'user@example.com' })
})

Then('a reset email is sent', function () {
  expect(response.status).toBe(202)
})
```

---

# 7. Hexagonal Architecture Testing

## Domain Layer

- Test business rules and domain logic
- Do not test Fastify, Drizzle/Prisma, or infrastructure logic
- All dependencies mocked with `vi.fn()`

## Ports

- Ports (TypeScript interfaces) themselves don't require unit tests
- Adapter implementations tested against their port contract

## Adapters

- Translation between domain and infrastructure
- Use **Testcontainers** for real database/Redis integration tests
- Use **MSW** (Mock Service Worker, Node mode) for external HTTP service stubbing

---

# 8. Test Structure

```
src/
  __tests__/
    unit/
    integration/
    contract/
    bdd/
      steps/
      features/    (symlink or copy of features/<feature>/acceptance.feature)
```

Name test files using `*.test.ts` for Vitest discovery.

Example:

```
__tests__/unit/userService.test.ts
__tests__/bdd/steps/resetPassword.steps.ts
__tests__/contract/userApi.contract.test.ts
```

---

# 9. Continuous Integration Requirements

All pull requests must pass:

- unit tests (`vitest run`)
- BDD integration tests (`cucumber-js`)
- contract tests
- static analysis (ESLint, `tsc --noEmit`)
- security scans (Snyk)
- evaluation gates

---

# 10. Forbidden Testing Practices

The following are not allowed:

- tests requiring manual verification
- reliance on test ordering
- uncontrolled randomness
- real external systems in unit tests
- fragile timing-dependent tests
- tests tightly coupled to Fastify internals

---

# 11. Definition of Done

A feature is complete when:

- all acceptance scenarios are implemented
- NFR constraints are validated
- evaluation criteria pass
- CI pipeline passes
- architecture boundaries remain intact (verified by `dependency-cruiser`)
