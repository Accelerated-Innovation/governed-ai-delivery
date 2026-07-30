# Next.js UI Tech Stack

This contract defines the approved baseline for a standalone `ui-nextjs`
project. Review version ranges during calibration; do not replace them with
unbounded `latest` dependencies.

---

## 1. Core

| Concern | Baseline |
|---|---|
| Runtime | Node.js 20.9+ |
| Framework | Next.js 16.x |
| UI library | React 19.x |
| Language | TypeScript 5.x, strict mode |
| Router | Next.js App Router |
| Build/dev | Next.js with Turbopack defaults |
| Styling | Tailwind CSS 4.x |

App Router is required. Pages Router requires an accepted ADR and a replacement
contract for every App Router rule that no longer applies.

---

## 2. Architecture

The application is a server-first, API-first layered UI:

- `src/app/` owns routes, layouts, metadata, and composition.
- Server Components are the default.
- Client Components are narrow interactive islands.
- `src/features/<feature>/application/` owns UI orchestration and view-data
  mapping.
- `src/features/<feature>/api/` owns typed access to the backend business API.
- The backend API owns business rules and database access.

Read:

- `APPLICATION_STRUCTURE.md`
- `SERVER_CLIENT_BOUNDARIES.md`
- `API_BOUNDARY.md`

---

## 3. Styling

| Concern | Baseline |
|---|---|
| CSS framework | Tailwind CSS 4.x |
| PostCSS integration | `@tailwindcss/postcss` |
| Theme source | semantic CSS variables mapped from `docs/ui/design/BRAND.md` |
| Class composition | `clsx` + `tailwind-merge`, or calibrated equivalents |

The global stylesheet is allowed for the Tailwind import, semantic theme
variables, narrowly scoped resets, font declarations, and global primitives.
Feature-specific styling belongs with feature components.

---

## 4. Data and State

| State | Owner |
|---|---|
| Initial/backend data | Server Component through a typed API adapter |
| Client-refreshed data | TanStack React Query only when justified |
| URL state | App Router search params and route segments |
| Forms | native/server form patterns or React Hook Form when client complexity warrants it |
| Local interaction | React component state |
| Cross-component UI state | a calibrated client store only when props/URL state are insufficient |

React Query is not the default for data already fetched during server
rendering. See `STATE_MANAGEMENT.md`.

---

## 5. Testing

| Concern | Baseline |
|---|---|
| Unit/client component | Vitest + React Testing Library |
| HTTP boundary mocking | MSW or adapter-level fakes |
| Accessibility | axe-core in component and Playwright flows |
| E2E | Playwright |
| Async Server Components | Playwright/integration coverage |
| Visual comparison | Playwright, approved screens only |

See `TESTING.md`.

---

## 6. HTTP and Business API

Use native `fetch` behind typed feature/shared API adapters. UI components,
pages, Server Actions, and Route Handlers do not construct business API
requests ad hoc.

No database drivers, ORMs, SQL, migrations, or database connections are
permitted in this project type. See `API_BOUNDARY.md`.

---

## 7. Quality Script Contract

Projects calibrate package-manager details but expose these behaviors:

| Script | Required behavior |
|---|---|
| `typecheck` | TypeScript check without emitting |
| `lint` | ESLint with zero warnings |
| `test:ci` | deterministic unit/component test run |
| `build` | production `next build` |
| `start:ci` | production server on the configured Playwright port |
| `test:e2e` | Playwright E2E suite |

`next build` does not replace the explicit lint step.

---

## 8. Primary References

- <https://nextjs.org/docs/app>
- <https://nextjs.org/docs/app/getting-started/installation>
- <https://tailwindcss.com/docs/installation/framework-guides/nextjs>
