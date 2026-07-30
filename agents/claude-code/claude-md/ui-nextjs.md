# Governed AI Delivery — Foundations (Level 3) — Next.js UI

You are operating inside a standalone governed Next.js UI project. Repository
contracts are authoritative.

> **Feature artifacts are not part of L3.** Adopt spec-driven delivery with
> `govkit apply --level 4 --type ui-nextjs --target <path>`.

## Architecture

Use server-first App Router composition and feature slices:

```text
src/app/                         # routing and composition
src/features/<feature>/application/
src/features/<feature>/api/
src/features/<feature>/components/
src/features/<feature>/types/
src/shared/
```

Read `docs/ui/architecture/nextjs/`,
`docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`, and
`docs/ui/design/BRAND.md` before code.

Server Components are the default. Use `"use client"` only for browser APIs
or interaction, and keep the boundary small.

## API and Database Boundary

All business capability is consumed through a backend-owned API. Never add
SQL, database clients/drivers, ORMs, migrations, schemas, or connection
strings. Never place domain rules in Next.js server code. Route Handlers and
Server Actions may be a thin BFF only for session handling, token protection,
protocol adaptation, or limited aggregation. This boundary is not waivable by
ADR.

If an endpoint is missing, stop that capability and report the API contract
gap.

## Layer Rules

- `app/` composes; `application/` orchestrates UI use cases.
- `api/` owns typed backend HTTP access and transport-error mapping.
- `components/` renders feature UI.
- `shared/` remains feature-neutral.
- Features do not import another feature's internals.
- Secrets and server tokens never enter client bundles.

## Design and Testing

Follow semantic Tailwind v4 tokens from the approved brand. Screenshots and
mockups are advisory unless promoted in an approved feature design.
Accessibility and accepted behavior take precedence.

Require strict typecheck, lint, Vitest, Playwright for server-rendered and
user-visible flows, and WCAG 2.1 AA with zero critical or serious axe
violations.

## ADR Required For

- New shared UI or state-management libraries
- Material server/client boundary changes
- New thin-BFF responsibilities
- Cross-feature coupling
- Material auth or API-client changes

Database access is never an ADR option.

## Output Expectations

Report contracts used, server/client choices, API-boundary compliance, ADR
status, and test/accessibility evidence.

## Upgrading to Spec-Driven Add-On (Level 4)

```text
govkit apply --level 4 --type ui-nextjs --target <path>
```

Level 4 adds the six-artifact feature workflow, planning skills, test-first
rules, design review, and governance gates.
