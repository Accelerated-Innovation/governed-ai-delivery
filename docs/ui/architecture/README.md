# UI Architecture Docs — Layout and Intentional Asymmetry

Repo-side documentation for govkit contributors. This file is **not**
installed into target projects — the agent manifests' `governed` lists name
their entries explicitly, and this README is deliberately not one of them.

## Layout

Shared docs at this level install for every UI project type:

- `MVVM_CONTRACT.md` — layer model for React/Vite and Angular (§1–5) plus
  the Next.js layer mapping (§6)
- `ACCESSIBILITY_STANDARDS.md`
- `NFRS_CONVENTIONS.md`
- `ADR/TEMPLATE.md`

Per-stack folders (`react/`, `angular/`, `nextjs/`) each ship the same core
set, pinned by `tests/test_ui_stack_docs.py`:

- `TECH_STACK.md`
- `COMPONENT_CONVENTIONS.md`
- `STATE_MANAGEMENT.md`
- `STYLING.md`
- `TESTING.md`

## Why `nextjs/` ships more docs than `react/` and `angular/`

Three additional docs are **intentionally nextjs-only** because they govern
server-first App Router concerns that have no equivalent in a client-side
SPA:

- `APPLICATION_STRUCTURE.md` — App Router layout, route files, colocation.
  For react/angular, the equivalent contract is `MVVM_CONTRACT.md` §3
  (Feature Slice Structure); a separate doc would duplicate it.
- `API_BOUNDARY.md` — Server Components, Server Actions, and thin-BFF route
  handlers against the no-database boundary (doctor D016).
- `SERVER_CLIENT_BOUNDARIES.md` — the server/client component split.

Do not "fix" this asymmetry by copying these docs into `react/` or
`angular/`. If a genuinely stack-agnostic concern emerges from one of them,
promote it into a shared doc instead. Decision record:
`plans/UI_DOCS_PARITY_AND_DESIGN_REFERENCES_PLAN.md`.
