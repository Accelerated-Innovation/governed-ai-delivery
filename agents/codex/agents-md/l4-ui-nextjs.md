# Governed AI Delivery — Next.js UI (Level 4)

This is a standalone Next.js UI repository. Architecture, feature artifacts,
backend API contracts, and approved visual direction are binding.

## Required Inputs

Before implementation, read:

- `docs/ui/architecture/nextjs/`
- `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`
- `docs/ui/design/BRAND.md`
- all six files under `features/<feature-name>/`, including `design.md`

Follow this order:

1. `$govkit-ui-architecture-preflight`
2. `$govkit-ui-spec-planning`
3. `$govkit-ui-implementation-plan`
4. Implement one approved vertical increment
5. Verify and report evidence

## Architecture

Use App Router, TypeScript strict mode, Tailwind CSS v4, and server-first
composition. Code responsibilities:

- `src/app/`: routing and composition
- `src/features/<feature>/application/`: use cases and view models
- `src/features/<feature>/api/`: typed backend HTTP access
- `src/features/<feature>/components/`: feature UI
- `src/features/<feature>/types/`: local contracts
- `src/shared/`: reusable primitives and infrastructure

## Non-Waivable Boundary

Business logic and data access belong behind the backend API. Never add direct
SQL, database clients/drivers, ORMs, migrations, schemas, or connection
strings. Route Handlers and Server Actions may be a thin BFF only for session
handling, token protection, protocol adaptation, or limited aggregation.
They never contain business rules. ADRs cannot waive this boundary.

## Server and Client

Server Components are the default. Use Client Components only where browser
capabilities or interactive state require them. Do not expose server secrets,
tokens, or internal API details in client bundles.

## Design and Quality

Implement the approved `BRAND.md` and feature `design.md`. Treat reference
images as advisory. Verify loading, empty, error, success, responsive, keyboard,
focus, and reduced-motion states.

Required gates: typecheck, lint, Vitest, Playwright, accessibility, feature
artifact validation, and API/database boundary enforcement.
