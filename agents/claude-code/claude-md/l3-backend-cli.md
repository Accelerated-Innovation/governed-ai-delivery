# Spec-Driven Development — Claude Code Instructions

These instructions are mandatory. Claude operates as a spec-driven delivery system.

Repository artifacts are the source of truth. Chat history is not.

---

## Operating Mode

Claude operates aligned to:

- Product specifications under `features/`
- Design principles under `docs/backend/architecture/DESIGN_PRINCIPLES.md`
- Testing conventions under `docs/backend/architecture/TESTING.md`

Before planning or generating code:

- Read `docs/backend/architecture/DESIGN_PRINCIPLES.md`
- Read `docs/backend/architecture/TESTING.md`
- Confirm required feature artifacts exist

If required inputs are missing, stop and ask.

---

## Mandatory Feature Structure

Every feature must live under `features/<feature_name>` with these required artifacts:

- `acceptance.feature`
- `nfrs.md`
- `plan.md`

Implementation must not begin unless all three artifacts exist.

Before proceeding to planning:

- If `nfrs.md` contains TBD entries in any category, stop and request completion
- If `acceptance.feature` is empty or missing scenarios, stop and request completion

---

## Feature Lifecycle (Mandatory Order — no steps may be skipped)

1. Write acceptance criteria (`acceptance.feature`)
2. Complete NFRs (`nfrs.md`)
3. Plan finalization → run `/spec-planning`
4. Implementation planning → run `/implementation-plan`
5. Incremental implementation (test-first)
6. Automated tests
7. CI gates (lint, tests)

---

## Planning Discipline

Generate and maintain `features/<feature_name>/plan.md` based on `governance/backend/templates/l3-plan.md`.

The plan must:

- Define explicit increments with deliverables and tests
- Map Gherkin scenarios to integration tests
- List tests before implementation in each increment

---

## Implementation Rules

- Implement one increment at a time
- Write tests before implementation code (test-first)
- Follow design principles from `docs/backend/architecture/DESIGN_PRINCIPLES.md` (SOLID, DRY, YAGNI, KISS)
- Follow testing conventions from `docs/backend/architecture/TESTING.md`

Generic rules load automatically from `.claude/rules/`:

- `test-first.md` — test-first development discipline
- `spec-compliance.md` — feature artifact and Gherkin conventions

---

## Testing Requirements

Each increment must include:

- Unit tests written before implementation code
- Integration tests derived from Gherkin scenarios

Gherkin scenarios must follow conventions:

- Every populated NFR category in `nfrs.md` must have at least one scenario tagged with the corresponding `@nfr-*` tag

---

## Automatic Refactor Conditions

Trigger refactor before proceeding if:

- Duplicate logic detected
- Structural complexity excessive
- Test flakiness detected

---

## Output Expectations

Every plan and implementation output must include:

- Referenced design principles
- Test coverage summary

If alignment is unclear, stop and ask.

---

## Commit Discipline

- Complete one increment, then commit before starting the next
- Each commit must be independently buildable and testable
- Commit message references the increment: `feat(<feature>): increment N — <name>`
- Do not combine multiple increments into a single commit
- If an increment exceeds ~300 lines of production code, split it before committing

---

## Authority

Architecture decisions belong to the team. Claude follows specifications — it does not invent them.
