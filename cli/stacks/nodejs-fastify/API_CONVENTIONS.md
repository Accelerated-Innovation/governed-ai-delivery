# Fastify API Design Instructions

Applies to all inbound adapter files under `/api/**`. Route handlers are responsible for HTTP concerns only. All domain logic must be delegated to inbound ports.

---

## 0. Interaction with Domain

* Handlers must call **inbound ports** (TypeScript interfaces) from `ports/inbound/`
* Do **not** call service implementations or business logic directly
* Use Fastify's DI decorator pattern or `awilix` to bind ports
* Inputs (e.g., request body, auth) must be mapped to domain objects before calling ports
* Ports return results or throw domain exceptions; handlers translate those into HTTP responses

---

## 1. Routing

* Use path-style: `/v1/<resource>/<action>` (e.g. `/v1/users/reset-password`)
* Group related routes using `fastify-plugin` and register per feature:

```typescript
import fp from 'fastify-plugin'
import type { FastifyPluginAsync } from 'fastify'

const userRoutes: FastifyPluginAsync = async (fastify) => {
  fastify.post('/v1/users/:userId/activate', activateUserHandler)
}

export default fp(userRoutes)
```

* Avoid scattering route declarations — one plugin file per resource

---

## 2. HTTP Verbs & Status Codes

* Use `fastify.get`, `fastify.post`, `fastify.put`, `fastify.delete`
* Required status codes:

  * `200`: Successful GET — `reply.send(body)`
  * `201`: Resource created — `reply.code(201).send(body)`
  * `204`: No content on DELETE — `reply.code(204).send()`
  * `400`: Validation failure — thrown by TypeBox schema or custom error
  * `401`: Authentication required — `@fastify/jwt` handles automatically
  * `403`: Unauthorized access — thrown by authorization check
  * `404`: Not found — `reply.code(404).send()`
  * `500`: Unexpected server exceptions only — Fastify global error handler

---

## 3. Request & Response Format

* Define request/response schemas using **TypeBox**:

```typescript
import { Type, type Static } from '@sinclair/typebox'

const ActivateUserResponse = Type.Object({
  data: Type.Object({
    id: Type.String(),
    status: Type.String(),
  }),
  error: Type.Optional(Type.Object({
    code: Type.String(),
    message: Type.String(),
  })),
})

type ActivateUserResponseType = Static<typeof ActivateUserResponse>
```

* Map request DTOs to domain inputs before calling a port
* Wrap all responses in the standard envelope above
* Register schemas in the route definition for automatic OpenAPI generation:

```typescript
fastify.post('/:userId/activate', {
  schema: {
    response: { 200: ActivateUserResponse },
  },
}, activateUserHandler)
```

---

## 4. Error Handling

* Ports may throw domain exceptions
* Register a global error handler to convert domain errors to RFC 9457 `ProblemDetail`:

```typescript
fastify.setErrorHandler((error, _request, reply) => {
  if (error instanceof UserNotFoundException) {
    return reply.code(404).send({
      type: 'https://example.com/errors/not-found',
      title: 'User Not Found',
      status: 404,
      detail: error.message,
    })
  }
  fastify.log.error(error)
  return reply.code(500).send({ title: 'Internal Server Error', status: 500 })
})
```

* Centralize exception logging in the error handler
* Never expose stack traces or internal error details in HTTP responses

---

## 5. Authentication & Authorization

* Use `@fastify/jwt` for JWT validation:

```typescript
await fastify.register(import('@fastify/jwt'), {
  secret: process.env.JWT_SECRET!,
})

fastify.addHook('onRequest', async (request, reply) => {
  try {
    await request.jwtVerify()
  } catch {
    reply.send(new Error('Unauthorized'))
  }
})
```

* Extract a structured identity context from `request.user` and pass into the port:

```typescript
async function activateUserHandler(request: FastifyRequest, reply: FastifyReply) {
  const identity = UserContext.fromJwtPayload(request.user as JwtPayload)
  const user = await userService.activateUser(params.userId, identity)
  reply.send({ data: UserDto.from(user) })
}
```

* Do not let domain logic depend on Fastify request types or `@fastify/jwt`
* Include `userId` in all logs via `request.log.child({ userId })`

---

## 6. Observability

* Use `request.log` (pino child logger) for request-scoped structured logging:

```typescript
request.log.info({
  event: 'user_activate_requested',
  userId: params.userId,
  durationMs: Date.now() - startTime,
})
```

* Include `requestId` automatically — Fastify injects `reqId` into every log entry
* Expose metrics via `/metrics` using `fastify-metrics` with `prom-client`

---

## 7. OpenAPI Spec

* Every route must define a `schema` with `summary`, `description`, `tags`, and `response`:

```typescript
fastify.post('/:userId/activate', {
  schema: {
    summary: 'Activate a user account',
    description: 'Transitions a user from pending to active state.',
    tags: ['users'],
    params: Type.Object({ userId: Type.String() }),
    response: {
      200: ActivateUserResponse,
      404: ProblemDetailSchema,
    },
  },
}, activateUserHandler)
```

* Use `@fastify/swagger` + `@fastify/swagger-ui` for automatic spec generation
* Validate OpenAPI schema in CI

---

## 8. Testing

* Use `fastify.inject()` for fast in-process route tests (no real HTTP):

```typescript
import { describe, it, expect, vi } from 'vitest'
import { buildApp } from '../app.js'

describe('POST /v1/users/:userId/activate', () => {
  it('returns 200 when user exists', async () => {
    const mockUserService = { activateUser: vi.fn().mockResolvedValue(testUser) }
    const app = await buildApp({ userService: mockUserService })

    const response = await app.inject({
      method: 'POST',
      url: '/v1/users/abc123/activate',
      headers: { authorization: `Bearer ${validToken}` },
    })

    expect(response.statusCode).toBe(200)
    expect(response.json().data.id).toBe('abc123')
  })
})
```

* Every route must have:

  * Input validation tests
  * Auth tests (unauthenticated, unauthorized)
  * Response shape tests
  * Port mock assertions

---

## 9. Adapter Boundaries

The API layer is an inbound adapter located under:
```
src/api/
```

It must not import from `services/`, `adapters/`, or any infrastructure library except what is needed to wire up plugins. All business logic goes through ports.
