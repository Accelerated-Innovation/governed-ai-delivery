# Technology Stack

This document defines the approved technology stack for this repository.

All contributors and AI agents must follow these standards when selecting libraries, frameworks, or infrastructure.

New technologies require an **ADR** before use.

---

# 1. Primary Language

**Python**

Approved version:
`Python 3.12+`

Rules:

- Type hints required for public interfaces
- Prefer `dataclasses` or `pydantic` models for structured data
- Avoid dynamic typing in domain logic
- Static typing should support maintainability and clarity

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
docs/architecture/ARCH_CONTRACT.md
docs/architecture/BOUNDARIES.md
```


---

# 3. API Framework

Approved framework:
`FastAPI`


Supporting libraries:

- `pydantic`
- `httpx`
- `uvicorn`

Rules:

- API layer is an **inbound adapter**
- Route handlers must call **inbound ports**
- Domain logic must never depend on FastAPI
- OpenAPI documentation must be generated automatically

API conventions are defined in:
```
docs/architecture/API_CONVENTIONS.md
``` 

---

# 4. Agent Frameworks

This repository supports AI-driven features.

Approved orchestration frameworks:
```
LangGraph
LangChain (limited use)
```


### LangGraph

Primary framework for agent orchestration.

Used for:

- multi-step reasoning
- tool execution
- stateful workflows
- deterministic agent graphs

### LangChain

Allowed for:

- model wrappers
- prompt templates
- lightweight utilities

Avoid using LangChain for complex orchestration.

---

# 5. LLM Providers

Providers must be accessed through **adapter layers**.

Examples:

- OpenAI
- Anthropic
- Azure OpenAI
- local models

Rules:

- Provider clients must live in `adapters/`
- Domain logic must never call LLM APIs directly
- Prompt templates must be versioned

---

# 6. Persistence

Approved persistence adapters:
```
PostgreSQL (via SQLAlchemy)
Redis (for caching and ephemeral state)
PGVector (for vector search)
Supabase (PostgreSQL via Supabase client)
```

Rules:

- Repositories must implement outbound ports
- Domain layer must not depend on ORM libraries
- Transactions must be handled in adapters

---

# 7. Messaging and Events

Approved messaging technologies:

- Kafka
- AWS SNS/SQS
- internal event buses

Rules:

- Messaging must be implemented through adapters
- Domain events must not depend on messaging libraries

---

# 8. Testing Stack

Primary testing tools:
```
pytest
pytest-bdd
httpx (for API integration tests)
pytest-mock (for dependency mocking)
```

Test categories:

- unit tests
- BDD integration tests
- contract tests

Testing must follow the rules defined in:
```
docs/architecture/TESTING.md
``` 

---

# 9. Development Tooling

Approved development tools include:
```
Ruff
SonarQube
Snyk
import-linter
pre-commit
```

These tools may be used by AI coding agents during planning and implementation to:

- detect structural complexity
- identify duplicated logic
- enforce architecture boundaries
- detect security vulnerabilities
- enforce linting and formatting rules

Tool findings should be treated as **blocking signals** when they violate project policies.

Configuration for these tools typically lives in:
```
pyproject.toml
.snyk
sonar-project.properties
.github/workflows/
```
Agent interaction rules for development tools are defined in:

`docs/architecture/AGENT_ARCHITECTURE.md`

---

# 10. Evaluation Framework

AI behavior evaluation is required when features use LLMs.

Evaluation standards and tooling:
```
docs/evaluation/eval_criteria.md   ← what must be evaluated (non-negotiable)
docs/evaluation/EVAL_STACK.md      ← approved tools and pipeline by environment
```

Feature-level configuration:
```
features/<feature_name>/eval_criteria.yaml
```

Evaluation includes:

- groundedness checks
- safety validation
- structural correctness
- CI evaluation gates

---

# 11. Observability

Approved tools:

- structured logging (`structlog`)
- metrics (`opentelemetry-sdk` + Prometheus exporter)
- distributed tracing (`opentelemetry-sdk`)

### Structured Logging

Use `structlog` for all application logging.

Rules:

- All log entries must be structured JSON in production
- logs must include `request_id`, `service`, and `layer` fields
- Domain layer may log domain events only — no infrastructure data
- Adapters may log infrastructure details (query times, connection errors, etc.)
- Use `structlog.get_logger(__name__)` — never `print()` or bare `logging`

### OpenTelemetry

Use `opentelemetry-sdk` to unify logs, metrics, and traces into a single pipeline exported to **Datadog** via the Datadog Agent (OTLP ingestion).

Approved packages:
```
opentelemetry-sdk
opentelemetry-api
opentelemetry-instrumentation-fastapi
opentelemetry-instrumentation-logging
opentelemetry-exporter-otlp
```

Rules:

- All three signals (logs, metrics, traces) are exported via `opentelemetry-exporter-otlp` → Datadog Agent
- `opentelemetry-instrumentation-logging` bridges `structlog` into the OTel log pipeline — no separate log shipper needed
- FastAPI instrumentation is automatic via `opentelemetry-instrumentation-fastapi`
- Adapters must emit spans for all external calls (DB, LLM, vector store)
- Domain services must not import OpenTelemetry directly — use an observability port
- Trace context (`trace_id`, `span_id`) is automatically injected into log entries via OTel logging bridge

### Observability Port

An outbound port (`ObservabilityPort`) must abstract logging and tracing from the domain:

- Domain calls port methods (e.g., `record_event`, `start_span`)
- Adapter implements the port using `structlog` + OpenTelemetry
- This keeps the domain layer infrastructure-agnostic (per architecture contract)


---

# 12. Static Analysis and Quality Gates

See Section 9 for approved tools. Rules enforced by those tools:

- architecture boundaries (`import-linter`)
- security issues (`Snyk`)
- duplication and complexity limits (`SonarQube`)
- formatting and linting (`Ruff` via `pre-commit`)

---

# 13. Dependency Rules

Approved dependency sources:

- PyPI
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
docs/architecture/ADR/TEMPLATE.md
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









