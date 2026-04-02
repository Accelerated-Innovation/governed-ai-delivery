---
description: "Generate an ordered implementation checklist with evaluation compliance summary from a validated preflight"
agent: "ask"
---

# Implementation Plan Prompt

You are writing an implementation plan based on a validated architecture preflight.

This plan must be evaluation-driven.

---

## 1. Inputs

Use the following artifacts:

* `features/<FEATURE>/nfrs.md`
* `features/<FEATURE>/acceptance.feature`
* `features/<FEATURE>/eval_criteria.yaml`
* `docs/backend/evaluation/eval_criteria.md`
* `docs/backend/architecture/**`
* Architecture preflight output

---

## 2. Planning Requirements

The implementation plan must:

* Follow Hexagonal Architecture (ports + adapters)
* Enforce FIRST principles for unit tests
* Enforce 7 Code Virtues for implementation
* Respect all boundary and dependency contracts
* Align with feature-specific eval thresholds

---

## 3. Output Format

Return a Markdown checklist with the following sections.

---

### Feature Summary

* Business goal
* User value
* Success criteria

---

### Architecture Mapping

Identify:

* Inbound ports (`ports/inbound/**`)
* Domain services (`services/**`)
* Outbound ports (`ports/outbound/**`)
* Adapters (`adapters/**`)
* API routes (`api/**`)

Explicitly confirm no boundary violations.

---

### Task Breakdown (Ordered Checklist)

List all implementation steps in order.

Example:

1. Define inbound port in `ports/inbound/<FEATURE>.py`
2. Define outbound port in `ports/outbound/<FEATURE>.py`
3. Implement service in `services/<FEATURE>.py`
4. Implement adapter in `adapters/<FEATURE>_adapter.py`
5. Register API route in `api/<FEATURE>.py`
6. Add unit tests (FIRST compliant)
7. Add integration tests
8. Add LLM evaluation harness

Each step must:

* Specify files/modules touched
* Reference the spec or architectural rule driving it
* Reference which FIRST principle it supports (if test-related)
* Reference which Code Virtue is at risk
* Mark ❗ if ADR required

---

### Test & Evaluation Plan

#### Unit Tests

* How FIRST will be satisfied
* Mocking strategy
* Isolation strategy

#### Code Quality

* Simplicity risks
* Duplication risks
* Expected refactor points

#### LLM Evaluation

* Which dimensions from `eval_criteria.yaml` apply
* Dataset or prompt set
* CI gate expectations

---

### Evaluation Compliance Summary

Provide a predicted compliance summary before implementation begins using the standardized format:

- FIRST rubric: `docs/backend/evaluation/FIRST_SCORING_RUBRIC.md`
- Virtue rubric: `docs/backend/evaluation/VIRTUE_SCORING_RUBRIC.md`

Each increment should target ~300 lines of production code. If an increment exceeds 500 lines, split it.

If predicted FIRST average or Virtue average is below 4.0, adjust the plan before proceeding.

---

### Refactor Triggers

List conditions under which refactoring must occur:

* Duplication detected
* Complexity threshold exceeded
* Structural simplicity violated
* FIRST score < threshold
* Virtue score < threshold

---

### Risks & Unknowns

* Missing constraints
* Integration risks
* Performance concerns
* Security implications

---

## 4. Output Rules

* Do not generate implementation code.
* Do not skip evaluation planning.
* Plan must be executable as-is.
* Plan must explicitly align with `docs/backend/evaluation/eval_criteria.md`.

This output feeds Copilot Agent for implementation.
