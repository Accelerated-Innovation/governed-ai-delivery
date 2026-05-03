# Technology Stack

This document defines the approved technology stack for this repository.

All contributors and AI agents must follow these standards when selecting libraries, frameworks, or infrastructure.

New technologies require an **ADR** before use.

---

# 1. Primary Language

**Java**

Approved version:
`Java 21 (LTS)`

Rules:

- Use Java records for immutable DTOs and value objects
- Use sealed classes for domain state hierarchies
- Enable preview features only with an ADR
- Avoid raw types — all public interfaces must be fully typed with generics where appropriate
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
`Spring Boot 3.x / Spring Web MVC`

Supporting libraries:

- `springdoc-openapi-starter-webmvc-ui` (OpenAPI / Swagger UI)
- `spring-boot-starter-validation` (Bean Validation — Jakarta EE)
- `jackson-databind` (JSON serialization)

Rules:

- API layer is an **inbound adapter**
- `@RestController` handlers must call **inbound ports** (interfaces)
- Domain logic must never depend on Spring Web
- Error responses must use `ProblemDetail` (RFC 9457, supported natively in Spring 6)
- OpenAPI documentation must be generated automatically

API conventions are defined in:
```
docs/backend/architecture/API_CONVENTIONS.md
```

---

# 4. Agent Frameworks

This repository supports AI-driven features.

Approved orchestration frameworks:
```
Spring AI (primary)
LangChain4j (limited use)
```

### Spring AI

Primary framework for agent orchestration.

Used for:

- multi-step reasoning and tool-calling pipelines
- structured LLM output via advisors
- stateful chat memory
- deterministic prompt templates

### LangChain4j

Allowed for:

- model wrappers
- prompt templates
- lightweight utilities

Avoid using LangChain4j for complex orchestration.

### Decision Matrix

| Scenario | Use | Reason |
|---|---|---|
| Single LLM call with structured output | Spring AI `ChatClient` | Clean abstraction, no orchestration overhead |
| Prompt template with variable substitution | Spring AI `PromptTemplate` | Built-in; no extra dependency |
| Sequential tool calls (> 2 steps) | Spring AI with tools + advisors | Stateful pipeline |
| Branching logic based on LLM output | Spring AI custom advisor chain | Conditional step execution |
| Multi-turn conversation with memory | Spring AI `MessageChatMemoryAdvisor` | State persistence |
| Parallel tool execution | Spring AI parallel tool execution | Fan-out pattern |

**Default rule:** If the task requires more than two sequential LLM interactions, use Spring AI advisors. Otherwise, prefer the direct `ChatClient`.

---

# 4a. LLM Gateway (Level 5)

Approved LLM gateway:
```
Spring AI unified model abstraction
```

All LLM completion requests must route through Spring AI's `ChatModel` abstraction. No direct provider SDK calls for inference outside `adapters/llm/`.

Provides:

- Provider abstraction (Azure OpenAI, OpenAI, Anthropic, Bedrock)
- Retry and fallback logic via Spring Retry
- Token usage tracking

Rules:

- LLM adapter lives in `adapters/llm/` — an outbound adapter
- Domain services call `LlmPort`, never Spring AI `ChatModel` directly
- Provider SDK imports restricted to `adapters/llm/`

Full contract: `docs/backend/architecture/LLM_GATEWAY_CONTRACT.md`

---

# 5. LLM Providers

Providers must be accessed through **adapter layers**.

Examples:

- Azure OpenAI (`spring-ai-azure-openai`)
- OpenAI (`spring-ai-openai`)
- Anthropic (`spring-ai-anthropic`)
- Amazon Bedrock (`spring-ai-bedrock`)

Rules:

- Provider clients must live in `adapters/`
- Domain logic must never call LLM APIs directly
- Prompt templates must be versioned

---

# 6. Persistence

Approved persistence adapters:
```
PostgreSQL (via Spring Data JPA + Hibernate)
Redis (via Spring Data Redis — caching and ephemeral state)
PGVector (via pgvector-hibernate — vector search)
```

Rules:

