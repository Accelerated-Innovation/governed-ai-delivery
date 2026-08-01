# Architectural Boundaries

This document defines module boundaries, allowed dependencies, and ownership rules within a single repository. These boundaries enforce Hexagonal Architecture. All violations must be approved via ADR.

**Note on multi-repository features:** These layer boundaries apply *within* a single repository. For features spanning multiple repositories, see [CROSS_REPO_FEATURES.md](../../CROSS_REPO_FEATURES.md) and [REPO_SCOPE_ANALYSIS_GUIDANCE.md](../../REPO_SCOPE_ANALYSIS_GUIDANCE.md). Repository-level boundaries (which repo owns which modules) are separate from layer-level boundaries (which layer owns which abstractions).

## 1. Architectural Model

This system uses Hexagonal Architecture (Ports and Adapters). Primary layers:

* `api/` – inbound adapters (HTTP interfaces, webhooks)
* `ports/` – inbound and outbound interface definitions
* `services/` – domain behaviour and orchestration
* `models/` – domain entities and value objects
* `adapters/` – implementations of outbound ports (e.g. DB, Redis, LLM providers)
* `common/` – cross-cutting concerns (logging, tracing, DTOs)

The domain is `services/` (behaviour) plus `models/` (state). There is no
`domain/` package — see [ARCH_CONTRACT.md](ARCH_CONTRACT.md) section 2.

## 2. Allowed Dependencies

| Module       | Allowed to import from                  |
| ------------ | --------------------------------------- |
| `api/`       | `ports/inbound/`, `models/`, `common/`  |
| `adapters/`  | `ports/`, `services/`, `models/`, `common/` |
| `services/`  | `ports/`, `models/`, `common/`          |
| `ports/`     | `models/`, `common/`                    |
| `models/`    | `common/` only                          |
| `common/`    | none (must be dependency-free)          |

`ports/` sits **below** `services/`: ports hold interfaces and may reference
entities, while services import the port interfaces they depend on. Granting
`ports/ → services/` as well would create the cycle forbidden below.

`api/` may name entities because inbound port signatures carry them, but it
must never reach into `services/` — all behaviour is invoked through
`ports/inbound/`.

### Forbidden:

* `api` importing `services` directly → ❌
* `services` or `models` importing any adapter → ❌
* `models` importing `ports` or `services` → ❌
* `adapters` reaching across layers horizontally → ❌
* Circular dependencies between ports and services → ❌

All are enforced by the boundary-enforcement tool your stack uses — named in
`TECH_STACK.md` and configured as described in `LAYER_IMPLEMENTATION.md` — and
by PR review. The rules above are the same for every stack; only the tool that
checks them differs.

## 3. Communication Rules

* Only `ports/inbound/` define entrypoints to the domain
* `api/` may only call inbound ports
* `adapters/` implement outbound ports, injected into the domain
* No adapter may contain orchestration or core logic

## 4. Module Isolation

* Each adapter implements only its own port
* `services/` must never reference specific adapters
* `models/` must stay free of behaviour that belongs in `services/`
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
