# Error Mapping Contract

This document defines how domain exceptions map to HTTP responses at the API adapter boundary.

See also: [API_CONVENTIONS.md](API_CONVENTIONS.md), [ARCH_CONTRACT.md](ARCH_CONTRACT.md)

---

## 1. Principle

Domain services raise **domain exceptions**. The API layer (inbound adapter) catches them and maps to HTTP responses. Domain code must never import `HTTPException` or any framework-specific error type.

---

## 2. Domain Exception Hierarchy

All domain exceptions inherit from a common base:

```python
class DomainError(Exception):
    """Base class for all domain exceptions."""
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code  # Machine-readable error code (e.g., "SCHEMA_CONFLICT")
```

### Standard Domain Exceptions

| Exception | Meaning | HTTP Status |
|---|---|---|
| `NotFoundError` | Requested entity does not exist | 404 |
| `ConflictError` | Operation conflicts with current state (e.g., duplicate, version mismatch) | 409 |
| `ValidationError` | Input violates domain rules (not schema validation — that's the API layer) | 422 |
| `AuthorizationError` | Caller lacks permission for this operation | 403 |
| `ExternalServiceError` | An outbound dependency failed (after retries) | 502 |
| `RateLimitError` | Caller has exceeded allowed request rate | 429 |
| `DomainError` (base) | Catch-all for unclassified domain failures | 500 |

---

## 3. HTTP Error Response Shape

All error responses follow a consistent structure:

```json
{
  "error": {
    "code": "SCHEMA_CONFLICT",
    "message": "Schema version 3 already exists and is immutable",
    "details": {}
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `error.code` | string | Yes | Machine-readable error code, UPPER_SNAKE_CASE |
| `error.message` | string | Yes | Human-readable description |
| `error.details` | object | No | Additional context (field errors, constraint details) |

---

## 4. API Exception Handler

Implement a centralized exception handler in the API layer:

```python
from fastapi import Request
from fastapi.responses import JSONResponse

DOMAIN_TO_HTTP = {
    NotFoundError: 404,
    ConflictError: 409,
    ValidationError: 422,
    AuthorizationError: 403,
    ExternalServiceError: 502,
    RateLimitError: 429,
}

async def domain_exception_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_code = DOMAIN_TO_HTTP.get(type(exc), 500)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.code or type(exc).__name__.upper(),
                "message": str(exc),
            }
        },
    )

# Register in FastAPI app setup:
# app.add_exception_handler(DomainError, domain_exception_handler)
```

---

## 5. Rules

- Domain code raises domain exceptions — never HTTP exceptions
- The API layer maps domain exceptions to HTTP responses — domain code does not choose status codes
- Every domain exception must have a corresponding entry in the mapping table above
- New exception types require updating this document and the exception handler
- `ValidationError` is for domain-level validation (business rules), not for request schema validation (which FastAPI handles via Pydantic)
- Never expose stack traces or internal paths in error responses
- Log the full exception (including stack trace) server-side via the observability port

---

## 6. Adapter Errors

Adapter-level errors (database connection failures, HTTP timeouts to external services) should be caught in the adapter and re-raised as domain exceptions:

```python
class HttpSchemaRegistryAdapter:
    def publish(self, schema_id: str, version: int, body: dict) -> None:
        try:
            response = self._client.post(...)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                raise ConflictError(f"Schema {schema_id} v{version} already exists", code="SCHEMA_CONFLICT")
            raise ExternalServiceError(f"Registry returned {e.response.status_code}", code="REGISTRY_ERROR")
        except httpx.ConnectError:
            raise ExternalServiceError("Schema registry unavailable", code="REGISTRY_UNAVAILABLE")
```

This keeps the domain layer unaware of HTTP, database, or messaging specifics.
