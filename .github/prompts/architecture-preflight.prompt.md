# Architecture Preflight Prompt

You are preparing to plan and implement a new feature.

Before generating any code or detailed plan, produce an Architecture Preflight Report that includes:

## 1. Summary

- What is the feature or change?
- What input specs are being used (NFRs, Gherkin, LLM evals)?
- What affected modules or layers are in scope?

## 2. Standards Check

For each of the following, state which architectural rules or standards apply (cite file and section):

- Layering (from `ARCH_CONTRACT.md`)
- API conventions (from `API_CONVENTIONS.md`)
- Auth/security patterns (from `SECURITY_AUTH_PATTERNS.md`)
- Error model and response shape
- Logging and observability expectations

## 3. Boundary Analysis

- What modules or services will this code touch?
- Are any boundary rules at risk of violation? (from `BOUNDARIES.md`)
- Does this require a new interface between services?

## 4. ADR Decision

Choose one:

- ✅ ADR required → Include proposed ADR title and reason
- ✅ No ADR needed → Explain why

## 5. Tests Required

- What test types are needed? (unit, contract, integration, evals)
- What test coverage or metrics are required by the NFRs?

## 6. Risks & Unknowns

- List assumptions, open design questions, or external risks
- Flag any missing constraints, incomplete specs, or potential conflicts

---

Output this report as structured Markdown so it can be pasted into a PR, issue comment, or planning doc.

If any spec inputs are missing, ask the user before proceeding.