- Repositories must implement outbound ports
- Domain layer must not depend on JPA, Hibernate, or Spring Data
- Transactions must be handled in adapters (`@Transactional` in adapter layer only)

---

# 7. Messaging and Events

Approved messaging technologies:

- Apache Kafka (via Spring Kafka)
- RabbitMQ (via Spring AMQP)
- AWS SNS/SQS (via Spring Cloud AWS)

Rules:

- Messaging must be implemented through adapters
- Domain events must not depend on messaging libraries

---

# 8. Testing Stack

Primary testing tools:
```
JUnit 5                              — unit and integration tests
Mockito                              — dependency mocking
Spring Boot Test + MockMvc           — API integration tests
AssertJ                              — expressive assertions
Cucumber-JVM + cucumber-spring       — BDD / Gherkin integration tests
Testcontainers                       — real infrastructure in tests (PostgreSQL, Redis)
WireMock                             — external HTTP service stubbing
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
Checkstyle / SpotBugs / PMD   — static analysis
SonarQube                     — code quality
Snyk                          — security vulnerability scanning
ArchUnit                      — architecture boundary enforcement
Spotless                      — code formatting (Google Java Format)
pre-commit                    — pre-commit hooks
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
pom.xml / build.gradle
checkstyle.xml
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

# 10a. LLM Evaluation (Level 5)

Approved LLM evaluation tools:
```
Promptfoo     — adversarial and regression testing (CI)
Spring AI evaluation helpers — quality metrics via provider APIs
```

Rules:

- Promptfoo is required for user-facing features or features processing untrusted input
- These tools complement FIRST/Virtues — they do not replace them

Full contract: `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md`

---

# 11. Observability

Approved tools:

- structured logging (`Logback` with `logstash-logback-encoder` for JSON output)
- metrics and distributed tracing (`OpenTelemetry Java Agent` + Micrometer)

### Structured Logging

Use `Logback` with `logstash-logback-encoder` for JSON-structured logs.

Rules:

- All log entries must be structured JSON in production
- Logs must include `requestId`, `service`, and `layer` fields (via MDC)
- Domain layer may log domain events only — no infrastructure data
- Adapters may log infrastructure details (query times, connection errors, etc.)
- Use SLF4J's `LoggerFactory.getLogger(getClass())` — never `System.out.println()`

### OpenTelemetry

Use the **OpenTelemetry Java Agent** (javaagent) for automatic instrumentation of Spring Boot, JDBC, and HTTP clients, exporting to **Datadog** via OTLP.

For manual spans:

```xml
<dependency>
  <groupId>io.opentelemetry</groupId>
  <artifactId>opentelemetry-api</artifactId>
</dependency>
```

Rules:

- OpenTelemetry Java Agent handles automatic instrumentation — no manual setup required for Spring / JDBC
- Adapters must emit spans for all external calls that are not auto-instrumented
- Domain services must not import OpenTelemetry directly — use an observability port
- Trace context (`traceId`, `spanId`) is automatically injected into log entries via MDC bridge

### Observability Port

An outbound port (`ObservabilityPort`) must abstract logging and tracing from the domain:

- Domain calls port methods (e.g., `recordEvent`, `startSpan`)
- Adapter implements the port using SLF4J + OpenTelemetry API
- This keeps the domain layer infrastructure-agnostic (per architecture contract)

Full contract: `docs/backend/architecture/OBSERVABILITY_PORT_CONTRACT.md`

---

# 11a. Runtime Guardrails (Level 5)

Approved guardrail tools:
```
Spring AI content safety filters    — behavioral safety
Azure AI Content Safety             — structured output validation
```

Rules:

- Both tools live in `adapters/guardrails/`
- Neither may be imported in domain or service layers

Full contract: `docs/backend/architecture/GUARDRAILS_CONTRACT.md`

---

# 12. Static Analysis and Quality Gates

See Section 9 for approved tools. Rules enforced by those tools:

- architecture boundaries (`ArchUnit`)
- security issues (`Snyk`)
- duplication and complexity limits (`SonarQube`)
- formatting (`Spotless` / `google-java-format`)

---

# 13. Dependency Rules

Approved dependency sources:

- Maven Central
- internally approved private repositories

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
