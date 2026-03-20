# MVVM Architecture Contract — React UI

This document defines the architectural contract for all React UI projects governed by this kit. All violations require an accepted ADR.

---

## 1. Layer Model

```
┌─────────────────────────────────────┐
│           View (Components)          │  src/features/*/components/
│   Pure render — no logic, no fetch   │  src/shared/components/
└──────────────┬──────────────────────┘
               │ props / hook return values
┌──────────────▼──────────────────────┐
│         ViewModel (Hooks + Store)    │  src/features/*/hooks/
│  React Query — server state          │  src/features/*/store/
│  Zustand — client UI state           │
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
| View (components) | ViewModel hooks, shared components, types |
| ViewModel (hooks) | API layer, shared API config, types |
| ViewModel (store) | Types only — never API layer directly |
| Model (API) | Shared base client, types |
| Shared components | Types only — no feature imports |
| Shared API | Environment config only |

### Forbidden

- View importing from `api/` directly → never
- View importing from another feature's internals → never
- Store calling API functions → never (use React Query mutations)
- `shared/` importing from `features/` → never
- Circular dependencies between features → never

---

## 3. Feature Slice Structure

Every feature is self-contained:

```
src/features/<feature-name>/
├── components/     # View
├── hooks/          # ViewModel — server state
├── store/          # ViewModel — client state (if needed)
├── api/            # Model
└── types/          # Feature-local TypeScript types
```

Cross-feature imports are forbidden. If two features need to share something, it moves to `src/shared/` via ADR.

---

## 4. State Ownership

| State type | Owner | Tool |
|---|---|---|
| Server data (API responses) | React Query cache | `useQuery` / `useMutation` |
| Client UI state (modals, tabs, selections) | Zustand store | Feature-scoped store |
| Form state | Local component state or React Hook Form | `useState` / `useForm` |
| URL state (filters, pagination) | URL params | `useSearchParams` |

Never duplicate server data into Zustand. Never put UI-only state into React Query.

---

## 5. Backend Boundary

The UI owns nothing in the backend. The API layer is read-only from the UI's perspective — it consumes contracts defined by the backend team. If a required endpoint does not exist, an ADR is required to negotiate and document the contract before UI implementation begins.
