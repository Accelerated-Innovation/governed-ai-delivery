# Layer Implementation Guide

This document provides a consolidated reference for implementing each layer in the hexagonal architecture.

---

## Overview

The system uses **Hexagonal Architecture** with these layers:

```
┌─────────────────────────┐
│   Adapters (Inbound)    │  internal/api/
├─────────────────────────┤
│  Ports (Interfaces)     │  internal/ports/
├─────────────────────────┤
│  Domain (Core Logic)    │  internal/domain/
├─────────────────────────┤
│   Adapters (Outbound)   │  internal/adapters/
└─────────────────────────┘
```

All communication goes through ports. Adapters never talk directly to each other.

---

## 1. Domain Layer

**Location:** `internal/domain/services/`, `internal/domain/models/`

**Role:** Pure business logic and state management. The core of the system.

### Hard Rules

- **No external dependencies** — only Go standard library (`errors`, `fmt`, `context`)
- **No framework references** — Gin, pgx, go-redis, zap, etc. must never appear
- **Dependency injection only** — all external systems injected via constructor
- **Stateless functions** — business logic as pure functions where possible
- **Domain-specific errors** — define sentinel errors or custom error types that adapters map to infrastructure errors
- **Interfaces (ports) only** — no implementation details in domain code

### Examples

```go
// ✓ Good — pure domain logic, injected dependencies
type UserService struct {
    repo UserRepository // port (interface), not a concrete type
}

func NewUserService(repo UserRepository) *UserService {
    return &UserService{repo: repo}
}

func (s *UserService) ActivateUser(ctx context.Context, userID string, identity UserContext) (*User, error) {
    user, err := s.repo.FindByID(ctx, userID)
    if err != nil {
        return nil, fmt.Errorf("finding user: %w", err)
    }
    if user == nil {
        return nil, ErrUserNotFound
    }
    if err := user.Activate(); err != nil {
        return nil, err
    }
    if err := s.repo.Save(ctx, user); err != nil {
        return nil, fmt.Errorf("saving user: %w", err)
    }
    return user, nil
}

// ✗ Bad — framework references, hardcoded dependencies
func (s *UserService) ActivateUser(c *gin.Context) { // Gin type in domain
    row, _ := pgxpool.Query(ctx, "SELECT ...")       // hardcoded DB call
    ...
}
```

### Testing

- Unit test all public methods with `go test` + `testify/assert`
- Mock all injected port interfaces with `testify/mock`
- No database, HTTP, or external service calls
- Fast and isolated

**Reference:** `docs/backend/architecture/ARCH_CONTRACT.md`

---

## 2. Port Layer

**Location:** `internal/ports/`

**Role:** Define contracts between domain and adapters via Go interfaces.

### Inbound Ports

```go
// internal/ports/user_service_port.go
type UserServicePort interface {
    ActivateUser(ctx context.Context, userID string, identity UserContext) (*domain.User, error)
    GetUser(ctx context.Context, userID string) (*domain.User, error)
}
```

### Outbound Ports

```go
// internal/ports/user_repository.go
type UserRepository interface {
    FindByID(ctx context.Context, userID string) (*domain.User, error)
    Save(ctx context.Context, user *domain.User) error
}
```

### Hard Rules

- **Interface only** — no struct fields, no implementation
- **Framework-agnostic** — no Gin, pgx, or infrastructure types in method signatures
- **Domain types only** — use domain models, custom errors — not `map[string]any`
- **Single concern** — one interface per contract

**Reference:** `docs/backend/architecture/BOUNDARIES.md`

---

## 3. Inbound Adapter Layer (API)

**Location:** `internal/api/`

**Role:** Handle HTTP requests and delegate to domain via inbound ports.

```go
// internal/api/user_handler.go
type UserHandler struct {
    userService ports.UserServicePort
}

func NewUserHandler(svc ports.UserServicePort) *UserHandler {
    return &UserHandler{userService: svc}
}

// ActivateUser godoc
// @Summary Activate a user account
// @Router  /v1/users/{userId}/activate [post]
func (h *UserHandler) ActivateUser(c *gin.Context) {
    identity, _ := c.MustGet("identity").(domain.UserContext)

    user, err := h.userService.ActivateUser(c.Request.Context(), c.Param("userId"), identity)
    if err != nil {
        if errors.Is(err, domain.ErrUserNotFound) {
            c.JSON(http.StatusNotFound, problemDetail(404, "User Not Found", err.Error()))
            return
        }
        c.JSON(http.StatusInternalServerError, problemDetail(500, "Internal Error", ""))
        return
    }

    c.JSON(http.StatusOK, APIResponse[UserDTO]{Data: userDTOFrom(user)})
}
```

### Hard Rules

- **Thin handlers** — validate input, call inbound port, translate response
- **No business logic** — all logic lives in the domain
- **Error mapping** — `errors.Is` to map domain errors to HTTP status codes
- **Authentication/validation first** — validate before calling the port

### Testing

- Use `net/http/httptest` with `router.ServeHTTP(w, req)`
- Mock the port with `testify/mock`

**Reference:** `docs/backend/architecture/API_CONVENTIONS.md`

---

## 4. Outbound Adapter Layer

**Location:** `internal/adapters/`

