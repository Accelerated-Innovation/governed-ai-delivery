# Architecture Contract

This contract defines mandatory architectural standards for this codebase. All Copilot agents, contributors, and tools must follow these constraints during planning and development.

## 1. Architectural Style

This codebase follows Hexagonal Architecture (also known as Ports and Adapters).

### Core Concepts:

* **Domain**: Pure business logic and entities
* **Ports**: Interfaces the domain exposes (inbound) and depends on (outbound)
* **Adapters**: Implementations of ports, including APIs, UIs, databases, queues, etc.

## 2. Layering

### Domain Core

* Contains: `services`, `models`, `use_cases`
* Must have no external dependencies other than standard Python and `typing`
* All logic must be framework-agnostic and testable in isolation

### Ports

* Inbound ports: defined in `ports/inbound/` (e.g., `UserServicePort`)
* Outbound ports: defined in `ports/outbound/` (e.g., `UserRepositoryPort`)
* All ports are pure Python interfaces (ABC or `Protocol`)

### Adapters

* Inbound adapters (e.g., HTTP): `api/`
* Outbound adapters (e.g., DB, Redis, external services): `adapters/`
* Adapters implement ports and depend on the domain, never the reverse

## 3. Boundaries

* Domain must not import from adapters
* Adapters may import from domain and ports
* Cross-module calls must go through interfaces (ports)
* Enforced via `import-linter` and PR review

## 4. Dependencies

* Approved libraries:

  * Domain: standard Python, Pydantic (for type safety)
  * Adapters:

    * HTTP: FastAPI
    * DB: SQLAlchemy, Redis client
    * External APIs: `httpx`, `boto3`
* No circular imports
* Third-party libraries in the domain layer require an ADR

## 5. ADR Rules

An ADR is required when:

* Adding a new port or adapter
* Modifying a domain contract
* Changing dependency rules or boundaries
* Introducing new architectural patterns

Template: `docs/architecture/ADR/TEMPLATE.md`
Location: `docs/architecture/ADR/`

## 6. Design Principles

* Follow SOLID principles in all layers
* Ports must define clear contracts
* Adapters must be loosely coupled and easily swappable
* Domain logic must be stateless and injectable

## 7. Security

* Auth and identity are implemented in adapters
* All JWT validation and permission checks must occur before domain logic is invoked
* Secrets and config must use environment variables via `BaseSettings`
* No logging of credentials, tokens, or PII

## 8. Observability

* All adapters must emit structured logs with:

  * `event`, `layer`, `adapter`, `user_id`, `request_id`
* Include tracing headers and span IDs
* Metrics exposed via Prometheus endpoints
* Do not emit logs from the domain layer

## 9. Testing Policy

* Domain: 100% unit test coverage
* Ports: interface tests
* Adapters: integration + contract tests
* End-to-end tests for key flows
* All tests must run in CI and must pass before merge

## 10. Review & Enforcement

* PRs must comply with this contract
* Violations require a documented ADR
* Copilot must cite this contract when generating plans or code
* import-linter and test gates are enforced in CI
