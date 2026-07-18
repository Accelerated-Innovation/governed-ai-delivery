---
paths:
  - "src/**"
---
# UI Layer Rules — React (src/)

This file consolidates the React UI layer rules. Claude Code loads it automatically when editing files under `src/`. Rules below apply on top of the root govkit governance (`.claude/rules/govkit/governance.md`).

Source-of-truth contracts live in `docs/ui/architecture/` and `docs/ui/architecture/react/` — this file is the inline-loadable summary.

---

## Architecture (Recap)

This project uses MVVM with a vertical slice feature structure under `src/`:

- `src/features/<feature>/components/` — View (pure components)
- `src/features/<feature>/hooks/` — ViewModel (React Query hooks)
- `src/features/<feature>/store/` — ViewModel (Zustand client state)
- `src/features/<feature>/api/` — Model (API client functions)
- `src/features/<feature>/types/` — TypeScript types for this feature
- `src/shared/components/` — Shared UI primitives only
- `src/shared/api/` — Base API config, interceptors, auth headers

---

## Components — `src/features/*/components/`, `src/shared/components/`

See `docs/ui/architecture/react/COMPONENT_CONVENTIONS.md` for full guidance and code examples (Section 8).

### Hard Rules

- **No direct API calls** — use custom hooks wrapping React Query
- **No data transformation** — transform in hooks via `select`
- **No business logic** — conditional rendering only; extract logic to hooks
- **No cross-feature imports** — share via `src/shared/`
- **No direct store writes** — call named actions from the store

### Testing

- Vitest + React Testing Library
- FIRST principles (Fast, Isolated, Repeatable, Self-Verifying, Timely)
- **Required:** axe-core accessibility checks in every component test

---

## ViewModel — `src/features/*/hooks/`, `src/features/*/store/`

See `docs/ui/architecture/react/STATE_MANAGEMENT.md` for full patterns.

### Summary

- **React Query** — all server state, wrapped in custom hooks, shaped via `select`
- **Zustand** — client UI state only (modals, tabs, selections); never duplicate server data
- **Boundaries** — hooks don't import from components; stores don't call APIs; hooks don't cross features

---

## API (Model Layer) — `src/features/*/api/`, `src/shared/api/`

The API layer is the outbound adapter to the backend. It is the only layer that knows about HTTP, endpoints, and request/response shapes.

### Hard Rules

- Plain async functions only — no React, no hooks, no state
- One file per backend resource (e.g., `user.api.ts`, `orders.api.ts`)
- All functions use the shared base client from `src/shared/api/client.ts`
- No raw `fetch` or `axios` calls outside of `src/shared/api/client.ts`
- Request and response types must be explicitly typed — no `any`
- Error handling: let errors propagate — React Query handles error state

### Shared Base Client

`src/shared/api/client.ts` owns:

- Base URL configuration (from environment variables only)
- Auth header injection
- Common error shape normalisation

No feature-level API file may replicate this logic.

### Naming

```typescript
// Functions named as: verb + resource
export async function fetchUserProfile(userId: string): Promise<UserProfileResponse> {}
export async function updateUserProfile(userId: string, payload: UpdateProfilePayload): Promise<UserProfileResponse> {}
export async function deleteUserAccount(userId: string): Promise<void> {}
```

### Environment Variables

- Base URL via `VITE_API_BASE_URL` — never hardcoded
- No secrets in frontend code

---

## Accessibility — applies to all UI under `src/`

See `docs/ui/architecture/ACCESSIBILITY_STANDARDS.md` for the full standard.

### Standard

WCAG 2.1 Level AA. Non-negotiable. Zero critical axe-core violations permitted.

### Quick Reference

- **Semantic HTML first** — use native elements before ARIA
- **Keyboard operable** — every interactive element must work with Tab, Enter, Space, Arrows, Escape
- **Images** — descriptive alt text (empty only for decorative)
- **Forms** — labels not placeholders; error messages via `aria-describedby`
- **Focus** — always visible; do not suppress outline without replacement
- **Color** — never the sole information carrier
- **Testing** — axe-core in every component test

### Testing Pattern (React)

```typescript
import { render } from '@testing-library/react';
import { axe } from 'vitest-axe';

it('has no accessibility violations', async () => {
  const { container } = render(<MyComponent />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```
