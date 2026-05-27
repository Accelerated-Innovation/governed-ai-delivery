# Technology Stack

This document defines the approved technology stack for this repository.

All contributors and AI agents must follow these standards when selecting libraries, frameworks, or infrastructure.

New technologies require an **ADR** before use.

---

# 1. Primary Language

**C#**

Approved version:
`C# 12 / .NET 8 (LTS)`

Rules:

- Nullable reference types enabled (`<Nullable>enable</Nullable>`)
- Prefer `record` types for immutable DTOs and value objects
- Use `required` properties on records and classes where applicable
- Avoid dynamic typing in domain logic — all public interfaces must be typed
- Static typing must support maintainability and clarity

---

# 2. Architecture Model

This repository uses **Hexagonal Architecture (Ports and Adapters)**.

Core layers:
```
Api/       → inbound adapters (HTTP interfaces)
Ports/     → inbound and outbound interfaces
Services/  → domain logic and orchestration
Adapters/  → infrastructure implementations
Common/    → shared utilities and types
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
`ASP.NET Core Minimal APIs (.NET 8)`

Supporting libraries:

- `Microsoft.AspNetCore.OpenApi` (OpenAPI generation)
- `Swashbuckle.AspNetCore` (Swagger UI)
- `FluentValidation.AspNetCore` (request validation)

Rules:

- API layer is an **inbound adapter**
- Route handlers must call **inbound ports** (interfaces)
- Domain logic must never depend on ASP.NET Core
- Use `IResult` and `Results.*` for responses
- Error responses must use `ProblemDetails` (RFC 9457)
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

- Azure OpenAI
- OpenAI
- Anthropic
- Local models (Ollama)

Rules:

- Provider clients must live in `Adapters/`
- Domain logic must never call LLM APIs directly
- Prompt templates must be versioned

---

# 6. Persistence

Approved persistence adapters:
```
PostgreSQL (via Entity Framework Core 8)
Redis (via StackExchange.Redis — caching and ephemeral state)
pgvector (via pgvector-dotnet — vector search)
Azure SQL / SQL Server (via EF Core)
```

Rules:

- Repositories must implement outbound ports
- Domain layer must not depend on EF Core or StackExchange.Redis
- Transactions must be handled in adapters

---

# 7. Messaging and Events

Approved messaging technologies:

- Azure Service Bus
- RabbitMQ (via MassTransit)
- AWS SNS/SQS

Rules:

- Messaging must be implemented through adapters
- Domain events must not depend on messaging libraries

---

# 8. Testing Stack

Primary testing tools:
```
xUnit                                  — unit and integration tests
NSubstitute                            — dependency mocking
Microsoft.AspNetCore.Mvc.Testing       — API integration tests (TestServer)
SpecFlow                               — BDD / Gherkin integration tests
FluentAssertions                       — expressive assertions
Bogus                                  — test data generation
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
dotnet-format / CSharpier   — formatting
Roslyn Analyzers            — static analysis (StyleCop, SonarAnalyzer)
SonarQube                   — code quality
Snyk                        — security vulnerability scanning
ArchUnitNET                 — architecture boundary enforcement
Husky.Net                   — pre-commit hooks
```

These tools may be used by AI coding agents during planning and implementation to:

- detect structural complexity
- identify duplicated logic
- enforce architecture boundaries
- detect security vulnerabilities
- enforce formatting rules

Tool findings should be treated as **blocking signals** when they violate project policies.

Configuration for these tools typically lives in:
```
.editorconfig
Directory.Build.props
.snyk
sonar-project.properties
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

- structured logging (`Serilog` with JSON formatter)
- metrics and distributed tracing (`OpenTelemetry .NET SDK`)

### Structured Logging

Use `Serilog` for all application logging.

Rules:

- All log entries must be structured JSON in production
- Logs must include `RequestId`, `Service`, and `Layer` properties
- Domain layer may log domain events only — no infrastructure data
- Adapters may log infrastructure details (query times, connection errors, etc.)
- Use `Log.ForContext<T>()` — never `Console.WriteLine()` or `Debug.Print()`

### OpenTelemetry

Use `OpenTelemetry .NET SDK` to unify logs, metrics, and traces into a single pipeline exported to **Datadog** via the Datadog Agent (OTLP ingestion).

Approved packages:
```
OpenTelemetry
OpenTelemetry.Extensions.Hosting
OpenTelemetry.Instrumentation.AspNetCore
OpenTelemetry.Instrumentation.Http
OpenTelemetry.Exporter.OpenTelemetryProtocol
Serilog.Sinks.OpenTelemetry
```

Rules:

- All three signals (logs, metrics, traces) are exported via OTLP → Datadog Agent
- `Serilog.Sinks.OpenTelemetry` bridges Serilog into the OTel log pipeline
- ASP.NET Core instrumentation is automatic via `OpenTelemetry.Instrumentation.AspNetCore`
- Adapters must emit spans for all external calls (DB, LLM, cache)
- Domain services must not import OpenTelemetry directly — use an observability port
- Trace context (`TraceId`, `SpanId`) is automatically injected into log entries

### Observability Port

An outbound port (`IObservabilityPort`) must abstract logging and tracing from the domain:

- Domain calls port methods (e.g., `RecordEvent`, `StartSpan`)
- Adapter implements the port using Serilog + OpenTelemetry
- This keeps the domain layer infrastructure-agnostic (per architecture contract)

Full contract: `docs/backend/architecture/OBSERVABILITY_PORT_CONTRACT.md`

---

# 11a. Runtime Guardrails (Level 5)

Approved guardrail tools:
```
Semantic Kernel content safety filters    — behavioral safety
Azure AI Content Safety                   — structured output validation
```

Rules:

- Both tools live in `Adapters/Guardrails/`
- Neither may be imported in domain or service layers

Full contract: `docs/backend/architecture/GUARDRAILS_CONTRACT.md`

---

# 12. Static Analysis and Quality Gates

See Section 9 for approved tools. Rules enforced by those tools:

- architecture boundaries (`ArchUnitNET`)
- security issues (`Snyk`)
- duplication and complexity limits (`SonarQube`)
- formatting (`CSharpier` / `dotnet-format` via `Husky.Net`)

---

# 13. Dependency Rules

Approved dependency sources:

- NuGet (nuget.org)
- internally approved packages

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
- Azure Container Apps

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

# 16. Customization for New Projects

New projects using this template should review and customize:

- LLM provider configuration
- persistence technology
- messaging infrastructure
- deployment platform

Changes must remain consistent with the architecture contract.

---

# Summary

This technology stack ensures:

- architectural consistency
- controlled AI integration
- deterministic testing
- evaluation-driven AI behavior validation
- maintainable and portable systems
