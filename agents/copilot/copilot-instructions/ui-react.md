---
applyTo: "**"
---
# GitHub Copilot Instructions — Foundations (Level 3) — React UI

These instructions govern how GitHub Copilot plans, reasons, and generates
code in this React UI repository. They are mandatory.

Copilot must treat this repository as a governed delivery system, not an open
coding environment. Repository artifacts are the source of truth. Chat memory
is not.

> **Feature artifacts are not part of L3.** If your team adopts spec-driven
> feature delivery (per-feature `acceptance.feature`, `nfrs.md`, `plan.md`,
> `eval_criteria.yaml`, and `architecture_preflight.md`), upgrade with
> `govkit apply --level 4`.

---

## 1. Operating Mode

Copilot operates aligned to:

* Architecture contracts under `docs/ui/architecture/`
* Path-scoped instructions under `.github/instructions/govkit/`

Before generating or modifying code:

* Read the MVVM contract, component conventions, and state management rules
* Apply layer-boundary rules and accessibility standards as binding constraints

If required inputs are missing or unclear, stop and ask.

---

## 2. MVVM Architecture

This project follows MVVM with a vertical slice source-code structure under
`src/`. Note: `src/features/` is the React source tree (not the govkit
`features/` directory, which only exists at Level 4+).

```
src/
├── features/<slice>/
│   ├── components/   # View — pure React components
│   ├── hooks/        # ViewModel — React Query hooks
│   ├── store/        # ViewModel — Zustand client state
│   ├── api/          # Model — API client functions
│   └── types/        # Slice-local TypeScript types
├── shared/
│   ├── components/   # Shared UI primitives only
│   └── api/          # Base API config, auth headers
└── app/              # Entry point, routing, providers
```

Read before generating any code:

* `docs/ui/architecture/MVVM_CONTRACT.md`
* `docs/ui/architecture/react/COMPONENT_CONVENTIONS.md`
* `docs/ui/architecture/react/STATE_MANAGEMENT.md`
* `docs/ui/architecture/react/TECH_STACK.md`
* `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`

---

## 3. Layer Rules

### View — Components (`src/features/<slice>/components/`)

* No direct API calls. No fetch. No axios.
* No business logic or data transformation
* Receive data and callbacks via props or hooks only
* All data via React Query hooks or Zustand selectors
* See `.github/instructions/govkit/components.instructions.md`

### ViewModel — Hooks (`src/features/<slice>/hooks/`)

* All server state via React Query (`useQuery`, `useMutation`)
* One hook file per logical data concern
* Transform API responses here — never in components
* See `.github/instructions/govkit/viewmodel.instructions.md`

### ViewModel — Store (`src/features/<slice>/store/`)

* Zustand for client-only UI state (modals, selections, pagination)
* Never store server data in Zustand — that belongs in React Query cache
* Slice-scoped stores only — no global catch-all store

### Model — API (`src/features/<slice>/api/`)

* Plain async functions — no React, no hooks
* One file per backend resource
* Use shared base client from `src/shared/api/`
* See `.github/instructions/govkit/api.instructions.md`

### Accessibility

* Every interactive component must meet WCAG 2.1 AA
* See `.github/instructions/govkit/accessibility.instructions.md` and
  `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md`

---

## 4. Boundary Rules

These are hard constraints. Never violate without an accepted ADR.

* Components must not import from `api/` directly
* Components must not import from another slice's internals
* Zustand stores must not call API functions directly — use React Query
  mutations
* `shared/` must not import from `features/`
* No business logic outside `hooks/` and `api/`

---

## 5. Implementation Rules

* Respect all boundary rules above
* Follow MVVM separation strictly
* Test-first is recommended for new components; the binding test-first rule
  is part of the Level 4 Spec-Driven Add-On
* Accessibility checks are part of every change, not a separate phase

---

## 6. ADR Required For

* Adding a new state management library
* Introducing a new shared component library
* Changing the API client strategy
* Cross-slice state dependencies
* Any deviation from the MVVM layer boundaries
* Changes to authentication or authorization patterns

ADRs live under `docs/ui/architecture/ADR/`. Use the `/govkit-adr-author` skill to
scaffold a new ADR.

---

## 7. Testing Requirements

Each change must include:

* Component tests with Vitest + React Testing Library (FIRST compliant)
* Accessibility checks via axe-core (zero critical violations)
* Integration tests when crossing layer boundaries

---

## 8. Output Expectations

Every implementation output must include:

* Referenced architecture contracts
* ADR status (Accepted / pending / not required — with justification)
* Layer-boundary compliance confirmation
* Test coverage summary including accessibility

If alignment is unclear, stop and ask.

---

## 9. Commit Discipline

* Each commit must be independently buildable and testable
* Commit message follows your project's convention; reference an ADR when one
  applies
* Keep commits focused — split large changes before committing

---

## 10. Upgrading to Spec-Driven Add-On (Level 4)

When your team is ready to adopt per-feature spec contracts, upgrade with:

```
govkit apply --type ui-react --level 4 --target <path>
```

Level 4 layers the following on top of Level 3:

* `features/<name>/` directory model with the 5-artifact governed contract
  (separate from `src/features/`)
* `/govkit-ui-spec-planning`, `/govkit-ui-architecture-preflight`, `/govkit-ui-implementation-plan`
  skills
* Test-first and spec-compliance instructions (binding, not just recommended)
* Evaluation prediction discipline including accessibility, FIRST, and 7
  Virtues
* Governance CI jobs: artifact existence, eval-criteria schema, prediction
  thresholds
