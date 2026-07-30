# Governed AI Delivery — Next.js UI (Level 4)

This standalone Next.js UI follows the contracts in
`docs/ui/architecture/nextjs/`. Before implementation, read the approved
`docs/ui/design/BRAND.md`, all six feature artifacts including `design.md`,
and the backend API contract.

Use `/govkit-ui-architecture-preflight`, `/govkit-ui-spec-planning`, and
`/govkit-ui-implementation-plan` before implementing one approved vertical
increment.

Use App Router, strict TypeScript, Tailwind CSS v4, and server-first
composition. `src/app/` composes feature slices. Feature `application/`
orchestrates UI use cases, `api/` performs typed backend HTTP calls,
`components/` renders, and `types/` owns local contracts.

Business logic and data access remain behind the backend API. Never add SQL,
database clients/drivers, ORMs, migrations, schemas, or connection strings.
Route Handlers and Server Actions may only handle session, token protection,
protocol adaptation, or limited aggregation. They contain no domain rules.
An ADR cannot waive this boundary.

Server Components are the default. Client Components require a browser or
interaction justification and must not expose secrets.

Implement the approved brand/design; references are advisory. Verify loading,
empty, error, success, responsive, keyboard, focus, and reduced-motion states.
Pass typecheck, lint, Vitest, Playwright, accessibility, artifact, and
API/database boundary gates.
