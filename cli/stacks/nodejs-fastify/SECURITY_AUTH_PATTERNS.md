# Security and Authentication Patterns

This document defines allowed authentication and authorization models. All API access and secure workflows must follow these patterns. Deviations require an ADR.

---

## 1. Authentication Model

### JWT Bearer Token

* Authentication is enforced at the **adapter layer** (`/api`) using `Authorization: Bearer <access_token>`

```
Authorization: Bearer <access_token>
```

* Tokens must:

  * Be signed with `HS256` or `RS256`
  * Include `sub`, `iat`, `exp`, and `scope` claims
  * Be validated using `@fastify/jwt`

* Configure JWT validation in `app.ts`:

```typescript
await fastify.register(import('@fastify/jwt'), {
  secret: process.env.JWT_SECRET!,
  verify: {
    algorithms: ['HS256', 'RS256'],
    maxAge: '1h',
  },
})

fastify.decorate('authenticate', async (request: FastifyRequest, reply: FastifyReply) => {
  try {
    await request.jwtVerify()
  } catch {
    reply.code(401).send({ error: 'Unauthorized' })
  }
})
```

* The resulting `UserContext` is constructed from `request.user` (the decoded JWT payload) and passed into ports. **Domain code must never validate tokens directly.**

### Refresh Token Policy

* Access tokens expire after 1 hour
* If using refresh tokens:

  * Store in secure HTTP-only cookies
  * Validate server-side before issuing new access tokens

---

## 2. Authorization Model

### Role-Based Access Control (RBAC)

* Use `scope` or `role` claims in JWT
* Valid roles: `user`, `admin`, `service`
* Implement an `authorize` decorator that checks the required role:

```typescript
fastify.decorate('authorize', (requiredRole: string) =>
  async (request: FastifyRequest, reply: FastifyReply) => {
    const identity = UserContext.fromJwtPayload(request.user as JwtPayload)
    if (identity.role !== requiredRole) {
      reply.code(403).send({ error: 'Forbidden' })
    }
  }
)
```

### Route enforcement pattern:

```typescript
fastify.get('/v1/admin/stats', {
  onRequest: [fastify.authenticate, fastify.authorize('admin')],
}, getAdminStatsHandler)
```

* Never hardcode roles in route handlers
* Domain ports should receive a typed `UserContext` without JWT details

---

## 3. Cross-Cutting Security Rules

* All protected endpoints must use the `authenticate` hook via `onRequest`
* Public endpoints must be declared explicitly — default is protected
* Never decode tokens manually using `jwt.verify()` outside the auth setup

---

## 4. Identity Propagation

* Log `userId` and `requestId` at all adapter boundaries via pino's child logger:

```typescript
request.log.info({
  event: 'activate_user_requested',
  userId: identity.userId,
  requestId: request.id,
})
```

* Pass downstream service headers:

  * `Authorization: Bearer <access_token>`
  * `X-Request-ID`

---

## 5. Account State Enforcement

* Block requests for suspended or expired accounts in the inbound adapter:

```typescript
const identity = UserContext.fromJwtPayload(request.user as JwtPayload)
if (identity.isSuspended) {
  return reply.code(403).send({ error: 'Account suspended' })
}
```

* The `UserContext` type must include state flags:

```typescript
export interface UserContext {
  userId: string
  role: string
  isActive: boolean
  isVerified: boolean
  isSuspended: boolean
}

export const UserContext = {
  fromJwtPayload(payload: JwtPayload): UserContext {
    return {
      userId:      payload.sub!,
      role:        payload.role ?? 'user',
      isActive:    payload.is_active === true,
      isVerified:  payload.is_verified === true,
      isSuspended: payload.is_suspended === true,
    }
  },
}
```

* Ports must receive a validated `UserContext` with state flags already checked

---

## 6. Password Hashing

* Use `argon2` for password hashing (preferred):

```typescript
import argon2 from 'argon2'

const hash = await argon2.hash(plainPassword, { type: argon2.argon2id })
const valid = await argon2.verify(hash, plainPassword)
```

* Alternatively, use `bcryptjs` with a cost factor of 12+
* Never store plain-text passwords
* Never use MD5 or SHA-1 for password storage

---

## 7. Common Violations

🚫 Skipping token validation
🚫 Extracting `userId` from raw tokens without `@fastify/jwt` verification
🚫 Inline role checks like `if (payload.role === 'admin')`
🚫 Logging token contents or passwords
🚫 Accepting passwords in query params or GET requests
🚫 Storing secrets in `.env` committed to version control — use a secrets manager

---

## 8. Related Files

* `src/api/plugins/auth.ts` — `authenticate` and `authorize` decorators
* `src/common/UserContext.ts` — `fromJwtPayload()` factory, roles, and flags
* `src/api/middleware/requestEnrichment.ts` — injects `userId` and `requestId` into logs

---

## 9. Domain Constraints

* Domain ports must never depend on:

  * `@fastify/jwt` or any JWT library
  * Fastify request/response types
  * Cookie or header parsing

* Security and identity enforcement is the responsibility of the inbound adapter (API layer)

* All domain-facing methods receive a validated `UserContext` or fail early
