# Layer Implementation Guide

This document provides a consolidated reference for implementing each layer in the hexagonal architecture.

---

## Overview

The system uses **Hexagonal Architecture** with these layers:

```
┌─────────────────────────┐
│   Adapters (Inbound)    │  api/
├─────────────────────────┤
│  Ports (Interfaces)     │  ports/inbound/, ports/outbound/
├─────────────────────────┤
│  Domain (Core Logic)    │  services/, models/
├─────────────────────────┤
│   Adapters (Outbound)   │  adapters/
└─────────────────────────┘
```

All communication goes through ports. Adapters never talk directly to each other.

---

## 1. Domain Layer

**Location:** `src/domain/services/`, `src/domain/models/`

**Role:** Pure business logic and state management. The core of the system.

### Hard Rules

- **No external dependencies** — only Node.js built-ins and domain-specific types
- **No framework references** — Fastify, Drizzle, ioredis, pino, etc. must never appear
- **Dependency injection only** — all external systems injected via constructor
- **Stateless functions** — business logic as pure functions where possible
- **Domain-specific exceptions** — throw exceptions that adapters can translate
- **Interfaces (ports) only** — no implementation details in domain code

### Examples

```typescript
// ✓ Good — pure domain logic, injected dependencies
export class UserService implements UserServicePort {
  constructor(private readonly repo: UserRepository) {}

  async activateUser(userId: string, identity: UserContext): Promise<User> {
    const user = await this.repo.findById(userId)
    if (!user) throw new UserNotFoundException(userId)
    user.activate()
    await this.repo.save(user)
    return user
  }
}

// ✗ Bad — framework references, hardcoded dependencies
import { FastifyInstance } from 'fastify'     // framework in domain
import { db } from '../adapters/postgres/db'  // hardcoded adapter

export class UserService {
  async activateUser(fastify: FastifyInstance, id: string) {
    const row = await db.select().from(users).where(eq(users.id, id))  // leaks ORM
    ...
  }
}
```

### Testing

- Unit test all public methods with Vitest
- Mock all injected port dependencies with `vi.fn()`
- No database, HTTP, or external service calls
- Fast and isolated

**Reference:** `docs/backend/architecture/ARCH_CONTRACT.md`

---

## 2. Port Layer

**Location:** `src/ports/inbound/`, `src/ports/outbound/`

**Role:** Define contracts between domain and adapters.

### Inbound Ports

```typescript
// ports/inbound/UserServicePort.ts
export interface UserServicePort {
  activateUser(userId: string, identity: UserContext): Promise<User>
  getUser(userId: string): Promise<User | null>
}
```

### Outbound Ports

```typescript
// ports/outbound/UserRepository.ts
export interface UserRepository {
  findById(userId: string): Promise<User | null>
  save(user: User): Promise<void>
}
```

### Hard Rules

- **Interface only** — no implementation logic, no side effects
- **Framework-agnostic** — no Fastify, Drizzle, or infrastructure types
- **Domain types only** — use domain models, DTOs, exceptions
- **Single concern** — one port per interface/contract

**Reference:** `docs/backend/architecture/BOUNDARIES.md`

---

## 3. Inbound Adapter Layer (API)

**Location:** `src/api/`

**Role:** Handle HTTP requests and delegate to domain via inbound ports.

```typescript
// api/users/userRoutes.ts
import fp from 'fastify-plugin'
import type { FastifyPluginAsync } from 'fastify'
import type { UserServicePort } from '../../ports/inbound/UserServicePort.js'

const userRoutes: FastifyPluginAsync<{ userService: UserServicePort }> = async (
  fastify, { userService }
) => {
  fastify.post<{ Params: { userId: string } }>(
    '/v1/users/:userId/activate',
    { onRequest: [fastify.authenticate] },
    async (request, reply) => {
      const identity = UserContext.fromJwtPayload(request.user)
      try {
        const user = await userService.activateUser(request.params.userId, identity)
        return reply.code(200).send({ data: UserDto.from(user) })
      } catch (err) {
        if (err instanceof UserNotFoundException) return reply.code(404).send()
        if (err instanceof UserAlreadyActiveError)
          return reply.code(400).send({ error: { code: 'USER_ALREADY_ACTIVE' } })
        throw err
      }
    }
  )
}

export default fp(userRoutes)
```

### Hard Rules

- **Thin adapters** — validate input, call inbound port, translate response
- **No business logic** — all logic lives in the domain
- **Port delegation** — all work goes through inbound ports
- **Exception mapping** — catch domain exceptions, translate to HTTP status codes

### Testing

- Use `fastify.inject()` for fast in-process route tests
- Mock the inbound port with `vi.fn()`

**Reference:** `docs/backend/architecture/API_CONVENTIONS.md`

---

