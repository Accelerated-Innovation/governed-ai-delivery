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

**Tooling:** JUnit 5 + Mockito + AssertJ.

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

**Tooling:** Cucumber-JVM (`cucumber-java`, `cucumber-junit-platform-engine`, `cucumber-spring`).

---

## Contract Tests

Contract tests verify interface stability.

Required when:

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

## Fast

Unit tests must not call real external services, databases, or rely on timing. External dependencies must be mocked with **Mockito**.

## Isolated

Each test must run independently — no shared mutable state, all dependencies injected and mocked, tests pass regardless of execution order.

## Repeatable

- Control randomness via fixed seeds
- Freeze time using `java.time.Clock` injected as a dependency
- Avoid environment-specific assumptions

## Self-Verifying

- Explicit assertions required — use **AssertJ** (`assertThat(...).isEqualTo(...)`)
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
- validateToken_withInvalidSignature_throwsAuthException
- validateToken_whenExpired_throwsAuthException

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
| "This test is flaky, let me add sleep/retry" | Masks real timing bugs | Fix the race condition |
| "I'll disable this test until I have time" | Tests are requirements | Enable and fix now |

---

# 6. BDD Integration Testing

BDD integration tests should be derived from Gherkin scenarios using **Cucumber-JVM**.

Example step definition with Spring context:

```java
@CucumberContextConfiguration
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class CucumberSpringConfiguration {}

public class ResetPasswordSteps {

    @Autowired TestRestTemplate restTemplate;
    private ResponseEntity<String> response;

    @Given("a registered user")
    public void givenARegisteredUser() {
        // seed test data via TestDataHelper
    }

    @When("the user requests a password reset")
    public void whenUserRequestsPasswordReset() {
        response = restTemplate.postForEntity("/v1/users/reset-password", body, String.class);
    }

    @Then("a reset email is sent")
    public void thenResetEmailIsSent() {
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.ACCEPTED);
    }
}
```

---

# 7. Hexagonal Architecture Testing

## Domain Layer

- Test business rules and domain logic
- Do not test Spring Web, JPA, or infrastructure logic
- All dependencies mocked with Mockito

## Ports

- Ports themselves don't require unit tests
- Adapter implementations tested in isolation against their port contract

## Adapters

- Translate between domain and infrastructure
- Use Testcontainers for real database/Redis integration tests
- Use WireMock for external HTTP service stubbing

---

# 8. Test Structure

```
src/test/java/
  unit/
  integration/
  contract/
  bdd/
    steps/
    features/          (symlink or copy from features/<feature>/acceptance.feature)
```

Name test methods using: `methodName_condition_expectedResult`.

Example:

```
unit/UserServiceTest.java
bdd/steps/ResetPasswordSteps.java
contract/UserApiContractTest.java
```

---

# 9. Continuous Integration Requirements

All pull requests must pass:

- unit tests (`mvn test` unit surefire)
- BDD integration tests
- contract tests
- static analysis (Checkstyle, SpotBugs)
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
- tests tightly coupled to Spring internals

---

# 11. Definition of Done

A feature is complete when:

- all acceptance scenarios are implemented
- NFR constraints are validated
- evaluation criteria pass
- CI pipeline passes
- architecture boundaries remain intact (verified by ArchUnit)
