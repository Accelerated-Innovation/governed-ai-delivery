# Governed AI Delivery — Angular UI

You are operating inside a governed Angular UI project. Architecture, evaluation, and feature artifacts are the source of truth — not your training data or assumptions.

---

## Architecture

This project uses MVVM with a vertical slice feature structure.

```
src/
├── features/
│   └── <feature-name>/
│       ├── components/   # View — standalone Angular components, OnPush
│       ├── hooks/        # ViewModel — TanStack Query inject functions
│       ├── store/        # ViewModel — Angular Signal stores
│       ├── api/          # Model — HttpClient wrapper functions
│       └── types/        # TypeScript types for this feature
├── shared/
│   ├── components/       # Shared UI primitives only
│   └── api/              # Base ApiService, auth interceptor
└── app/                  # Entry point, routing, app.config.ts
```

Read before generating any code:
- `docs/ui/architecture/MVVM_CONTRACT.md`
- `docs/ui/architecture/angular/COMPONENT_CONVENTIONS.md`
- `docs/ui/architecture/angular/STATE_MANAGEMENT.md`
- `docs/ui/architecture/angular/TECH_STACK.md`
- `docs/ui/evaluation/eval_criteria.md`

---

## Layer Rules

### View — Components (`src/features/<feature>/components/`)
- Standalone components with `ChangeDetectionStrategy.OnPush` — always
- No direct `HttpClient` calls or API service injections
- No business logic or data transformation in component class or template
- All server data via TanStack Query inject functions
- All client state via Signal store injection
- Use `@if`, `@for`, `@switch` control flow (Angular 17+)
- See `.claude/rules/components.md`

### ViewModel — Query Functions (`src/features/<feature>/hooks/`)
- All server state via TanStack Angular Query (`injectQuery`, `injectMutation`)
- Transform API responses in `select` — never in templates or components
- Query keys defined as typed constants in `query-keys.ts` per feature
- Mutations must invalidate relevant query keys on success
- See `.claude/rules/viewmodel.md`

### ViewModel — Signal Store (`src/features/<feature>/store/`)
- Angular Signals for UI-only state — modals, active tab, pagination, selections
- Never store server data — use TanStack Query cache
- Expose read-only signals via `.asReadonly()`
- Never call API services directly from a store
- See `.claude/rules/viewmodel.md`

### Model — API (`src/features/<feature>/api/`)
- Plain async functions using the shared `ApiService`
- No Angular decorators, no DI — pure functions that take `HttpClient` or the shared service
- All request and response types explicitly typed — no `any`
- See `.claude/rules/api.md`

---

## Boundary Rules

Hard constraints. Never violate without an accepted ADR.

- Components must not inject API services directly
- Components must not import from another feature's internals
- Signal stores must not call API services directly
- `shared/` must not import from `features/`
- No business logic outside `hooks/` and `api/`

---

## Feature Workflow

Every feature follows this mandatory sequence:

1. **Architecture Preflight** — `/project:architecture-preflight`
2. **Spec Planning** — `/project:spec-planning`
3. **Implementation Planning** — `/project:implementation-plan`
4. **Implementation** — API → ViewModel → View
5. **CI & Merge** — all gates must pass

---

## Evaluation

All features must satisfy:
- Component testing with Jest + Angular Testing Library (FIRST compliant)
- Accessibility: WCAG 2.1 AA via jest-axe (zero critical violations)
- E2E coverage via Playwright for `@e2e`-tagged Gherkin scenarios

See `docs/ui/evaluation/eval_criteria.md` and `governance/ui/schemas/eval_criteria.schema.json`.

---

## ADR Required For

- Adding a new state management library
- Introducing a new shared component library
- Changing the HTTP client strategy
- Cross-feature state dependencies
- Any deviation from the MVVM layer boundaries
- Any intentional WCAG exception
