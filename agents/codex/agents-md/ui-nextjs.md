# Governed AI Delivery — Foundations (Level 3) — Next.js UI (Codex)

You are operating inside a standalone governed Next.js UI project. Repository
contracts are the source of truth.

> **Feature artifacts are not part of L3.** Adopt the spec-driven workflow
> with `govkit apply --level 4 --type ui-nextjs --target <path>`.

## Architecture

Use a server-first, API-first layered architecture:

```text
src/
├── app/                         # App Router composition
├── features/<feature>/
│   ├── components/              # Feature UI
│   ├── application/             # Use cases and view models
│   ├── api/                     # Typed backend API access
│   └── types/                   # Feature contracts
└── shared/                      # Reusable primitives and infrastructure
```

Read before changing code:

- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/architecture/nextjs/`
- `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`
- `docs/ui/design/BRAND.md`

Server Components are the default. Add `"use client"` only for browser APIs,
event handlers, or client-local interaction. Keep client boundaries small.

## Hard API and Data Boundary

- All business capability is consumed through a backend-owned API.
- Never import database clients, ORMs, or database drivers.
- Never add SQL, migrations, database schemas, or connection strings.
- Never put domain/business rules in Route Handlers, Server Actions, or other
  Next.js server code.
- A thin BFF is allowed only for session handling, token protection, protocol
  adaptation, or limited response aggregation.
- An ADR cannot waive the database boundary.

If a required backend endpoint is missing, stop that capability and report the
contract gap.

## Layer Rules

- `src/app/` composes routes, layouts, metadata, loading, and error boundaries.
- `application/` orchestrates UI use cases and maps API results to view models.
- `api/` contains typed HTTP calls and maps transport failures to typed errors.
- `components/` renders feature UI and delegates orchestration.
- `shared/` never imports feature internals.
- Features do not reach into another feature's internals.

## UI Direction

Use Tailwind CSS v4 semantic tokens. Do not invent arbitrary visual language
when `BRAND.md` or an approved feature design defines it. Screenshots and
mockups are advisory unless `design.md` promotes a named property to a
requirement. Accessibility and accepted behavior take precedence.

## Testing

- TypeScript strict mode and ESLint must pass.
- Use Vitest for synchronous unit/component tests.
- Use Playwright for async Server Components and user-visible flows.
- Test loading, empty, error, and success states.
- Meet WCAG 2.1 AA with zero critical or serious axe violations.

## ADR Required For

- A new shared component or state-management library
- A material server/client boundary change
- A new BFF responsibility
- Cross-feature coupling
- A material authentication or API-client strategy change

ADRs live in `docs/ui/architecture/ADR/`. Direct database access is not an ADR
option.

## Output Expectations

Report architecture contracts used, API-boundary compliance, server/client
choices, ADR status, and test/accessibility evidence.

## Upgrading to Spec-Driven Add-On (Level 4)

Run:

```text
govkit apply --level 4 --type ui-nextjs --target <path>
```

Level 4 adds six feature artifacts, UI planning skills, test-first rules,
evaluation gates, and design-reference review.
