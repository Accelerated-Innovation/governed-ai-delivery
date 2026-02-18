# Architectural Boundaries

This document defines module boundaries, allowed dependencies, and ownership rules. These boundaries enforce Hexagonal Architecture. All violations must be approved via ADR.

## 1. Architectural Model

This system uses Hexagonal Architecture (Ports and Adapters). Primary layers:

* `domain/` – core business logic
* `ports/` – inbound and outbound interface definitions
* `adapters/` – implementations of ports (e.g. FastAPI, DB, Redis)
* `common/` – cross-cutting concerns (logging, tracing, DTOs)

## 2. Allowed Dependencies

| Module      | Allowed to import from         |
| ----------- | ------------------------------ |
| `api/`      | `ports/inbound/`, `common/`    |
| `adapters/` | `ports/`, `domain/`, `common/` |
| `ports/`    | `domain/`, `common/`           |
| `domain/`   | `common/` only                 |
| `common/`   | none (must be dependency-free) |

### Forbidden:

* `api` importing `domain` directly → ❌
* `domain` importing any adapter → ❌
* `adapters` reaching across layers horizontally → ❌
* Circular dependencies between ports and adapters → ❌

All are enforced with `import-linter`.

## 3. Communication Rules

* Only `ports/inbound/` define entrypoints to the domain
* `api/` may only call inbound ports
* `adapters/` implement outbound ports, injected into the domain
* No adapter may contain orchestration or core logic

## 4. Module Isolation

* Each adapter implements only its own port
* `domain` logic must never reference specific adapters
* `ports/` must remain interface-only — no logic or side effects

## 5. Ownership

| Folder              | Owner         |
| ------------------- | ------------- |
| `services/user/`    | Identity Team |
| `services/payment/` | Payments Team |
| `api/admin/`        | Platform Team |
| `adapters/stripe/`  | Payments Team |
| `adapters/redis/`   | Infra Team    |

Cross-boundary changes require explicit review from the responsible team.

## 6. Enforcement

CI will fail on:

* Forbidden imports
* Port-to-implementation coupling
* Leaky abstractions (e.g. domain uses SQLAlchemy)

Resolution requires either:

* Refactor to comply
* ADR with rationale, tradeoffs, and rollback path
