# Spec Compliance

These rules apply to all files in the project.

See also: [Repository Scope Enforcement](repo-scope.md)

---

## Feature Artifacts

Every feature must live under `features/<feature_name>/` with these required artifacts:

- `acceptance.feature` — Gherkin scenarios with Given/When/Then steps
- `nfrs.md` — Non-functional requirements (no TBD entries permitted; sections per `NFRS_CONVENTIONS.md`)
- `eval_criteria.yaml` — Evaluation configuration validated against the agent's schema
- `architecture_preflight.md` — Pre-implementation alignment check
- `plan.md` — Implementation plan with increments, tests, and deliverables

Implementation must not begin unless all five artifacts exist and are complete.

## Defect fixes

A change that *restores* behavior an existing requirement, contract, ADR, or
spec already established may use the fix lane instead of the five artifacts
above: one record at `fixes/<id>/fix.yaml`, scaffolded by `govkit fix init <id>`.

It qualifies only when all four hold:

- It restores established behavior, and names the source that established it
- It includes a reproduction or regression test
- It introduces no new intended behavior
- It does not change architecture, security/auth, data handling, public
  contracts, NFRs, or cross-service ownership

If any of those fails, the change belongs in the feature lane above — and, where
the contract requires one, behind an ADR. Declaring a risk flag `true` does not
waive it; it moves the change out of this lane.

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
