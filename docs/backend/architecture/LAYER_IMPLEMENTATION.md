# Layer Implementation Guide

This document provides a consolidated reference for implementing each layer in the hexagonal architecture. For comprehensive guidance on any layer, see the references at the bottom of each section.

---

## Overview

The system uses **Hexagonal Architecture** with these layers:

```
┌─────────────────────────┐
│   Adapters (Inbound)    │  api/, cli/
├─────────────────────────┤
│  Ports (Interfaces)     │  ports/inbound/, ports/outbound/
├─────────────────────────┤
│  Domain (Core Logic)    │  services/, models/
├─────────────────────────┤
│   Adapters (Outbound)   │  adapters/
└─────────────────────────┘
```

All communication goes through ports. Adapters never talk directly to each other.

---

## 1. Domain Layer

**Location:** `src/domain/services/`, `src/domain/models/`

**Role:** Pure business logic and state management. The core of the system.

### Hard Rules

- **No external dependencies** — only standard library and Pydantic (for types)
- **No framework references** — FastAPI, SQLAlchemy, Redis, etc. must never appear
- **Dependency injection only** — all external systems injected via constructor
- **Stateless functions** — business logic as pure functions where possible
- **Domain-specific exceptions** — raise exceptions that adapters can understand
- **Interfaces (ports) only** — no implementation details in domain code

### Examples

```python
# ✓ Good — pure domain logic, injected dependencies
class UserService:
    def __init__(self, repo: UserRepository):  # port (interface)
        self.repo = repo
    
    def activate_user(self, user_id: str) -> User:
        user = self.repo.get(user_id)
        user.activate()
        self.repo.save(user)
        return user

# ✗ Bad — framework references, hardcoded dependencies
class UserService:
    def __init__(self):
        self.db = SQLAlchemy()  # hardcoded, not injected
    
    @route('/users/{id}/activate')  # framework decorator in domain
    def activate_user(self, id: str):
        ...
```

### Testing

- Unit test all public methods
- Mock all injected port dependencies
- No database, HTTP, or external service calls
- Fast and isolated

**Reference:** `docs/backend/architecture/ARCH_CONTRACT.md`

---

## 2. Port Layer

**Location:** `src/ports/inbound/`, `src/ports/outbound/`

**Role:** Define contracts between domain and adapters. Adapters implement these, domain depends on them.

### Inbound Ports

Define how the domain is called (use cases, entry points).

```python
# ports/inbound/user_service_port.py
from abc import ABC, abstractmethod
from typing import Optional
from domain.models import User

class UserServicePort(ABC):
    @abstractmethod
    def activate_user(self, user_id: str) -> User:
        """Activate a user account."""
        pass
    
    @abstractmethod
    def get_user(self, user_id: str) -> Optional[User]:
        """Retrieve a user by ID."""
        pass
```

### Outbound Ports

Define what external systems the domain depends on (storage, APIs, messaging).

```python
# ports/outbound/user_repository_port.py
from abc import ABC, abstractmethod
from domain.models import User

class UserRepositoryPort(ABC):
    @abstractmethod
    def get(self, user_id: str) -> Optional[User]:
        """Retrieve from storage."""
        pass
    
    @abstractmethod
    def save(self, user: User) -> None:
        """Persist to storage."""
        pass
```

### Hard Rules

- **Interface only** — no implementation logic, no side effects
- **Framework-agnostic** — no web framework, ORM, database references
- **Domain types only** — use domain models, DTOs, exceptions — not raw framework types
- **Single concern** — one port per interface/contract
- **Bidirectional** — inbound ports called by adapters; outbound ports implemented by adapters

### Testing

- Ports themselves don't require tests
- Adapter implementations tested in isolation against their port contract
- Integration tests verify adapters work with real infrastructure

**Reference:** `docs/backend/architecture/BOUNDARIES.md`

---

## 3. Inbound Adapter Layer (API / CLI)

**Location:** `src/api/`, `src/cli/`

**Role:** Handle external input (HTTP requests, CLI commands) and delegate to domain via inbound ports.

### API Layer (HTTP)

