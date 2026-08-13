---
applyTo: "*"
---

# Spec Compliance

These instructions apply to all files in the project.

See also: [Repository Scope Enforcement](repo-scope.instructions.md)

---

## Feature Artifacts

Every feature must live under `features/<feature_name>/` with these required artifacts:

- `acceptance.feature` — Gherkin scenarios with Given/When/Then steps
- `nfrs.md` — Non-functional requirements (no TBD entries permitted; sections per `NFRS_CONVENTIONS.md`)
- `eval_criteria.yaml` — Evaluation configuration validated against the agent's schema
- `architecture_preflight.md` — Pre-implementation alignment check
- `plan.md` — Implementation plan with increments, tests, and deliverables

Implementation must not begin unless all five artifacts exist and are complete.

## Gherkin Conventions

- Every `acceptance.feature` must have a `Feature:` keyword, at least one `Scenario:`, and Given/When/Then steps
- Every populated NFR category in `nfrs.md` must have at least one scenario tagged with the corresponding `@nfr-*` tag
- Features producing shared artifacts should include `@contract` scenarios

## Pre-Implementation Checks

Before writing any implementation code:

- Verify `nfrs.md` contains no TBD entries
- Verify `acceptance.feature` has complete scenarios
- Verify `eval_criteria.yaml` exists and validates against the schema
- Verify `architecture_preflight.md` exists and its status is not Blocked
- Verify `plan.md` exists with defined increments and tests
- Verify "Repository Scope" section in `nfrs.md` is complete (see Repository Scope Enforcement rule)

If any artifact is incomplete, stop and request completion before proceeding.

## Plan Discipline

- Follow the increments defined in `plan.md`
- Implement one increment at a time
- Each increment must be independently buildable and testable
- Do not expand scope beyond the active increment
