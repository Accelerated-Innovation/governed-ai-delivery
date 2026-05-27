# Technology Stack

This document defines the approved technology stack for this repository.

All contributors and AI agents must follow these standards when selecting libraries, frameworks, or infrastructure.

New technologies require an **ADR** before use.

---

# 1. Primary Language

**TypeScript**

Approved version:
`TypeScript 5+ / Node.js 20 LTS`

Rules:

- `strict` mode enabled in `tsconfig.json`
- `noImplicitAny`, `strictNullChecks`, `exactOptionalPropertyTypes` enforced
- Prefer `type` aliases and `interface` for all public contracts
- Avoid `any` — use `unknown` and narrow at boundaries
- Use Zod for runtime validation of external inputs (API requests, env vars)

---

# 2. Architecture Model

This repository uses **Hexagonal Architecture (Ports and Adapters)**.

Core layers:
```
api/       → inbound adapters (HTTP interfaces)
ports/     → inbound and outbound interfaces
services/  → domain logic and orchestration
adapters/  → infrastructure implementations
common/    → shared utilities and types
```

Rules:

- Domain code must remain framework-agnostic
- Adapters may depend on infrastructure libraries
- Ports define contracts between layers
- Direct dependency between adapters is prohibited

See:
```
docs/backend/architecture/ARCH_CONTRACT.md
docs/backend/architecture/BOUNDARIES.md
```

---

# 3. API Framework

Approved framework:
`Fastify 4+`

Supporting libraries:

- `@fastify/swagger` + `@fastify/swagger-ui` (OpenAPI generation)
- `@sinclair/typebox` (TypeBox JSON Schema for request/response validation)
- `zod` (runtime validation at domain boundaries)
- `@fastify/cors`, `@fastify/helmet`, `@fastify/rate-limit` (security middleware)

Rules:

- API layer is an **inbound adapter**
- Route handlers must call **inbound ports** (TypeScript interfaces)
- Domain logic must never depend on Fastify
- All request/response schemas defined with TypeBox for automatic OpenAPI generation
- Error responses must use RFC 9457 `ProblemDetail` structure
- OpenAPI documentation must be generated automatically

API conventions are defined in:
```
docs/backend/architecture/API_CONVENTIONS.md
```

---

<!-- §4 Agent Frameworks, §4a LLM Gateway moved to AGENT_ARCHITECTURE.md (L5-only). -->

---

# 5. LLM Providers

Providers must be accessed through **adapter layers**.

Examples:

- OpenAI (`@ai-sdk/openai`)
- Anthropic (`@ai-sdk/anthropic`)
- Azure OpenAI (`@ai-sdk/azure`)
- Local models (Ollama)

Rules:

- Provider clients must live in `adapters/`
- Domain logic must never call LLM APIs directly
- Prompt templates must be versioned

---

# 6. Persistence

Approved persistence adapters:
```
PostgreSQL (via Drizzle ORM or Prisma)
Redis (via ioredis — caching and ephemeral state)
pgvector (via pgvector extension with Drizzle/Prisma — vector search)
```

Rules:

- Repositories must implement outbound ports
- Domain layer must not depend on Drizzle, Prisma, or ioredis
- Transactions must be handled in adapters

---

# 7. Messaging and Events

Approved messaging technologies:

- BullMQ (Redis-backed job queues)
- AWS SNS/SQS (`@aws-sdk/client-sqs`)
- Kafka (`kafkajs`)

Rules:

- Messaging must be implemented through adapters
- Domain events must not depend on messaging libraries

---

# 8. Testing Stack

Primary testing tools:
```
Vitest                         — unit and integration tests (fast, native ESM)
@fastify/inject                — Fastify route testing without real HTTP
Supertest                      — HTTP integration tests
Cucumber.js                    — BDD / Gherkin integration tests
testcontainers                 — real infrastructure in tests (PostgreSQL, Redis)
msw (Mock Service Worker)      — external HTTP service stubbing (Node mode)
```

Test categories:

- unit tests
- BDD integration tests
- contract tests

Testing must follow the rules defined in:
```
docs/backend/architecture/TESTING.md
```

---

# 9. Development Tooling

Approved development tools include:
```
ESLint (+ @typescript-eslint)   — linting
Prettier                        — formatting
SonarQube                       — code quality
Snyk                            — security vulnerability scanning
dependency-cruiser              — architecture boundary enforcement
lint-staged + Husky             — pre-commit hooks
```

