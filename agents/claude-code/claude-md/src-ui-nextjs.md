# `src/` — Next.js UI Source Rules

- `src/app/` owns routing and composition, not domain rules.
- `src/features/<feature>/application/` orchestrates UI use cases.
- `src/features/<feature>/api/` performs typed backend API calls.
- `src/features/<feature>/components/` renders feature UI.
- `src/features/<feature>/types/` owns local contracts.
- `src/shared/` stays feature-neutral.
- Server Components are the default; minimize `"use client"`.
- Never add direct database access, SQL, ORM, migrations, or connection
  strings.
- Never put business rules in Route Handlers or Server Actions.
- Read `docs/ui/architecture/nextjs/` before editing source.
