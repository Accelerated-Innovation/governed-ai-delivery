# Next.js API and Business Boundary

This is a hard contract: business operations flow through a published backend
API. The standalone UI never connects directly to a database.

---

## 1. Required Flow

```text
Browser / Next.js UI
        -> typed API adapter
        -> backend business API
        -> backend domain logic
        -> database
```

The backend API is authoritative for authorization, validation, business rules,
and durable state.

---

## 2. Typed API Adapters

Backend calls live in:

```text
src/features/<feature>/api/
src/shared/api/
```

Adapters must:

- use typed request/response contracts
- use the shared transport for base URL, auth, timeouts, and error mapping
- check non-success responses
- avoid leaking backend error details to users
- support cancellation where the calling flow can be abandoned
- keep secrets server-only

Raw `fetch` calls outside declared API infrastructure require an ADR and must
still target a published API, never a database.

---

## 3. No Direct Database Access

Forbidden in the UI target:

- Prisma, Drizzle, Sequelize, Knex, TypeORM, or another ORM
- `pg`, `mysql2`, `mssql`, or another database driver
- SQL query execution
- migration or database-schema ownership
- database URLs or connection strings
- Server Components, Server Actions, or Route Handlers that connect to a
  database

This prohibition cannot be waived by a project-local ADR. Put database-owning
code in a separately governed backend project.

---

## 4. Business Logic

Allowed UI logic:

- view-data mapping and formatting
- presentation-specific sorting/grouping
- loading, empty, error, and optimistic states
- interaction and navigation state
- client feedback that improves form usability

Forbidden authoritative logic:

- pricing or billing decisions
- eligibility
- authorization
- inventory/account balances
- workflow approval rules
- validation that determines whether a durable operation is accepted

The UI may mirror a backend rule for immediate feedback, but the backend must
revalidate it and remain authoritative.

---

## 5. Server Components

Server Components call feature/shared API adapters directly. Do not call an
internal Route Handler merely to reach the same backend API; that adds an
unnecessary HTTP hop.

Server Components must not expose credentials or unfiltered sensitive backend
responses through serializable props.

---

## 6. Server Actions

Server Actions may:

- validate UI input shape
- call a backend API mutation
- translate a backend result into UI action state
- trigger appropriate Next.js revalidation after backend success

They may not:

- write a database
- implement the business operation locally
- make authorization decisions independently of the backend

---

## 7. Thin BFF Route Handlers

Route Handlers are allowed for:

- session/cookie handling
- secure token forwarding
- protocol adaptation
- UI-specific aggregation of published backend operations
- webhook/callback handling that delegates durable work to the backend API

They are not a second business API. Every public handler validates input,
authenticates/authorizes through the approved backend/session contract, avoids
sensitive error disclosure, and applies appropriate abuse controls.

---

## 8. Contract Dependencies

Feature preflight records every backend endpoint, contract owner, availability,
and blocker status. Missing business API operations block UI implementation
until the contract is agreed and documented.
