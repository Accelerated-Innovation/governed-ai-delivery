# Server and Client Component Boundaries

Server Components are the default in `ui-nextjs`. Add a Client Component only
for capabilities that require the browser or React client runtime.

---

## 1. Server Components

Use a Server Component for:

- route and layout composition
- API data fetching close to the backend
- access to server-only credentials
- reducing browser JavaScript
- streaming content through Suspense boundaries

Keep data fetching behind typed API/application functions rather than embedding
transport logic in JSX.

---

## 2. Client Components

Use `"use client"` only when the subtree requires:

- event handlers
- local interactive state
- lifecycle effects
- browser APIs
- client-only third-party libraries
- client query/store hooks

Place the boundary as deep as practical. Everything imported by a Client
Component participates in its client module graph.

---

## 3. Props Across the Boundary

Props passed from Server to Client Components must be serializable and limited
to what the interaction needs.

Do not pass:

- secrets or tokens
- database/backend implementation objects
- raw oversized API responses when a smaller view shape is sufficient
- functions other than supported Server Action references

---

## 4. Module Isolation

Mark sensitive adapters as server-only. Browser-dependent modules are
client-only. A shared barrel must not erase this distinction.

Forbidden:

- importing server-only API/auth code into a Client Component
- reading non-public environment variables from client code
- placing `"use client"` on a broad layout to work around one interactive leaf

---

## 5. Loading and Errors

Use route-segment `loading.tsx`, Suspense, `error.tsx`, and `not-found.tsx`
intentionally. Every data-bearing screen plans:

- loading
- empty
- error
- success
- unauthorized/forbidden when applicable
- not-found when applicable

Error UI exposes safe user-facing messages and a recovery action where one is
possible.

---

## 6. Mutations

Mutations may originate from a Server Action or a Client Component calling an
approved API/BFF endpoint. In both cases:

- backend business API remains authoritative
- pending and duplicate-submit behavior is explicit
- errors are mapped safely
- cache/revalidation behavior is documented

---

## 7. Testing the Boundary

Tests verify:

- server-only modules cannot enter client bundles
- Client Components are limited to interactive areas
- serializable props contain no secrets
- async Server Component journeys have integration/E2E coverage
- mutation flows cover pending, success, validation failure, and backend error
