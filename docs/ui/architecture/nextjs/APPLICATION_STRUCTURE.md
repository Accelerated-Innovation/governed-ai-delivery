# Next.js Application Structure

This document defines the source layout and dependency direction for a
standalone `ui-nextjs` application.

---

## 1. Reference Layout

```text
src/
├── app/                         # delivery/composition
│   ├── (route-group)/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── loading.tsx
│   │   ├── error.tsx
│   │   └── not-found.tsx
│   └── api/                     # thin BFF Route Handlers only
├── features/
│   └── <feature>/
│       ├── components/          # presentation
│       ├── application/         # UI orchestration, mappers, client hooks
│       ├── api/                 # typed backend API adapters
│       └── types/               # feature-local types
└── shared/
    ├── components/              # approved shared UI primitives
    ├── api/                     # base HTTP/auth/error infrastructure
    ├── accessibility/
    └── types/
```

Route folders compose feature capabilities; they do not become a second
feature implementation tree.

---

## 2. Dependency Direction

| Source | May depend on |
|---|---|
| `app/` | feature public entry points, shared UI |
| feature components | feature application layer, feature types, shared components |
| feature application | feature API adapters, feature types, shared utilities |
| feature API | shared API infrastructure, feature types |
| shared components | shared types and utilities only |
| shared API | environment/auth/transport utilities only |

Forbidden:

- feature internals importing another feature's internals
- shared code importing feature code
- components importing database or backend implementation packages
- route files containing reusable business or transformation logic
- circular feature dependencies

---

## 3. Route Files

`page.tsx` and `layout.tsx` are composition roots. They may:

- read route parameters
- call a feature server-facing application function
- compose Server and Client Components
- declare metadata
- select loading/error/not-found boundaries

They must not:

- contain business rules
- connect to a database
- construct raw backend requests
- accumulate reusable feature logic
- import client-only code into broad server subtrees without need

---

## 4. Feature Public Surface

Each feature exposes a deliberate public entry point. Other routes/features do
not reach into its `components/`, `application/`, or `api/` internals.

Promoting code to `shared/` requires evidence that it is genuinely
cross-feature. A new shared component library or a change to a shared contract
requires an ADR.

---

## 5. Route Groups and Colocation

Route groups may organize authentication, product areas, or layout families
without changing URLs. Route-local files may colocate:

- route composition tests
- route-specific metadata
- loading/error/not-found UI
- non-reusable route helpers

Reusable feature behavior belongs under `features/`.

---

## 6. Generated and Framework Files

Generated clients and framework output must be isolated and excluded from
hand-authored boundary checks where appropriate:

- `.next/`
- `node_modules/`
- coverage and Playwright reports
- generated API clients under a declared generated path

Generated code does not grant permission to introduce database access into the
UI target.
