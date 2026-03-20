# Angular UI Tech Stack

---

## 1. Core

| Concern | Tool | Version |
|---|---|---|
| Framework | Angular | 17+ |
| Language | TypeScript | 5+ |
| Build | Angular CLI + Vite | 17+ |
| Routing | Angular Router | built-in |

---

## 2. State Management

| Concern | Tool |
|---|---|
| Server state | TanStack Angular Query (`@tanstack/angular-query-experimental`) |
| Client UI state | Angular Signals (built-in since Angular 16+) |
| Form state | Angular Reactive Forms |

See `docs/ui/architecture/angular/STATE_MANAGEMENT.md` for usage rules.

---

## 3. Testing

| Concern | Tool |
|---|---|
| Unit / component tests | Jest + Angular Testing Library (`@testing-library/angular`) |
| Accessibility checks | jest-axe (component) + @axe-core/playwright (E2E) |
| E2E / visual regression | Playwright |
| HTTP mocking in tests | `HttpClientTestingModule` or MSW v2 |

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
| HTTP client | Angular `HttpClient` via shared base service |
| Request/response typing | TypeScript interfaces — no `any` |

No raw `fetch` or `axios`. Use the shared `ApiService` in `src/shared/api/api.service.ts`.

---

## 6. Quality Gates (CI)

| Gate | Tool |
|---|---|
| Type checking | `tsc --noEmit` |
| Linting | ESLint + `@angular-eslint` |
| Component tests | Jest |
| Accessibility | axe-core (zero critical violations) |
| E2E | Playwright |

---

## 7. Governance

| Concern | Location |
|---|---|
| Architecture contract | `docs/ui/architecture/MVVM_CONTRACT.md` |
| Component conventions | `docs/ui/architecture/angular/COMPONENT_CONVENTIONS.md` |
| State management rules | `docs/ui/architecture/angular/STATE_MANAGEMENT.md` |
| Evaluation criteria | `docs/ui/evaluation/eval_criteria.md` |
| ADRs | `docs/ui/architecture/ADR/` |
