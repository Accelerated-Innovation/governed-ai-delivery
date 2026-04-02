# UI Tech Stack

---

## 1. Core

| Concern | Tool | Version |
|---|---|---|
| Framework | React | 18+ |
| Language | TypeScript | 5+ |
| Build | Vite | 5+ |
| Routing | React Router | 6+ |

---

## 2. State Management

| Concern | Tool |
|---|---|
| Server state | TanStack React Query v5 |
| Client UI state | Zustand v4 |
| Form state | React Hook Form v7 |

See `STATE_MANAGEMENT.md` for usage rules.

---

## 3. Testing

| Concern | Tool |
|---|---|
| Unit / component tests | Vitest + React Testing Library |
| Accessibility checks | jest-axe (component) + @axe-core/playwright (E2E) |
| E2E / visual regression | Playwright |
| API mocking in tests | MSW (Mock Service Worker) v2 |

---

## 4. Observability

| Concern | Tool |
|---|---|
| Error monitoring | Datadog RUM |
| Performance monitoring | Datadog RUM |
| OpenTelemetry tracing | `@opentelemetry/sdk-web` → Datadog OTLP endpoint |

OpenTelemetry instrumentation lives in `src/shared/observability/`. Features must not instrument themselves directly.

---

## 5. HTTP

| Concern | Tool |
|---|---|
| HTTP client | Native `fetch` via shared base client |
| Request/response typing | TypeScript interfaces — no `any` |

No Axios. Use the shared base client in `src/shared/api/client.ts`.

---

## 6. Quality Gates (CI)

| Gate | Tool |
|---|---|
| Type checking | `tsc --noEmit` |
| Linting | ESLint + `eslint-plugin-react`, `eslint-plugin-jsx-a11y` |
| Component tests | Vitest |
| Accessibility | axe-core (zero critical violations) |
| E2E | Playwright |
| Bundle size | `vite-bundle-analyzer` (advisory, not blocking by default) |

---

## 7. Governance

| Concern | Location |
|---|---|
| Architecture contract | `docs/ui/architecture/MVVM_CONTRACT.md` |
| Component conventions | `docs/ui/architecture/COMPONENT_CONVENTIONS.md` |
| State management rules | `docs/ui/architecture/STATE_MANAGEMENT.md` |
| Evaluation criteria | `docs/ui/evaluation/eval_criteria.md` |
| FIRST scoring rubric | `docs/ui/evaluation/FIRST_SCORING_RUBRIC.md` |
| Virtue scoring rubric | `docs/ui/evaluation/VIRTUE_SCORING_RUBRIC.md` |
| ADRs | `docs/ui/architecture/ADR/` |
