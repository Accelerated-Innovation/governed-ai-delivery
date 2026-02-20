# Implementation Plan Prompt

You are writing an implementation plan based on a validated architecture preflight.

This plan must be evaluation-driven.

---

## 1. Inputs

Use the following artifacts:

* `features/<FEATURE>/nfrs.md`
* `features/<FEATURE>/<FEATURE>.feature`
* `features/<FEATURE>/eval_criteria.yaml`
* `docs/evaluation/eval_criteria.md`
* `docs/architecture/**`
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

Provide a predicted compliance summary before implementation begins:

* Expected FIRST average score (0–5) and justification
* Expected 7 Virtue average score (0–5) and justification
* Identified refactor triggers likely to occur
* Risk areas that may reduce evaluation scores
* Confirmation that `eval_criteria.yaml` thresholds are satisfied by design

If predicted averages are below required thresholds, adjust the plan before proceeding.

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
* Plan must explicitly align with `docs/evaluation/eval_criteria.md`.

This output feeds Copilot Agent for implementation.