## 4. Outbound Adapter Layer

**Location:** `src/adapters/`

**Role:** Implement outbound ports. Connect domain to external systems.

### Structure

```
adapters/
├── postgres/           # Drizzle-based repository adapter
│   ├── schema.ts       # Drizzle table schemas
│   └── UserRepositoryAdapter.ts
├── redis/              # ioredis cache adapter
│   └── RedisCacheAdapter.ts
├── stripe/             # External API adapter
│   └── StripePaymentAdapter.ts
└── email/              # Email service adapter
    └── ResendEmailAdapter.ts
```

### Example Implementation

```typescript
// adapters/postgres/UserRepositoryAdapter.ts
import { db } from './db.js'
import { users } from './schema.js'
import { eq } from 'drizzle-orm'
import type { UserRepository } from '../../ports/outbound/UserRepository.js'

export class UserRepositoryAdapter implements UserRepository {
  async findById(userId: string): Promise<User | null> {
    const row = await db.select().from(users).where(eq(users.id, userId)).limit(1)
    return row[0] ? toDomain(row[0]) : null
  }

  async save(user: User): Promise<void> {
    await db.insert(users)
      .values(toRow(user))
      .onConflictDoUpdate({ target: users.id, set: toRow(user) })
  }
}
```

### Hard Rules

- **Port implementation only** — implement the interface you're adapting
- **No business logic** — translation and integration only
- **No cross-adapter calls** — each adapter is independent
- **ORM types stay here** — don't leak Drizzle/Prisma schema types to the domain
- **Exception translation** — catch infrastructure errors, throw domain exceptions

### Testing

- **Unit tests:** Mock Drizzle `db` with `vi.fn()`
- **Integration tests:** Use Testcontainers for real PostgreSQL / Redis
- **Contract tests:** Verify adapter satisfies its port interface

**Reference:** `docs/backend/architecture/BOUNDARIES.md`

---

## 5. Composition Root (Dependency Injection)

**Location:** `src/app.ts` or `src/container.ts`

Use `awilix` or manual wiring to compose adapters and ports:

```typescript
// app.ts
import Fastify from 'fastify'
import { UserRepositoryAdapter } from './adapters/postgres/UserRepositoryAdapter.js'
import { UserService } from './domain/services/UserService.js'
import userRoutes from './api/users/userRoutes.js'

export async function buildApp() {
  const fastify = Fastify({ logger: true })

  const userRepo = new UserRepositoryAdapter()
  const userService = new UserService(userRepo)

  await fastify.register(userRoutes, { userService })

  return fastify
}
```

### Hard Rules

- **Single location** — all wiring in one place
- **No adapters in domain** — adapters only instantiated here
- **Dependency chain clear** — easy to see what depends on what

---

## 6. Cross-Cutting Concerns

**Location:** `src/common/`

```
common/
├── dto.ts              # Data transfer objects
├── exceptions.ts       # Domain exceptions
├── logging.ts          # pino logger factory
├── observability.ts    # OTel tracing helpers
└── validators.ts       # Reusable Zod schemas
```

### Hard Rules

- **No imports from other layers** — common cannot import from `services/`, `adapters/`, or `api/`
- **No business logic** — utilities and shared types only

---

## 7. Dependency Rules

```
┌──────────────────────────┐
│  API Adapters            │  → can import Ports, Common + Fastify
├──────────────────────────┤
│  Ports (Interfaces)      │  → can import Domain, Common
├──────────────────────────┤
│  Domain Services         │  → can import Common only (no Fastify, Drizzle, ioredis)
├──────────────────────────┤
│  Outbound Adapters       │  → can import Domain, Ports, Common + Drizzle/ioredis
├──────────────────────────┤
│  Common (Utils)          │  → no dependencies
└──────────────────────────┘
```

Enforced via **`dependency-cruiser`**. Violations require an ADR.

---

## 8. Testing by Layer

| Layer | Type | Dependencies | Speed |
|-------|------|--------------|-------|
| Domain | Unit | All mocked (`vi.fn()`) | Fast |
| Ports | Contract | N/A | N/A |
| API | Unit + Integration | Mocked + `fastify.inject()` | Fast/Medium |
| Outbound Adapters | Unit + Integration | Mocked + Testcontainers | Medium/Slow |

---

## 9. Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---------|----------------|-----|
| Domain imports Drizzle schema | Couples domain to infrastructure | Use outbound ports |
| Route handler calls `UserService` directly | Violates port contract | Call `UserServicePort` interface |
| Adapter calls another adapter | Creates implicit dependencies | Go through ports |
| Putting logic in route handler | Mixes concerns | Move to domain service |
| `import { db } from '../adapters/...'` in domain | Hardcoded dependency | Inject via constructor |
| Circular imports | Breaks architecture | Refactor to use ports |
