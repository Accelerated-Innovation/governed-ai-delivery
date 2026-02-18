# FastAPI API Design Instructions

Applies to all inbound adapter files under `/api/**`. Route handlers are responsible for HTTP concerns only. All domain logic must be delegated to inbound ports.

---

## 0. Interaction with Domain

* Handlers must call **inbound ports** (interfaces) from `ports/inbound/`
* Do **not** call service implementations or business logic directly
* Use dependency injection or wiring to bind ports to adapter implementations
* Inputs (e.g., request models, auth) must be mapped to domain objects before calling ports
* Ports return results or raise domain exceptions; handlers translate those into HTTP responses

---

## 1. Routing

* Use path-style: `/v1/<resource>/<action>` (e.g. `/v1/users/reset-password`)
* Use FastAPI's `@router` pattern with clearly named `APIRouter` objects per module
* Avoid inline route declarations in `main.py`

---

## 2. HTTP Verbs & Status Codes

* Use FastAPI’s `@get`, `@post`, `@put`, `@delete` decorators
* Required status codes:

  * `200`: Successful GET
  * `201`: Resource created
  * `204`: No content on DELETE
  * `400`: Validation failure
  * `401`: Authentication required
  * `403`: Unauthorized access
  * `404`: Not found
  * `422`: FastAPI validation error
  * `500`: Unexpected server exceptions only

---

## 3. Request & Response Format

* Request models must inherit from `BaseModel`
* Map request models to domain inputs before calling a port
* Wrap all responses in a standard envelope:

```python
class ApiResponse(BaseModel):
    data: Optional[Any]
    error: Optional[ErrorInfo]
```

* Avoid returning raw `dict` or untyped `Response` objects

---

## 4. Error Handling

* Ports may raise domain exceptions
* Use exception handlers or middleware to convert domain errors to `HTTPException`

```python
raise HTTPException(status_code=400, detail={"code": "INVALID_INPUT", "message": "Invalid email"})
```

* Centralize exception logging
* Never expose stack traces or internal error details in HTTP responses

---

## 5. Authentication & Authorization

* Use `Depends(get_current_user)` for all protected routes
* Auth must be enforced before calling any port
* Pass a structured identity context into the port call (e.g., `UserContext`)
* Do not let domain logic depend on auth libraries
* Include `user_id` in all logs and telemetry

---

## 6. Observability

* Use structured logging with:

  * `event`, `path`, `status_code`, `duration_ms`
* Include `request_id` and `user_id` where available
* Time all requests with middleware
* Expose metrics via `/metrics` using `prometheus_fastapi_instrumentator`

---

## 7. OpenAPI Spec

* Every endpoint must include:

  * Summary
  * Description
  * Response model
  * Status code docs

* Use FastAPI’s `response_model=...` correctly

* Annotate query/body params with `Field(...)` and descriptions

* Validate OpenAPI schema in CI

---

## 8. Testing

* Use `pytest` and `TestClient` for route tests

* Every route must have:

  * Input validation tests
  * Auth tests (unauthenticated, unauthorized)
  * Response shape tests
  * Port mock assertions

* Use `httpx.AsyncClient` for async testing

---

## 9. Adapter Boundaries

* `/api/**` may import:

  * `ports/inbound/**`
  * domain DTOs and enums
  * common logging or metrics utils

* `/api/**` may **not** import:

  * adapter implementations
  * outbound port interfaces
  * service logic from other adapters

* All boundaries are enforced via `import-linter`
