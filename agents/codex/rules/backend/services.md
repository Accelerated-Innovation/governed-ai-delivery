# Service Layer Rules

Services implement core business logic in alignment with Hexagonal Architecture.

## Purpose

- Encapsulate domain rules, state transitions, and orchestration
- Must not handle HTTP, serialization, or DB logic
- May call repositories (via outbound ports), validators, and injected helpers

## Structure

- One service per domain area (e.g., `UserService`, `PaymentService`)
- Classes must use the `Service` suffix
- Expose clear public methods named after business operations (e.g., `create_user()`)

## Dependencies

- Inject dependencies via constructor (no inline instantiation)
- Accept only ports and pure helpers — no adapters or framework code

```python
class UserService:
    def __init__(self, user_repo: UserPort):
        self.user_repo = user_repo
```

## Boundaries

Services must not import from `api/`, `adapters/`, or FastAPI. Services may raise domain exceptions and return DTOs or pure Python values.

## Testing

- Unit test all public methods in isolation
- Mock dependencies (repos, ports)
- Validate logic, not HTTP behavior

## Violations

- Business logic must never live in route handlers or adapter code
- All non-API, non-infrastructure logic belongs in the service layer
