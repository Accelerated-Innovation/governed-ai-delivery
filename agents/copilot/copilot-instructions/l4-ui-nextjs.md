---
applyTo: "**"
---
# GitHub Copilot Instructions — Next.js UI (Level 4)

Read `docs/ui/architecture/nextjs/`, `docs/ui/design/BRAND.md`, the six feature
artifacts including `design.md`, and the backend API contract before code.
Complete UI architecture, spec, and implementation planning first.

Use server-first App Router feature slices. `app/` composes; `application/`
orchestrates UI use cases; `api/` performs typed backend HTTP; `components/`
renders; `types/` owns feature contracts.

All business logic and data access stay behind the backend API. Never generate
SQL, database clients/drivers, ORMs, migrations, schemas, or connection
strings. Route Handlers and Server Actions are thin session/token/protocol/
aggregation adapters only. They contain no domain rules. No ADR waives this.

Prefer Server Components, minimize client islands, and protect secrets. Follow
the approved brand/design; references remain advisory. Test loading, empty,
error, success, responsive, keyboard, focus, and reduced-motion states. Pass
typecheck, lint, Vitest, Playwright, accessibility, artifact, and API/database
boundary gates.
