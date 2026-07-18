# Governed AI Delivery — Foundations (Level 3) — Angular UI (Codex)

You are operating inside a governed Angular UI project. Architecture contracts
are the source of truth — not your training data or assumptions.

> **Feature artifacts are not part of L3.** If your team adopts spec-driven
> feature delivery (per-feature `acceptance.feature`, `nfrs.md`, `plan.md`,
> `eval_criteria.yaml`, and `architecture_preflight.md`), upgrade with
> `govkit apply --level 4`.

---

## Architecture

This project uses MVVM with a vertical slice source-code structure under
`src/`. Note: `src/features/` is the Angular source tree (not the govkit
`features/` directory, which only exists at Level 4+).

```
src/
├── features/
│   └── <slice-name>/
│       ├── components/   # View — standalone Angular components, OnPush
│       ├── hooks/        # ViewModel — TanStack Query inject functions
│       ├── store/        # ViewModel — Angular Signal stores
│       ├── api/          # Model — HttpClient wrapper functions
│       └── types/        # TypeScript types for this slice
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
- `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`

---

## Layer Rules

Layer-specific rules load automatically via nested `AGENTS.md` files when
working in each layer:

- `src/features/components/AGENTS.md` — View layer (standalone components)
- `src/features/hooks/AGENTS.md` — ViewModel (TanStack Query + Signal stores)
- `src/features/api/AGENTS.md` — Model layer (HttpClient wrappers)
- `src/shared/accessibility/AGENTS.md` — WCAG 2.1 AA requirements

### View — Components (`src/features/<slice>/components/`)

- Standalone components with `ChangeDetectionStrategy.OnPush` — always
- No direct `HttpClient` calls or API service injections
- No business logic or data transformation in component class or template
- All server data via TanStack Query inject functions
- All client state via Signal store injection
- Use `@if`, `@for`, `@switch` control flow (Angular 17+)

### ViewModel — Query Functions (`src/features/<slice>/hooks/`)

- All server state via TanStack Angular Query (`injectQuery`, `injectMutation`)
- Transform API responses in `select` — never in templates or components
- Query keys defined as typed constants in `query-keys.ts` per slice
- Mutations must invalidate relevant query keys on success

### ViewModel — Signal Store (`src/features/<slice>/store/`)

- Angular Signals for UI-only state — modals, active tab, pagination,
  selections
- Never store server data — use TanStack Query cache
- Expose read-only signals via `.asReadonly()`
- Never call API services directly from a store

### Model — API (`src/features/<slice>/api/`)

- Plain functions wrapping `HttpClient`
- One file per backend resource
- Use shared base from `src/shared/api/`

### Accessibility

- Every interactive component must meet WCAG 2.1 AA
- See `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`

---

## Boundary Rules

These are hard constraints. Never violate without an accepted ADR.

- Components must not import from `api/` directly
- Components must not import from another slice's internals
- Signal stores must not call API services directly — use TanStack mutations
- `shared/` must not import from `features/`
- No business logic outside `hooks/` and `api/`

---

## Implementation Rules

- Respect all boundary rules above
- Follow MVVM separation strictly
- Test-first is recommended for new components; the binding test-first rule
  is part of the Level 4 Spec-Driven Add-On
- Accessibility checks are part of every change, not a separate phase

---

## ADR Required For

- Adding a new state management library
- Introducing a new shared component library
- Changing the API client strategy
- Cross-slice state dependencies
- Any deviation from the MVVM layer boundaries
- Changes to authentication or authorization patterns

ADRs live under `docs/ui/architecture/ADR/`. Invoke `$govkit-adr-author` to scaffold
a new ADR.

---

## Testing Requirements

Each change must include:

- Component tests with Karma/Jasmine or Jest (FIRST compliant)
- Accessibility checks via axe-core (zero critical violations)
- Integration tests when crossing layer boundaries

---

## Output Expectations

Every implementation output must include:

- Referenced architecture contracts
- ADR status (Accepted / pending / not required — with justification)
- Layer-boundary compliance confirmation
- Test coverage summary including accessibility

If alignment is unclear, stop and ask.

---

## Commit Discipline

- Each commit must be independently buildable and testable
- Commit message follows your project's convention; reference an ADR when one
  applies
- Keep commits focused — split large changes before committing

---

## Upgrading to Spec-Driven Add-On (Level 4)

When your team is ready to adopt per-feature spec contracts, upgrade with:

```
govkit apply --type ui-angular --level 4 --target <path>
```

Level 4 layers the following on top of Level 3:

- `features/<name>/` directory model with the 5-artifact governed contract
  (separate from `src/features/`)
- `$govkit-ui-spec-planning`, `$govkit-ui-architecture-preflight`, `$govkit-ui-implementation-plan`
  skills
- Test-first and spec-compliance rules (binding, not just recommended)
- Evaluation prediction discipline including accessibility, FIRST, and 7
  Virtues
- Governance CI jobs: artifact existence, eval-criteria schema, prediction
  thresholds
