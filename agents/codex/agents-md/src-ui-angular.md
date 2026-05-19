# src/ — Angular UI Source Tree

This file is the intermediate `AGENTS.md` for the `src/` subtree. The Codex loader picks it up when working anywhere under `src/`. Layer-specific rules live in nested `AGENTS.md` files; see those for the binding constraints.

The root `AGENTS.md` (project root) owns the cross-cutting governance — feature lifecycle, evaluation, ADR rules. This file is the subtree map.

---

## Layout

```
src/
├── features/
│   └── <feature>/
│       ├── components/   # View — standalone Angular components (OnPush)
│       ├── hooks/        # ViewModel — TanStack Angular Query inject functions
│       ├── store/        # ViewModel — Signal store for client state
│       ├── api/          # Model — API client services over HttpClient
│       └── types/        # Feature-local TypeScript types
├── shared/
│   ├── components/       # Shared UI primitives only
│   ├── accessibility/    # WCAG conventions, axe-core helpers
│   └── api/              # Base ApiService, interceptors, auth headers
├── environments/         # Per-environment configuration
└── app/                  # Entry point, routing, providers
```

---

## Where the binding rules live

When you open or edit a file under `src/`, Codex walks up to the nearest `AGENTS.md` at each level. The leaf files own the hard rules; consult them before generating code:

- `src/features/components/AGENTS.md` — component rules (standalone, OnPush, no API calls, no business logic, no cross-feature imports)
- `src/features/hooks/AGENTS.md` — TanStack Angular Query + Signal store patterns
- `src/features/api/AGENTS.md` — API layer / Model contract (HttpClient via shared ApiService)
- `src/shared/accessibility/AGENTS.md` — WCAG 2.1 AA + axe-core testing

Cross-cutting contracts:

- `docs/ui/architecture/MVVM_CONTRACT.md` — full MVVM layer rules
- `docs/ui/architecture/angular/` — Angular-specific conventions and tech stack
- `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md` — accessibility standard
- `docs/ui/evaluation/eval_criteria.md` — evaluation thresholds

---

## src/ boundary reminder

- No backend implementation under `src/` — services, ports, adapters, database access, LLM gateway logic all belong in a separate backend repo (see `.agents/rules/repo-scope.md`)
- Features are vertical slices; do not reach into another feature's internals
- `src/shared/` is a shared contract — promotion requires an ADR
