# Implementation Plan Prompt

You are writing an implementation plan based on a validated architecture preflight.

## 1. Inputs

Use the following artifacts:

* `features/<FEATURE>/nfrs.md` — non-functional requirements
* `features/<FEATURE>/<FEATURE>.feature` — Gherkin acceptance criteria
* `features/<FEATURE>/eval_criteria.yaml` — LLM evaluation hooks
* `docs/architecture/**` — contract, boundaries, security, API conventions
* Architecture preflight output — previously generated via `/architecture-preflight`

## 2. Output Format

Return a Markdown implementation plan with these sections:

### Feature Summary

Briefly explain the purpose of the feature and user value.

### Task Breakdown

List all implementation steps in order:

Example:

1. Define request/response models in `ports/inbound/<FEATURE>.py`
2. Implement domain logic in `services/<FEATURE>.py`
3. Add outbound port interface in `ports/outbound/<FEATURE>.py`
4. Implement outbound adapter in `adapters/<FEATURE>_adapter.py`
5. Register FastAPI route in `api/<FEATURE>.py`
6. Add unit tests, contract tests, and evaluation harnesses

Each step should:

* Specify which file(s) or module(s) will be modified or created
* Reference the related spec or architectural constraint
* Mark any step that requires a new ADR ❗

### Test Plan

* Coverage expectations for each module
* Required unit, integration, and contract tests
* LLM evaluation hooks or test entrypoints

### Risk Notes

* Known issues or implementation uncertainties
* External dependencies, missing context, or deferred work

---

Return the plan as a fully formatted Markdown checklist ready to paste into a pull request or tracking issue.
