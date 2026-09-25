---
paths:
  - "src/**"
---
# UI Layer Rules — Angular (src/)

This file consolidates the Angular UI layer rules. Claude Code loads it automatically when editing files under `src/`. Rules below apply on top of the root govkit governance (`.claude/rules/govkit/governance.md`).

Source-of-truth contracts live in `docs/ui/architecture/` and `docs/ui/architecture/angular/` — this file is the inline-loadable summary.

---

## Architecture (Recap)

This project uses MVVM with a vertical slice feature structure under `src/`:

- `src/features/<feature>/components/` — View (standalone Angular components, OnPush)
- `src/features/<feature>/hooks/` — ViewModel (TanStack Angular Query inject functions)
- `src/features/<feature>/store/` — ViewModel (Signal store for client state)
- `src/features/<feature>/api/` — Model (API client functions over `HttpClient`)
- `src/features/<feature>/types/` — TypeScript types for this feature
- `src/shared/components/` — Shared UI primitives only
- `src/shared/api/` — Base `ApiService`, interceptors, auth headers

---

## Components — `src/features/*/components/`, `src/shared/components/`

See `docs/ui/architecture/angular/COMPONENT_CONVENTIONS.md` for full guidance and code examples (Section 8).

### Hard Rules

- **Standalone only** — no `NgModule` declarations
- **OnPush detection** — always required
- **No direct API calls** — use query functions (e.g., `injectUserProfile`)
- **No data transformation** — shape data in query functions via `select`
- **No business logic** — conditional rendering only
- **No cross-feature imports** — share via `src/shared/`
- **No direct store writes** — call named actions

### Testing

- Vitest + Angular Testing Utilities (or Karma + Jasmine)
- FIRST principles (Fast, Isolated, Repeatable, Self-Verifying, Timely)
- **Required:** axe-core accessibility checks in every component test

---

## ViewModel — `src/features/*/hooks/`, `src/features/*/store/`

See `docs/ui/architecture/angular/STATE_MANAGEMENT.md` for full patterns.

### Summary

- **TanStack Angular Query** — all server state, wrapped in `injectQuery`/`injectMutation`, shaped via `select`
- **Signals** — client UI state only (modals, tabs, selections); never duplicate server data
- **Boundaries** — query functions don't import from components; stores don't call APIs; functions don't cross features

---

## API (Model Layer) — `src/features/*/api/`, `src/shared/api/`

The API layer is the outbound adapter to the backend. It is the only layer that knows about HTTP endpoints and request/response shapes.

### Hard Rules

- Plain async functions — no Angular decorators, `inject()` calls, or component lifecycle in feature API files
- Receive the shared `ApiService` as an explicit parameter; do not use `HttpClient` directly in feature API files
- All request parameters and return types explicitly typed — no `any`
- Name functions as verb + resource: `fetchUserProfile`, `updateUserProfile`
- Let errors propagate — TanStack Query handles error state
- No business logic — transform data in the ViewModel, not here

### Shared ApiService

`src/shared/api/api.service.ts` owns:

- Base URL from `environment.apiBaseUrl` — never hardcoded
- Auth header injection via HTTP interceptor
- Common error shape normalisation

No feature-level API file may replicate this logic.

### Pattern

The ViewModel captures `ApiService` during injection setup and passes it to these
functions. API functions never call `inject()`; query callbacks can run later,
outside Angular’s injection context. See `docs/ui/architecture/angular/STATE_MANAGEMENT.md`.

```typescript
// src/features/user/api/user.api.ts
import { firstValueFrom } from 'rxjs';
import type { ApiService } from '../../../shared/api/api.service';

export async function fetchUserProfile(api: ApiService, userId: string): Promise<UserProfileResponse> {
  return firstValueFrom(api.get<UserProfileResponse>(`/users/${userId}`));
}
```

### Environment Variables

- API base URL via `environment.apiBaseUrl` — configured per environment in `src/environments/`
- No secrets in frontend code

---

## Accessibility — applies to all UI under `src/`

See `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md` for the full standard.

### Standard

WCAG 2.1 Level AA. Non-negotiable. Zero critical axe-core violations permitted.

### Quick Reference

- **Semantic HTML first** — use native elements before ARIA
- **Keyboard operable** — Tab, Enter, Space, Arrows, Escape
- **Images** — descriptive alt text (empty only for decorative)
- **Forms** — labels not placeholders; error messages via `aria-describedby`
- **Focus** — always visible; do not suppress outline without replacement
- **Color** — never the sole information carrier
- **Testing** — axe-core in every component test

### Angular-Specific Patterns

- Use **Angular CDK `A11yModule`** for focus trapping in dialogs/overlays
- Use **Angular CDK `LiveAnnouncer`** for dynamic screen reader announcements
- Prefer **native HTML elements** over ARIA role overrides

### Testing Pattern (Angular)

```typescript
import { render } from '@testing-library/angular';
import { axe } from 'vitest-axe';

it('has no accessibility violations', async () => {
  const { container } = await render(MyComponent);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```