**Role:** Implement outbound ports. Connect domain to external systems.

### Structure

```
internal/adapters/
├── postgres/                  # pgx-based repository adapter
│   ├── user_repository.go     # implements ports.UserRepository
│   └── queries.sql.go         # sqlc-generated query functions (if using sqlc)
├── redis/                     # go-redis cache adapter
│   └── cache_adapter.go
├── stripe/                    # External API adapter
│   └── payment_adapter.go
└── email/                     # Email service adapter
    └── sendgrid_adapter.go
```

### Example Implementation

```go
// internal/adapters/postgres/user_repository.go
type PostgresUserRepository struct {
    pool *pgxpool.Pool
}

func NewPostgresUserRepository(pool *pgxpool.Pool) *PostgresUserRepository {
    return &PostgresUserRepository{pool: pool}
}

func (r *PostgresUserRepository) FindByID(ctx context.Context, userID string) (*domain.User, error) {
    row := r.pool.QueryRow(ctx,
        "SELECT id, email, status FROM users WHERE id = $1", userID)

    var id, email, status string
    if err := row.Scan(&id, &email, &status); err != nil {
        if errors.Is(err, pgx.ErrNoRows) {
            return nil, nil
        }
        return nil, fmt.Errorf("querying user: %w", err)
    }
    return &domain.User{ID: id, Email: email, Status: domain.UserStatus(status)}, nil
}

func (r *PostgresUserRepository) Save(ctx context.Context, user *domain.User) error {
    _, err := r.pool.Exec(ctx,
        `INSERT INTO users (id, email, status) VALUES ($1, $2, $3)
         ON CONFLICT (id) DO UPDATE SET email = $2, status = $3`,
        user.ID, user.Email, string(user.Status))
    return err
}
```

### Hard Rules

- **Port implementation only** — implement the interface you're adapting
- **No business logic** — translation and integration only
- **No cross-adapter calls** — each adapter is independent
- **pgx / ORM types stay here** — don't leak pgx rows or Redis commands to the domain
- **Error wrapping** — wrap infrastructure errors with `fmt.Errorf("context: %w", err)`

### Testing

- **Unit tests:** Mock the pgxpool with testify/mock or replace with in-memory fake
- **Integration tests:** Use Testcontainers-Go for real PostgreSQL / Redis
- **Contract tests:** Verify adapter satisfies its port interface

**Reference:** `docs/backend/architecture/BOUNDARIES.md`

---

## 5. Composition Root (Dependency Injection)

**Location:** `cmd/api/main.go` or `internal/app/app.go`

Wire up all adapters, ports, and handlers manually or via `google/wire`:

```go
// cmd/api/main.go
func main() {
    pool := connectDB()
    userRepo := postgres.NewPostgresUserRepository(pool)
    userService := services.NewUserService(userRepo)
    userHandler := api.NewUserHandler(userService)

    router := gin.Default()
    router.Use(api.AuthMiddleware(jwtSecret))
    router.POST("/v1/users/:userId/activate", userHandler.ActivateUser)

    router.Run(":8080")
}
```

### Hard Rules

- **Single location** — all wiring in `main.go` or a dedicated wiring file
- **No adapters in domain** — only instantiated here
- **Dependency chain clear** — easy to trace what depends on what

---

## 6. Cross-Cutting Concerns

**Location:** `internal/common/`

```
internal/common/
├── dto.go              # Data transfer objects
├── errors.go           # Domain sentinel errors
├── logging.go          # zap.Logger setup
├── observability.go    # OTel tracing helpers
└── validation.go       # Reusable validators
```

### Hard Rules

- **No imports from other internal layers** — common cannot import from `domain`, `adapters`, or `api`
- **No business logic** — utilities and shared types only

---

## 7. Dependency Rules

```
┌──────────────────────────┐
│  API Handlers            │  → can import ports, common + Gin
├──────────────────────────┤
│  Ports (Interfaces)      │  → can import domain, common
├──────────────────────────┤
│  Domain Services         │  → can import common only (no Gin, no pgx, no zap)
├──────────────────────────┤
│  Outbound Adapters       │  → can import domain, ports, common + pgx/go-redis
├──────────────────────────┤
│  Common (Utils)          │  → no dependencies
└──────────────────────────┘
```

Enforced via **`go-arch-lint`**. Violations require an ADR.

---

## 8. Testing by Layer

| Layer | Type | Dependencies | Speed |
|-------|------|--------------|-------|
| Domain | Unit | All mocked (testify/mock) | Fast |
| Ports | Contract | N/A | N/A |
| API | Unit + Integration | Mocked + httptest | Fast/Medium |
| Outbound Adapters | Unit + Integration | Mocked + Testcontainers | Medium/Slow |

---

## 9. Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---------|----------------|-----|
| Domain imports `pgxpool` | Couples domain to infrastructure | Use outbound ports |
| Handler calls `UserService` struct directly | Violates port contract | Use `UserServicePort` interface |
| Adapter calls another adapter | Creates implicit dependencies | Go through ports |
| Business logic in `gin.HandlerFunc` | Mixes concerns | Move to domain service |
| `time.Now()` called directly in domain | Makes testing hard | Inject a `clock` interface |
| Import cycle (`domain → api → domain`) | Breaks architecture | Refactor to use ports |
