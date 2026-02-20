# Evaluation Standards

This document defines the global quality and evaluation contract for all AI-assisted code generation in this repository.

It governs:

* Unit test quality (FIRST)
* Implementation quality (7 Code Virtues)
* Agent generation cycle
* Refactor triggers
* Scoring and acceptance thresholds
* Structural simplicity rules

All feature-level `eval_criteria.yaml` files must conform to this standard.

---

# 1. Unit Test Principles — FIRST

All generated unit tests must satisfy FIRST:

## Fast

* No real network calls
* No real database access
* No unnecessary sleep/timing dependencies
* Tests must execute quickly enough for frequent CI runs

## Isolated

* No shared mutable state
* Use dependency injection
* Mock external systems
* No order-dependent tests

## Repeatable

* Control randomness via seeding
* Freeze time for time-based logic
* Avoid environment-specific assumptions

## Self-Verifying

* Explicit assertions
* No manual log inspection
* Clear pass/fail outcomes

## Timely

* Tests written before or alongside implementation
* Compatible with Red-Green-Refactor cycle

---

# 2. Implementation Quality — 7 Code Virtues

All generated code must exhibit these virtues:

## Working

* All tests pass
* Edge cases handled
* No runtime errors

## Unique

* No duplicated logic
* Shared abstractions extracted

## Simple (Structural Simplicity)

* Minimal variables and mutable state
* Minimal branching and nesting
* Few execution paths per behavior
* Prefer straightforward data flow
* Modern language constructs allowed when they reduce structural complexity

### Refactor Triggers

* Deep nesting
* Excessive flags or state variables
* High cyclomatic complexity
* Interleaved concerns in one function

## Clear

* Descriptive identifiers
* Functions do one thing
* Minimal explanatory comments needed

## Easy

* Loose coupling
* High cohesion
* Clear extension points

## Developed

* Tests exist
* Dead code removed
* Consistent style

## Brief

* No redundant comments
* No speculative abstractions
* No unnecessary boilerplate

---

# 3. Agent Evaluation Workflow

Generation cycle:

1. Generate FIRST-compliant tests
2. Implement minimal working code
3. Run tests
4. Refactor for virtues
5. Re-run tests

---

# 4. Scoring Model

## Unit Tests

* FIRST score: 0–5 per principle
* Minimum average: 4

## Code Quality

* Virtue score: 0–5 per virtue
* Minimum average: 4

## Acceptance Threshold

* Tests must pass
* FIRST average >= 4
* Virtue average >= 4

---

# 5. Automatic Refactor Conditions

Trigger automatic refactor when:

* Duplicate logic detected
* Complexity threshold exceeded
* Test flakiness detected
* Low clarity score
* Excessive structural complexity detected

---

# 6. Structural Expression Guidance

Expression forms are preferred only when they reduce structural complexity and preserve clarity.

Prefer:

* Simple ternaries over temporary variables
* List comprehensions that remove incidental state
* Array methods that reduce mutable accumulators

Avoid:

* Nested ternaries
* Deeply chained expressions
* Expressions with hidden side effects

---

# 7. Feature-Level Eval YAML Schema

Each feature must include `features/<feature>/eval_criteria.yaml` with this structure:

```yaml
version: 1.0
feature: <feature_name>

unit_tests:
  enforce_FIRST: true
  minimum_FIRST_average: 4

code_quality:
  enforce_virtues: true
  minimum_virtue_average: 4

llm_evaluation:
  enabled: true
  dimensions:
    - name: groundedness
      threshold: 0.9
    - name: safety
      threshold: 1.0
  dataset: eval_sets/<feature_name>.json
  fail_on_regression: true
```

This YAML is generated or updated during the planning phase and enforced during CI.

---

All Copilot planning and implementation must reference this document when generating evaluation criteria.