```python
# api/users.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ports.inbound import UserServicePort

router = APIRouter(prefix="/v1/users", tags=["users"])

class ActivateUserRequest(BaseModel):
    user_id: str

@router.post("/{user_id}/activate")
async def activate_user(user_id: str, user_service: UserServicePort) -> dict:
    try:
        user = user_service.activate_user(user_id)
        return {"data": {"id": user.id, "status": user.status}}
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except UserAlreadyActiveError:
        raise HTTPException(status_code=400, detail="User already active")
```

### CLI Layer

See `docs/backend/architecture/CLI_CONVENTIONS.md` for detailed CLI guidance.

```python
# cli/users.py
import click
from ports.inbound import UserServicePort

@click.group()
def users():
    """User management commands."""
    pass

@users.command()
@click.argument('user_id')
def activate(user_id: str, user_service: UserServicePort):
    """Activate a user account."""
    try:
        user = user_service.activate_user(user_id)
        click.echo(f"Activated user {user.id}")
    except UserNotFoundError:
        click.echo(f"Error: User {user_id} not found", err=True)
        raise SystemExit(1)
```

### Hard Rules

- **Thin adapters** — validate input, call inbound port, translate response
- **No business logic** — all logic lives in the domain
- **Port delegation** — all work goes through inbound ports
- **Type translation** — convert HTTP/CLI types to domain types before calling port
- **Exception mapping** — catch domain exceptions, translate to HTTP status codes or CLI exit codes
- **Authentication/validation first** — validate and authenticate before calling the port

### Testing

- Test each handler in isolation
- Mock the inbound port
- Verify HTTP status codes and response formats
- Verify exception → error code mapping

**Reference:** 
- `docs/backend/architecture/API_CONVENTIONS.md` (FastAPI-specific)
- `docs/backend/architecture/CLI_CONVENTIONS.md` (CLI-specific)

---

## 4. Outbound Adapter Layer

**Location:** `src/adapters/`

**Role:** Implement outbound ports. Connect the domain to external systems (databases, APIs, caches, message queues).

### Structure

```
adapters/
├── postgres/          # Database adapter
│   ├── user_repository.py
│   └── connection.py
├── redis/             # Cache adapter
│   └── cache_adapter.py
├── stripe/            # External API adapter
│   └── payment_adapter.py
└── email/             # Email service adapter
    └── email_adapter.py
```

### Example Implementation

```python
# adapters/postgres/user_repository.py
from sqlalchemy.orm import Session
from ports.outbound import UserRepositoryPort
from domain.models import User
from domain.exceptions import UserNotFoundError

class PostgresUserRepository(UserRepositoryPort):
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get(self, user_id: str) -> Optional[User]:
        row = self.db.query(UserTable).filter_by(id=user_id).first()
        if not row:
            raise UserNotFoundError(f"User {user_id} not found")
        return User(id=row.id, email=row.email, status=row.status)
    
    def save(self, user: User) -> None:
        row = self.db.query(UserTable).filter_by(id=user.id).first()
        if row:
            row.email = user.email
            row.status = user.status
        else:
            row = UserTable(id=user.id, email=user.email, status=user.status)
            self.db.add(row)
        self.db.commit()
```

### Hard Rules

- **Port implementation only** — implement the interface you're adapting
- **No business logic** — translation and integration only
- **No cross-adapter calls** — each adapter is independent
- **Framework types stay here** — don't leak SQLAlchemy, Redis, HTTP library types to the domain
- **Dependency injection** — adapters are wired up by a composition root (DI container), not instantiated inline
- **Exception translation** — catch infrastructure exceptions, raise domain exceptions

### Testing

- **Unit tests:** Mock external services (databases, APIs)
- **Integration tests:** Use real infrastructure (test database, Redis, external APIs)
- **Contract tests:** Verify adapter satisfies its port interface

**Reference:** `docs/backend/architecture/BOUNDARIES.md`

---

## 5. Composition Root (Dependency Injection)

**Location:** `src/main.py` or `src/config/di.py`

**Role:** Wire up all adapters and ports. This is the only place framework and adapter instantiation happens.

```python
# main.py or config/di.py
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from ports.inbound import UserServicePort
from ports.outbound import UserRepositoryPort
from domain.services import UserService
from adapters.postgres import PostgresUserRepository

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_service(db: Session = Depends(get_db)) -> UserServicePort:
    repo = PostgresUserRepository(db)
    return UserService(repo)

app = FastAPI()

@app.get("/users/{id}/activate")
async def activate(id: str, user_service: UserServicePort = Depends(get_user_service)):
    user = user_service.activate_user(id)
    return {"data": user.to_dict()}
```

