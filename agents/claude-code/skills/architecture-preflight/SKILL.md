---
description: "Run before planning any feature to validate architecture boundaries, standards alignment, and ADR need"
argument-hint: "<feature_name>"
---

# Architecture Preflight

You are preparing to plan and implement the feature: **$ARGUMENTS**

Before generating any code or detailed plan, produce an Architecture Preflight Report.

## 1. Summary

- What is the feature or change?
- What input specs are being used (NFRs: `features/$ARGUMENTS/nfrs.md`, Gherkin: `features/$ARGUMENTS/acceptance.feature`)?
- What affected modules or layers are in scope?

## 2. Standards Check

For each of the following, state which architectural rules apply (cite file and section):

- Layering (from `docs/backend/architecture/ARCH_CONTRACT.md`)
- API conventions (from `docs/backend/architecture/API_CONVENTIONS.md`)
- Auth/security patterns (from `docs/backend/architecture/SECURITY_AUTH_PATTERNS.md`)
- Error model and response shape
- Logging and observability expectations

## 3. Boundary Analysis

- What modules or services will this code touch?
- Are any boundary rules at risk of violation? (from `docs/backend/architecture/BOUNDARIES.md`)
- Does this require a new interface between services?

## 4. ADR Decision

Choose one:

- ADR required → Include proposed ADR title and reason
- No ADR needed → Explain why

## 5. Tests Required

- What test types are needed? (unit, contract, integration, evals)
- What test coverage or metrics are required by the NFRs?

## 6. Risks & Unknowns

- List assumptions, open design questions, or external risks
- Flag any missing constraints, incomplete specs, or potential conflicts

---

Write this report to `features/$ARGUMENTS/architecture_preflight.md`.

If any spec inputs are missing, ask before proceeding.
