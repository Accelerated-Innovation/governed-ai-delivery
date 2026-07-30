# Next.js State Management

State follows ownership. Do not move server data into a client store merely
because the application uses React.

---

## 1. Decision Table

| State | Preferred owner |
|---|---|
| Initial backend data | Server Component/API adapter |
| Client-refreshed or polled backend data | TanStack React Query when justified |
| Filters/pagination that should be shareable | URL route/search params |
| Form submission | server form/Server Action or React Hook Form for complex client forms |
| Local interaction | `useState`/`useReducer` |
| Theme preference | client state persisted through an approved adapter |
| Cross-component client UI state | calibrated store only when composition/URL state is insufficient |

---

## 2. Server Data

Fetch initial data on the server through typed API adapters. Document caching
and revalidation intentionally; do not assume default behavior fits the
business freshness requirement.

Never:

- fetch a database directly
- duplicate the same backend response into a client store
- serialize secrets to hydrate client state

---

## 3. Client Query Cache

React Query is appropriate for data that genuinely needs browser-side
refreshing, polling, optimistic updates, or offline-aware interaction.

Every query/mutation is wrapped in a named feature hook with:

- typed query keys
- typed adapter calls
- intentional stale/freshness behavior
- mutation invalidation or reconciliation
- safe error mapping

It is not required for data already rendered and refreshed effectively through
the server route.

---

## 4. URL State

Prefer route segments/search params for filters, sort, pagination, tabs, and
other shareable navigation state. Parse and validate them at the route or
feature application boundary.

---

## 5. Forms and Mutations

Use the simplest model that meets interaction and accessibility needs:

- native form + Server Action for server-oriented flows
- React Hook Form for complex client validation/interactions

The backend API performs authoritative validation. Pending, duplicate-submit,
field-error, form-error, success, and retry behavior are planned explicitly.

---

## 6. Client Stores

A client store requires a concrete interaction need that props, composition,
URL state, and local state do not satisfy.

Rules:

- UI state only
- named typed actions
- no raw setters exposed to components
- no backend API calls from the store
- no server-response cache
- feature scope by default
- cross-feature state requires an ADR
