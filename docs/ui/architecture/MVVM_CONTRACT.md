# UI Architecture Contract

This document defines the shared architectural boundary for all UI projects
governed by this kit. React/Vite and Angular use the MVVM layer model below.
Next.js uses the server-first API-first layered model in
`docs/ui/architecture/nextjs/`. Framework-specific architecture rules take
precedence when they are more specific.

For framework-specific implementation rules see:
- React: `docs/ui/architecture/react/`
- Angular: `docs/ui/architecture/angular/`
- Next.js: `docs/ui/architecture/nextjs/`

---

## 1. React/Vite and Angular Layer Model

```
┌─────────────────────────────────────┐
│           View (Components)          │  src/features/*/components/
│   Pure render — no logic, no fetch   │  src/shared/components/
└──────────────┬──────────────────────┘
               │ props / data from ViewModel
┌──────────────▼──────────────────────┐
│            ViewModel                 │  src/features/*/hooks/   (server state)
│   Server state — query layer         │  src/features/*/store/   (client state)
│   Client UI state — store layer      │
└──────────────┬──────────────────────┘
               │ async function calls
┌──────────────▼──────────────────────┐
│           Model (API Layer)          │  src/features/*/api/
│   Plain async functions, typed I/O   │  src/shared/api/
└──────────────┬──────────────────────┘
               │ HTTP
┌──────────────▼──────────────────────┐
│         Backend API (Hexagonal)      │  External — not owned by this repo
└─────────────────────────────────────┘
```

---

## 2. Allowed Dependencies

| Layer | May import from |
|---|---|
| View (components) | ViewModel layer, shared components, types |
| ViewModel (query layer) | API layer, shared API config, types |
| ViewModel (store layer) | Types only — never API layer directly |
| Model (API) | Shared base client, types |
| Shared components | Types only — no feature imports |
| Shared API | Environment config only |

### Forbidden

- View importing from `api/` directly → never
- View importing from another feature's internals → never
- Store calling API functions directly → never (use the query layer's mutation mechanism)
- `shared/` importing from `features/` → never
- Circular dependencies between features → never

---

## 3. Feature Slice Structure

Every feature is self-contained:

```
src/features/<feature-name>/
├── components/     # View
├── hooks/          # ViewModel — server state (query layer)
├── store/          # ViewModel — client state (if needed)
├── api/            # Model
└── types/          # Feature-local TypeScript types
```

Cross-feature imports are forbidden. If two features need to share something, it moves to `src/shared/` via ADR.

---

## 4. State Ownership

| State type | Owner | Framework tool |
|---|---|---|
| Server data (API responses) | Query layer cache | React: React Query / Angular: TanStack Angular Query |
| Client UI state (modals, tabs, selections) | Store layer | React: Zustand / Angular: Angular Signals |
| Form state | Component or form library | React: React Hook Form / Angular: Reactive Forms |
| URL state (filters, pagination) | URL params | React: `useSearchParams` / Angular: `ActivatedRoute` |

Never duplicate server data into the client state store. Never put UI-only state into the query layer cache.

---

## 5. Backend Boundary

The UI owns nothing in the backend. All UI variants consume backend-owned API
contracts. Direct database access, ORM or database-driver dependencies, SQL,
migrations, and connection strings are forbidden in UI repositories.

If a required endpoint does not exist, stop UI implementation for that
capability and negotiate the API contract with the backend owner. An ADR may
document the agreed integration shape, but an ADR cannot waive the database
boundary.

## 6. Next.js Layer Mapping

Next.js is not forced into client-side MVVM terminology. Its equivalent
responsibilities are:

| Responsibility | Next.js location |
|---|---|
| Composition and routing | `src/app/` |
| Feature UI | `src/features/<feature>/components/` |
| Use-case orchestration and view models | `src/features/<feature>/application/` |
| Typed backend API access | `src/features/<feature>/api/` |
| Feature contracts | `src/features/<feature>/types/` |
| Reusable primitives and infrastructure | `src/shared/` |

Server Components are the default composition boundary. Client Components are
used only where browser APIs or interaction require them. Route Handlers and
Server Actions may form a thin BFF for session handling, token protection,
protocol adaptation, or limited response aggregation; they may not contain
domain rules or access a database.
