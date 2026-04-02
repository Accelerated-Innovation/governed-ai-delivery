# Cross-Cutting Concerns

This document defines patterns for concerns that span multiple layers of the hexagonal architecture but must respect layer boundaries.

See also: [ARCH_CONTRACT.md](ARCH_CONTRACT.md), [BOUNDARIES.md](BOUNDARIES.md)

---

## 1. Data Transfer Objects (DTOs)

### Placement Rules

| DTO Type | Location | Owned By | Purpose |
|---|---|---|---|
| Request models | `api/` | API layer | Parse and validate inbound HTTP requests |
| Response models | `api/` | API layer | Shape outbound HTTP responses |
| Domain models | `services/` or `ports/` | Domain layer | Represent business entities and value objects |
| Persistence models | `adapters/` | Adapter layer | Map to/from database schemas |

### Rules

- Request and response models are **API-layer concerns** — domain code must not import them
- Domain models are **plain Python dataclasses or Pydantic models** with no framework dependencies
- Adapters convert between persistence models and domain models — this conversion lives in the adapter
- Never pass a request model directly to a domain service — map to domain types at the API boundary
- Never return a domain model directly as an HTTP response — map to a response model at the API boundary

### Example Flow

```
HTTP Request → Request Model (API) → Domain Model (Service) → Persistence Model (Adapter)
                                   ↓
HTTP Response ← Response Model (API) ← Domain Model (Service)
```

---

## 2. Validation Boundaries

### Where Validation Lives

| Validation Type | Layer | Mechanism |
|---|---|---|
| Request schema validation | API | Pydantic models (automatic via FastAPI) |
| Business rule validation | Domain (services) | Domain logic raises `ValidationError` |
| Persistence constraints | Adapter | Database constraints, caught and re-raised as domain exceptions |

### Rules

- Schema validation (field types, required fields, format) is handled by Pydantic at the API boundary — domain code does not re-validate these
- Business rule validation (e.g., "schema version must be > previous version") lives in domain services
- Domain services raise `ValidationError` for business rule violations (see [ERROR_MAPPING.md](ERROR_MAPPING.md))
- Adapters catch constraint violations (unique key, foreign key) and re-raise as domain exceptions (`ConflictError`, `ValidationError`)

### Anti-patterns

- Validating field types in domain services (Pydantic already did this)
- Catching database constraint errors in domain services (adapter responsibility)
- Adding business rules to Pydantic validators (leaks domain logic into API layer)

---

## 3. Pagination

### Standard Pattern

Use cursor-based or offset-based pagination at the API layer. Domain services return full result sets or accept pagination parameters as value objects.

```python
# Domain — pagination as a value object
@dataclass(frozen=True)
class PageRequest:
    offset: int = 0
    limit: int = 20

@dataclass(frozen=True)
class PageResult[T]:
    items: list[T]
    total: int
    offset: int
    limit: int
```

### API Response Shape

```json
{
  "items": [...],
  "total": 142,
  "offset": 0,
  "limit": 20
}
```

### Rules

- Pagination parameters are defined as domain value objects — not as raw ints passed through
- The API layer maps query parameters to `PageRequest`
- The adapter handles SQL `OFFSET`/`LIMIT` or cursor logic
- Default page size is 20; maximum is 100
- Total count is always returned (use `COUNT` query or estimate for large tables — document the approach in the adapter)

---

## 4. Timestamps and Time Handling

### Rules

- All timestamps stored and transmitted in **UTC**
- Use `datetime.datetime` with `tzinfo=datetime.UTC` — never naive datetimes
- Domain services receive a clock dependency for testability:

```python
from typing import Protocol
import datetime

class Clock(Protocol):
    def now(self) -> datetime.datetime: ...

class SystemClock:
    def now(self) -> datetime.datetime:
        return datetime.datetime.now(datetime.UTC)
```

- Inject `Clock` into services that need the current time — never call `datetime.now()` directly in domain code
- API layer converts to ISO 8601 strings in responses
- Adapters handle database-specific timestamp types

---

## 5. Soft Deletes

If soft deletes are required (determined by ADR), follow this pattern:

### Domain

```python
@dataclass
class SoftDeletable:
    deleted_at: datetime.datetime | None = None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

### Rules

- Domain services set `deleted_at` via the injected clock — never hard-delete
- Queries default to excluding soft-deleted records (adapter applies `WHERE deleted_at IS NULL`)
- Include-deleted queries require an explicit `include_deleted=True` parameter
- Hard deletion (permanent removal) requires a separate ADR and explicit authorization
- Soft delete does not change the entity's ID or version — it is a state transition

---

## 6. Audit Trails

If audit logging is required (determined by compliance requirements):

### Pattern

- Audit events are recorded via the `ObservabilityPort` (see [OBSERVABILITY_PORT_CONTRACT.md](OBSERVABILITY_PORT_CONTRACT.md))
- Audit entries include: actor identity, action, entity type, entity ID, timestamp, and before/after state
- Audit events are **append-only** — never modified or deleted
- Audit storage is an adapter concern — the domain calls the port

### Rules

- Never log PII in audit trails without explicit data classification approval
- Audit events are separate from application logs — use a distinct event name prefix (e.g., `audit.schema_published`)
- Audit trail completeness is verified by integration tests

---

## 7. Configuration

### Rules

- Configuration is loaded at application startup in the composition root — not in domain services
- Domain services receive configuration values via constructor injection
- Use Pydantic `BaseSettings` for environment-based configuration
- Secrets must not appear in logs, error messages, or API responses
- Feature flags (if used) are injected as a port — domain code calls the port, not a feature flag library
