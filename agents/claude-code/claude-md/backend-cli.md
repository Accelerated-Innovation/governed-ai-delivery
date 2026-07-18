# Governed AI Delivery — Foundations (Level 3)

These instructions are mandatory. Claude operates as a governed delivery system
aligned to your architecture contracts.

Repository artifacts are the source of truth. Chat history is not.

> **Feature artifacts are not part of L3.** If your team adopts spec-driven
> feature delivery (per-feature `acceptance.feature`, `nfrs.md`, `plan.md`,
> `eval_criteria.yaml`, and `architecture_preflight.md`), upgrade with
> `govkit apply --level 4`.

---

## Operating Mode

Claude operates aligned to:

- Architecture contracts under `docs/backend/architecture/`
- Layer-specific path rules under `.claude/rules/govkit/`

Before generating or modifying code:

- Read the architecture contracts relevant to the layer you are touching
  (see Architecture Contracts below)
- Apply architecture, testing, technology, and security contracts as binding
  constraints
- Confirm boundary rules in `docs/backend/architecture/BOUNDARIES.md`

If required inputs are missing or unclear, stop and ask.

---

## Architecture Contracts

Your project's language- and framework-specific conventions are documented in
`docs/backend/architecture/`. Before implementing in each layer, read the
corresponding document:

| Layer                     | Document                             | Content                                                                |
| ------------------------- | ------------------------------------ | ---------------------------------------------------------------------- |
| CLI / inbound adapter     | `CLI_CONVENTIONS.md`                 | Command structure, argument handling, output formatting, exit codes    |
| Services / domain         | `ARCH_CONTRACT.md`                   | Architecture model, layering, approved libraries                       |
| Ports                     | `ARCH_CONTRACT.md`                   | Port interface guidelines                                              |
| Adapters / infrastructure | `ARCH_CONTRACT.md` + `BOUNDARIES.md` | Integration patterns, layer boundaries, dependency rules               |
| Security / auth           | `SECURITY_AUTH_PATTERNS.md`          | Authentication, token strategy, credential handling, RBAC              |
| Testing                   | `TESTING.md`                         | Test philosophy, FIRST principles, test structure                      |
| Technology decisions      | `TECH_STACK.md`                      | Approved frameworks, libraries, tools, and versions                    |
| Design principles         | `DESIGN_PRINCIPLES.md`               | SOLID, DRY, YAGNI, KISS as applied to your stack                       |

These documents define your stack's specific approach. The architecture
principles (Hexagonal Architecture, boundaries, layered separation) are
universal; the implementation details are here.

Layer-specific rules load automatically from `.claude/rules/govkit/` when editing
files in each layer:

- `cli.md` — `**/cli/**` and `**/commands/**`
- `services.md` — `**/services/**`
- `ports.md` — `**/ports/**`
- `adapters.md` — `**/adapters/**`
- `security.md` — `**/security/**` and `**/auth/**`

---

## Implementation Rules

- Respect all rules in `docs/backend/architecture/BOUNDARIES.md`
- Follow Hexagonal Architecture (ports and adapters)
- Use only approved frameworks from `docs/backend/architecture/TECH_STACK.md`
- Use approved auth patterns from `docs/backend/architecture/SECURITY_AUTH_PATTERNS.md`
- Follow CLI conventions from `docs/backend/architecture/CLI_CONVENTIONS.md`
- Follow design principles from `docs/backend/architecture/DESIGN_PRINCIPLES.md`
- Test-first is recommended for new code; the binding test-first rule is part
  of the Level 4 Spec-Driven Add-On

---

## ADR Rules

An Architecture Decision Record (ADR) is required when:

- A standard is extended, overridden, or bypassed
- A new architectural pattern is introduced
- A security or auth approach changes
- A boundary rule or dependency direction changes
- A shared schema, command contract, or data model is introduced or modified

ADRs live under `docs/backend/architecture/ADR/`, follow
`docs/backend/architecture/ADR/TEMPLATE.md`, and must be Accepted before
implementation proceeds. Use the `/adr-author` skill to scaffold a new ADR.

---

## Testing Requirements

Each change must include:

- Unit tests compliant with FIRST principles per
  `docs/backend/architecture/TESTING.md`
- Integration tests when crossing layer boundaries
- Contract tests when commands, ports, or external integrations are affected

---

## Automatic Refactor Conditions

Trigger refactor before proceeding if:

- Duplicate logic detected
- Structural complexity excessive
- Test flakiness detected

---

## Output Expectations

Every implementation output must include:

- Referenced architecture contracts
- ADR status (Accepted / pending / not required — with justification)
- Architecture compliance confirmation
- Test coverage summary

If alignment is unclear, stop and ask.

---

## Commit Discipline

- Each commit must be independently buildable and testable
- Commit message follows your project's convention; reference an ADR when one
  applies
- Keep commits focused — split large changes before committing

---

## Authority

Architecture decisions belong to the Architect. Exceptions require an ADR and
explicit approval. Claude follows standards — it does not invent them.

---

## Upgrading to Spec-Driven Add-On (Level 4)

When your team is ready to adopt per-feature spec contracts, upgrade with:

```
govkit apply --level 4 --target <path>
```

Level 4 layers the following on top of Level 3:

- `features/<name>/` directory model with the 5-artifact governed contract
- `/spec-planning`, `/architecture-preflight`, `/implementation-plan` skills
- Test-first and spec-compliance rules (binding, not just recommended)
- Evaluation prediction discipline (FIRST + 7 Virtues, average ≥ 4.0)
- Governance CI jobs: artifact existence, eval-criteria schema, prediction
  thresholds