### Hard Rules

- **Single location** — all wiring in one place
- **No adapters in domain** — adapters only instantiated here
- **Dependency chain clear** — easy to see what depends on what

---

## 6. Cross-Cutting Concerns

**Location:** `src/common/`

**Role:** Shared utilities, DTOs, logging, tracing, error handling.

```
common/
├── dto.py              # Data transfer objects
├── exceptions.py       # Domain exceptions
├── logging.py          # Logging setup
├── observability.py    # Tracing, metrics
└── validators.py       # Reusable validation
```

### Hard Rules

- **Dependency-free** — common cannot import from any other layer
- **No business logic** — utilities and shared types only
- **Used by all layers** — domain, ports, adapters all use common

---

## 7. Dependency Rules

All dependencies flow **downward only** (with exceptions for ports):

```
┌──────────────────────────┐
│  API / CLI Adapters      │  ↓ can import domain, ports, common
├──────────────────────────┤
│  Ports (Inbound/Outbound)│  ↓ can import domain, common
├──────────────────────────┤
│  Domain Services         │  ↓ can import common only
├──────────────────────────┤
│  Outbound Adapters       │  ↓ can import domain, ports, common
├──────────────────────────┤
│  Common (Utils)          │  ↓ no dependencies
└──────────────────────────┘
```

### Forbidden Imports

- ❌ Domain → Adapters
- ❌ Domain → API/CLI
- ❌ Adapter → Adapter (cross-adapter)
- ❌ Common → Anything

Enforced via `import-linter`. Violations require an ADR.

---

## 8. Testing by Layer

| Layer | Type | Dependencies | Speed |
|-------|------|--------------|-------|
| Domain | Unit | All mocked | Fast |
| Ports | Contract | N/A | N/A |
| API/CLI | Unit + Integration | Mocked + Real | Medium |
| Outbound Adapters | Unit + Integration | Mocked + Real | Medium/Slow |

All tests must satisfy **FIRST principles** and be deterministic.

See `docs/backend/architecture/TESTING.md` for complete testing guidance.

---

## 9. Summary Table

| Layer | Owns | Imports From | Cannot Import From | Key Responsibility |
|-------|------|--------------|-------------------|-------------------|
| **Domain** | services, models | common | adapters, ports, frameworks | Business logic |
| **Ports** | inbound, outbound | domain, common | adapters, frameworks | Contracts |
| **API/CLI** | routes, handlers | ports, common | domain impl | HTTP/CLI concerns |
| **Adapters** | DB, cache, external | domain, ports, common | other adapters | Infrastructure |
| **Common** | utils, DTOs, errors | (none) | any layer | Shared types |

---

## 10. References

- **High-level architecture:** `ARCH_CONTRACT.md`
- **Module boundaries:** `BOUNDARIES.md`
- **API conventions:** `API_CONVENTIONS.md` (FastAPI-specific)
- **CLI conventions:** `CLI_CONVENTIONS.md`
- **Testing standards:** `TESTING.md`
- **Error handling:** `ERROR_MAPPING.md`
- **Cross-repo features:** `../../CROSS_REPO_FEATURES.md`

---

## 11. Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---------|----------------|-----|
| Domain imports SQLAlchemy | Couples domain to infrastructure | Use outbound ports |
| Adapter calls another adapter | Creates implicit dependencies | Go through ports |
| API calls service directly | Violates port contract | Call inbound port |
| Putting logic in API layer | Mixes concerns | Move to domain service |
| Not injecting dependencies | Makes testing hard | Use constructor injection |
| Circular imports | Breaks architecture | Refactor to use ports |
| Putting exceptions in common | Couples layers inappropriately | Domain exceptions in domain |

---

## 12. Getting Help

- **"Where should this live?"** → See the layer summary above and reference table
- **"What can X import?"** → See dependency rules section
- **"How do I test this?"** → See testing by layer section
- **"How do I add a new adapter?"** → Create port, implement in adapter, inject in composition root, write tests
