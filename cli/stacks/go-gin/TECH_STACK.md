# Technology Stack

This document defines the approved technology stack for this repository.

All contributors and AI agents must follow these standards when selecting libraries, frameworks, or infrastructure.

New technologies require an **ADR** before use.

---

# 1. Primary Language

**Go**

Approved version:
`Go 1.22+`

Rules:

- All public functions and types must have doc comments
- Prefer explicit error handling over panics — `panic` only for unrecoverable programmer errors
- Use `errors.Is` / `errors.As` for error comparison — never string matching on `err.Error()`
- Avoid `interface{}` / `any` in domain code — use typed interfaces and concrete structs
- Static typing must support maintainability and clarity

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
- Ports define contracts (Go interfaces) between layers
- Direct dependency between adapters is prohibited

See:
```
docs/backend/architecture/ARCH_CONTRACT.md
docs/backend/architecture/BOUNDARIES.md
```

---

# 3. API Framework

Approved framework:
`Gin 1.9+`

Supporting libraries:

- `swaggo/swag` + `gin-swagger` (OpenAPI / Swagger UI generation)
- `go-playground/validator/v10` (request validation via struct tags)

Rules:

- API layer is an **inbound adapter**
- `gin.HandlerFunc` handlers must call **inbound ports** (Go interfaces)
- Domain logic must never depend on Gin
- All responses must use `c.JSON(statusCode, body)` — avoid raw `http.ResponseWriter` writes
- Error responses must follow RFC 9457 `ProblemDetail` structure
- OpenAPI documentation must be generated automatically via `swaggo/swag`

API conventions are defined in:
```
docs/backend/architecture/API_CONVENTIONS.md
```

---

<!-- Agent-runtime contracts live in the optional skill-oriented-agent-architecture extension.
     Model gateway contracts live in the optional llm-application extension. -->

---

# 5. LLM Providers (when `llm-application` is installed)

Contract: `extensions/llm-application/docs/backend/architecture/LLM_GATEWAY_CONTRACT.md`

Providers must be accessed through **adapter layers**.

Examples:

- Azure OpenAI (via `sashabaranov/go-openai` with Azure base URL)
- OpenAI (`sashabaranov/go-openai`)
- Anthropic (`anthropics/anthropic-sdk-go`)

Rules:

- Provider clients must live in `adapters/`
- Domain logic must never call LLM APIs directly
- Prompt templates must be versioned

---

# 6. Persistence

Approved persistence adapters:
```
PostgreSQL (via pgx/v5 — direct, no ORM; or sqlc for typed queries)
Redis (via go-redis/v9 — caching and ephemeral state)
pgvector (via pgvector-go — vector search)
```

Rules:

- Repositories must implement outbound ports (Go interfaces)
- Domain layer must not depend on `pgx`, `sqlc`, or `go-redis`
- Transactions must be handled in adapters

---

# 7. Messaging and Events

Approved messaging technologies:

- Kafka (`confluentinc/confluent-kafka-go` or `segmentio/kafka-go`)
- AWS SNS/SQS (`aws-sdk-go-v2/service/sqs`)
- NATS (`nats-io/nats.go`)

Rules:

- Messaging must be implemented through adapters
- Domain events must not depend on messaging libraries

---

# 8. Testing Stack

Primary testing tools:
```
go test (stdlib)                 — unit and integration tests
testify/assert + testify/mock    — assertions and mocking
godog                            — BDD / Gherkin integration tests
testcontainers-go                — real infrastructure in tests (PostgreSQL, Redis)
httpmock                         — external HTTP service stubbing
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
golangci-lint         — linting (staticcheck, errcheck, revive, etc.)
gofmt / goimports     — formatting
SonarQube             — code quality
Snyk                  — security vulnerability scanning
go-arch-lint          — architecture boundary enforcement
pre-commit            — pre-commit hooks
```

Configuration for these tools typically lives in:
```
.golangci.yml
.arch-lint.yml
.snyk
sonar-project.properties
.github/workflows/
```

AI coding agents may use these tools only within the project's approved task and authority boundaries.

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

<!-- Model evaluation contracts live in the optional llm-application extension. -->

---

# 11. Observability

Approved tools:

- structured logging (`uber-go/zap` with JSON output)
- metrics and distributed tracing (`go.opentelemetry.io/otel` SDK)

### Structured Logging

Use `uber-go/zap` for all application logging.

Rules:

- All log entries must be structured JSON in production (use `zap.NewProduction()`)
- Logs must include `request_id`, `service`, and `layer` fields
- Domain layer may log domain events only — no infrastructure data
- Adapters may log infrastructure details (query times, connection errors, etc.)
- Use `zap.L()` or inject a `*zap.Logger` — never use `log.Println()` or `fmt.Println()`

### OpenTelemetry

Use `go.opentelemetry.io/otel` SDK with OTLP export to **Datadog** via the Datadog Agent.

Approved packages:
```
go.opentelemetry.io/otel
go.opentelemetry.io/otel/sdk/trace
go.opentelemetry.io/otel/sdk/metric
go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc
go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin
go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp
```

Rules:

- All three signals exported via OTLP → Datadog Agent
- Gin instrumentation via `otelgin` middleware — no manual span creation for HTTP handlers
- Adapters must emit spans for all external calls (DB, LLM, cache)
- Domain services must not import OpenTelemetry directly — use an observability port

### Observability Port

An outbound port (`ObservabilityPort`) must abstract logging and tracing from the domain:

- Domain calls port methods (e.g., `RecordEvent`, `StartSpan`)
- Adapter implements the port using zap + OpenTelemetry
- This keeps the domain layer infrastructure-agnostic

Full contract: `docs/backend/architecture/OBSERVABILITY_PORT_CONTRACT.md`

---

<!-- Model guardrail contracts live in the optional llm-application extension. -->

---

# 12. Static Analysis and Quality Gates

See Section 9 for approved tools. Rules enforced by those tools:

- architecture boundaries (`go-arch-lint`)
- security issues (`Snyk`, `govulncheck`)
- duplication and complexity limits (`SonarQube`)
- formatting (`gofmt` / `goimports`)

---

# 13. Dependency Rules

Approved dependency sources:

- Go module proxy (proxy.golang.org)
- internally approved private Go module proxy

Prohibited:

- unmaintained modules
- experimental frameworks without ADR
- direct dependency on infrastructure inside domain layer

New modules require an ADR.

---

# 14. Infrastructure Compatibility

Projects generated from this template must support:

- CI pipelines
- containerized deployment
- stateless service execution

Container tooling may include:

- Docker
- Kubernetes
- Cloud Run

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
