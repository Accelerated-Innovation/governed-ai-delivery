---
name: l3-implementation-plan
description: Generate an ordered implementation checklist from a feature plan — Level 3 Spec-Driven
argument-hint: "<feature_name>"
user-invocable: true
---

# Implementation Plan (Level 3)

You are writing an implementation plan for a feature.

---

## 1. Inputs

Use the following artifacts:

* `features/$ARGUMENTS/nfrs.md`
* `features/$ARGUMENTS/acceptance.feature`
* `features/$ARGUMENTS/plan.md`
* `docs/backend/architecture/DESIGN_PRINCIPLES.md`
* `docs/backend/architecture/TESTING.md`

---

## 2. Planning Requirements

The implementation plan must:

* Enforce test-first development (tests before implementation in every step)
* Follow SOLID, DRY, YAGNI, KISS principles
* Respect existing project structure and conventions

---

## 3. Output Format

Return a Markdown checklist with the following sections.

---

### Feature Summary

* Business goal
* User value
* Success criteria

---

### Task Breakdown (Ordered Checklist)

List all implementation steps in order. Each step must:

* Specify files/modules touched
* Reference the spec or design principle driving it
* Mark test steps explicitly (write tests before implementation)

---

### Test Plan

#### Unit Tests

* Mocking strategy
* Isolation strategy

#### Integration Tests

* Gherkin scenario mapping
* Test data approach

---

### Refactor Triggers

List conditions under which refactoring must occur:

* Duplication detected
* Complexity threshold exceeded
* Test flakiness detected

---

### Risks & Unknowns

* Missing constraints
* Integration risks
* Performance concerns
* Security implications

---

## 4. Output Rules

* Do not generate implementation code.
* Plan must be executable as-is.

This output feeds Copilot Agent for implementation.