Configuration for these tools typically lives in:
```
eslint.config.ts
.prettierrc
.snyk
sonar-project.properties
.dependency-cruiser.cjs
.github/workflows/
```

Agent interaction rules for development tools are defined in:

`docs/backend/architecture/AGENT_ARCHITECTURE.md`

---

# 10. Evaluation Framework

AI behavior evaluation is required when features use LLMs.

Evaluation standards and tooling:
```
docs/backend/evaluation/eval_criteria.md   ← what must be evaluated (non-negotiable)
docs/backend/evaluation/EVAL_STACK.md      ← approved tools and pipeline by environment
```

Feature-level configuration:
```
features/<feature_name>/eval_criteria.yaml
```

---

<!-- §10a LLM Evaluation moved to AGENT_ARCHITECTURE.md (L5-only). -->

---

# 11. Observability

Approved tools:

- structured logging (`pino` with JSON output)
- metrics and distributed tracing (`@opentelemetry/sdk-node`)

### Structured Logging

Use `pino` for all application logging.

Rules:

- All log entries must be structured JSON in production
- Logs must include `requestId`, `service`, and `layer` fields
- Domain layer may log domain events only — no infrastructure data
- Adapters may log infrastructure details (query times, connection errors, etc.)
- Use `pino.child({ component: 'UserService' })` — never `console.log()`

### OpenTelemetry

Use `@opentelemetry/sdk-node` to unify logs, metrics, and traces exported to **Datadog** via OTLP.

Approved packages:
```
@opentelemetry/sdk-node
@opentelemetry/api
@opentelemetry/instrumentation-fastify
@opentelemetry/instrumentation-http
@opentelemetry/exporter-trace-otlp-proto
pino-opentelemetry-transport
```

Rules:

- All three signals exported via OTLP → Datadog Agent
- `pino-opentelemetry-transport` bridges pino logs into the OTel log pipeline
- Fastify instrumentation is automatic via `@opentelemetry/instrumentation-fastify`
- Adapters must emit spans for all external calls (DB, LLM, cache)
- Domain services must not import OpenTelemetry directly — use an observability port

### Observability Port

An outbound port (`ObservabilityPort`) must abstract logging and tracing from the domain:

- Domain calls port methods (e.g., `recordEvent`, `startSpan`)
- Adapter implements the port using pino + OpenTelemetry
- This keeps the domain layer infrastructure-agnostic

Full contract: `docs/backend/architecture/OBSERVABILITY_PORT_CONTRACT.md`

---

# 11a. Runtime Guardrails (Level 5)

Approved guardrail tools:
```
LlamaGuard (via Ollama or provider API)    — behavioral safety
Zod + custom validators                    — structured output validation
```

Rules:

- Both tools live in `adapters/guardrails/`
- Neither may be imported in domain or service layers

Full contract: `docs/backend/architecture/GUARDRAILS_CONTRACT.md`

---

# 12. Static Analysis and Quality Gates

See Section 9 for approved tools. Rules enforced by those tools:

- architecture boundaries (`dependency-cruiser`)
- security issues (`Snyk`)
- duplication and complexity limits (`SonarQube`)
- formatting and linting (`ESLint` + `Prettier` via `lint-staged`)

---

# 13. Dependency Rules

Approved dependency sources:

- npm registry
- internally approved private registry (GitHub Packages or Verdaccio)

Prohibited:

- unmaintained libraries
- experimental frameworks without ADR
- direct dependency on infrastructure inside domain layer

New libraries require an ADR.

---

# 14. Infrastructure Compatibility

Projects generated from this template must support:

- CI pipelines
- containerized deployment
- stateless service execution

Container tooling may include:

- Docker
- Kubernetes
- Cloud Run / Azure Container Apps

---

# 15. When an ADR Is Required

An ADR must be created if:

- introducing a new framework
- adding an LLM provider
- introducing a new persistence layer
- altering agent orchestration strategy
- introducing new external infrastructure

ADR template:
```
docs/backend/architecture/ADR/TEMPLATE.md
```

---

# Summary

This technology stack ensures:

- architectural consistency
- controlled AI integration
- deterministic testing
- evaluation-driven AI behavior validation
- maintainable and portable systems
