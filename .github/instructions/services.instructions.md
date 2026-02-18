# Service Layer Instructions

Applies to all modules under `/services/**`. Services implement core business logic in alignment with Hexagonal Architecture.

---

## 1. Purpose

- Encapsulate domain rules, state transitions, and orchestration
- Must not handle HTTP, serialization, or DB logic
- May call:
  - Repositories (via outbound ports)
  - Validators and injected helpers
  - Other services via defined interfaces

---

## 2. Structure and Naming

- One service per domain area (e.g., `UserService`, `PaymentService`)
- Classes must use the `Service` suffix
- Expose clear public methods named after business operations (e.g., `create_user()`)

---

## 3. Dependencies

- Inject dependencies via constructor (no inline instantiation)
- Accept only ports and pure helpers (no adapters or framework code)

```python
class UserService:
    def __init__(self, user_repo: UserPort):
        self.user_repo = user_repo
```

---

## 4. Boundaries

- Services must not:
  - Import from `/api`, `/adapters`, or FastAPI
  - Reference request/response models
  - Access environment or global config directly
- Services may:
  - Raise domain exceptions
  - Return DTOs or pure Python values

---

## 5. Error Handling

- Raise custom exceptions (e.g., `UserAlreadyExistsError`)
- Never raise `HTTPException` or adapter-specific errors

---

## 6. Logging

- Use structured logging with `event`, `user_id`, and `service_name`
- Do not log secrets or raw tokens

---

## 7. Testing

- Unit test all public methods in isolation
- Mock dependencies (e.g., repos, ports)
- Validate logic, not HTTP behavior

---

## 8. Cross-Cutting Concerns

- Handle retries, caching, and async dispatch using decorators
- Services must remain stateless
- Long-running work must be delegated to jobs/tasks (e.g., Celery, RQ)

---

## 9. Violations

- Business logic must never live in route handlers or adapter code
- Logic found in `/api` or `/repos` should be moved to a service
- All non-API, non-infrastructure logic belongs in the service layer