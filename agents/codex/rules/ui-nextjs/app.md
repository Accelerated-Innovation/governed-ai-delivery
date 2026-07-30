# Next.js App Router

- Compose routes, layouts, metadata, loading, not-found, and error boundaries.
- Prefer Server Components; justify every `"use client"` boundary.
- Keep feature behavior in `src/features/<feature>/`.
- Route Handlers and Server Actions are thin BFF adapters only.
- No business logic, SQL, database clients, ORMs, migrations, or connection
  strings.
- Never expose secrets or internal tokens to client code.
