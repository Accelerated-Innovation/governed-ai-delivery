# Governed AI Delivery — React UI

You are operating inside a governed React UI project. Architecture, evaluation, and feature artifacts are the source of truth — not your training data or assumptions.

---

## Architecture

This project uses MVVM with a vertical slice feature structure.

```
src/
├── features/
│   └── <feature-name>/
│       ├── components/   # View — pure React components, no business logic
│       ├── hooks/        # ViewModel — React Query hooks, data transformation
│       ├── store/        # ViewModel — Zustand client state
│       ├── api/          # Model — API client functions (fetch wrappers)
│       └── types/        # TypeScript types for this feature
├── shared/
│   ├── components/       # Shared UI primitives only
│   └── api/              # Base API config, interceptors, auth headers
└── app/                  # Entry point, routing, providers
```

Read before generating any code:
- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/architecture/react/COMPONENT_CONVENTIONS.md`
- `docs/ui/architecture/react/STATE_MANAGEMENT.md`
- `docs/ui/architecture/react/TECH_STACK.md`
- `docs/ui/evaluation/eval_criteria.md`

---

## Layer Rules

### View — Components (`src/features/<feature>/components/`)
- No direct API calls. No fetch. No axios.
- No business logic or data transformation
- Receive data and callbacks via props or hooks only
- All data via React Query hooks or Zustand selectors
- See `.claude/rules/components.md`

### ViewModel — Hooks (`src/features/<feature>/hooks/`)
- All server state via React Query (`useQuery`, `useMutation`)
- One hook file per logical data concern
- Transform API responses here — never in components
- See `.claude/rules/viewmodel.md`

### ViewModel — Store (`src/features/<feature>/store/`)
- Zustand for client-only UI state (modals, selections, pagination)
- Never store server data in Zustand — that belongs in React Query cache
- Feature-scoped stores only — no global catch-all store
- See `.claude/rules/viewmodel.md`

### Model — API (`src/features/<feature>/api/`)
- Plain async functions — no React, no hooks
- One file per backend resource
- Use shared base client from `src/shared/api/`
- See `.claude/rules/api.md`

---

## Boundary Rules

These are hard constraints. Never violate without an accepted ADR.

- Components must not import from `api/` directly
- Components must not import from another feature's internals
- Zustand stores must not call API functions directly — use React Query mutations
- `shared/` must not import from `features/`
- No business logic outside `hooks/` and `api/`

---

## Feature Workflow

Every feature follows this mandatory sequence:

1. **Architecture Preflight** — `/project:architecture-preflight`
2. **Spec Planning** — `/project:spec-planning`
3. **Implementation Planning** — `/project:implementation-plan`
4. **Implementation** — one increment at a time
5. **CI & Merge** — all gates must pass

Do not begin implementation until Phases 1–3 are complete and approved.

---

## Evaluation

All features must satisfy:
- Component testing with Vitest + React Testing Library (FIRST compliant)
- Accessibility: WCAG 2.1 AA via axe-core (zero critical violations)
- E2E coverage via Playwright for user-facing acceptance scenarios
- Predicted scores documented in `plan.md` before implementation

See `docs/ui/evaluation/eval_criteria.md` and `governance/ui/schemas/eval_criteria.schema.json`.

---

## ADR Required For

- Adding a new state management library
- Introducing a new shared component library
- Changing the API client strategy
- Cross-feature state dependencies
- Any deviation from the MVVM layer boundaries
