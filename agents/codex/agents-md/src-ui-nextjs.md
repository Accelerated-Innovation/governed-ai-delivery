# `src/` — Next.js UI Source Tree

The root `AGENTS.md` owns lifecycle and cross-cutting governance. This file
maps source responsibilities.

```text
src/
├── app/                         # Routes, layouts, metadata, boundaries
├── features/<feature>/
│   ├── application/             # Use-case orchestration and view models
│   ├── api/                     # Typed backend API calls
│   ├── components/              # Feature UI
│   └── types/                   # Feature-local contracts
└── shared/                      # Reusable UI and infrastructure
```

- Server Components are the default.
- `src/app/` composes features; it does not own domain rules.
- Only `api/` and shared API infrastructure perform backend HTTP calls.
- All business/data access stays behind the backend API.
- No SQL, database dependencies, ORM, migrations, or connection strings.
- `shared/` cannot import from `features/`.
- Features cannot import another feature's internals.

Read `docs/ui/architecture/nextjs/` before editing source.
