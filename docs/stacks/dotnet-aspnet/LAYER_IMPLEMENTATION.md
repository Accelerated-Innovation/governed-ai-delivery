# Layer Implementation Guide

This document provides a consolidated reference for implementing each layer in the hexagonal architecture. For comprehensive guidance on any layer, see the references at the bottom of each section.

---

## Overview

The system uses **Hexagonal Architecture** with these layers:

```
┌─────────────────────────┐
│   Adapters (Inbound)    │  Api/, Cli/
├─────────────────────────┤
│  Ports (Interfaces)     │  Ports/Inbound/, Ports/Outbound/
├─────────────────────────┤
│  Domain (Core Logic)    │  Services/, Models/
├─────────────────────────┤
│   Adapters (Outbound)   │  Adapters/
└─────────────────────────┘
```

All communication goes through ports. Adapters never talk directly to each other.

---

## 1. Domain Layer

**Location:** `src/Domain/Services/`, `src/Domain/Models/`

**Role:** Pure business logic and state management. The core of the system.

### Hard Rules

- **No external dependencies** — only BCL (Base Class Library) and domain-specific types
- **No framework references** — ASP.NET Core, EF Core, Serilog, etc. must never appear
- **Dependency injection only** — all external systems injected via constructor
- **Stateless functions** — business logic as pure functions / methods where possible
- **Domain-specific exceptions** — raise exceptions that adapters can translate
- **Interfaces (ports) only** — no implementation details in domain code

### Examples

```csharp
// ✓ Good — pure domain logic, injected dependencies
public class UserService(IUserRepository repo) : IUserServicePort
{
    public async Task<User> ActivateUserAsync(string userId, UserContext identity)
    {
        var user = await repo.GetAsync(userId)
            ?? throw new UserNotFoundException(userId);
        user.Activate();
        await repo.SaveAsync(user);
        return user;
    }
}

// ✗ Bad — framework references, hardcoded dependencies
public class UserService
{
    private readonly AppDbContext _db = new();     // hardcoded, not injected

    [HttpPost("/users/{id}/activate")]             // framework attribute in domain
    public async Task<IActionResult> Activate(string id) { ... }
}
```

### Testing

- Unit test all public methods with xUnit
- Substitute all injected port dependencies with NSubstitute
- No database, HTTP, or external service calls
- Fast and isolated

**Reference:** `docs/backend/architecture/ARCH_CONTRACT.md`

---

## 2. Port Layer

**Location:** `src/Ports/Inbound/`, `src/Ports/Outbound/`

**Role:** Define contracts between domain and adapters. Adapters implement these; domain depends on them.

### Inbound Ports

Define how the domain is called (use cases, entry points).

```csharp
// Ports/Inbound/IUserServicePort.cs
public interface IUserServicePort
{
    Task<User> ActivateUserAsync(string userId, UserContext identity);
    Task<User?> GetUserAsync(string userId);
}
```

### Outbound Ports

Define what external systems the domain depends on (storage, APIs, messaging).

```csharp
// Ports/Outbound/IUserRepository.cs
public interface IUserRepository
{
    Task<User?> GetAsync(string userId);
    Task SaveAsync(User user);
}
```

### Hard Rules

- **Interface only** — no implementation logic, no side effects
- **Framework-agnostic** — no ASP.NET Core, EF Core, or infrastructure references
- **Domain types only** — use domain models, DTOs, exceptions — not raw framework types
- **Single concern** — one port per interface/contract
- **Bidirectional** — inbound ports called by adapters; outbound ports implemented by adapters

### Testing

- Ports themselves don't require tests
- Adapter implementations tested in isolation against their port contract
- Integration tests verify adapters work with real infrastructure

**Reference:** `docs/backend/architecture/BOUNDARIES.md`

---

## 3. Inbound Adapter Layer (API)

**Location:** `src/Api/`

**Role:** Handle HTTP requests and delegate to domain via inbound ports.

### API Layer (HTTP — ASP.NET Core Minimal APIs)

```csharp
// Api/Users/UserEndpoints.cs
public static class UserEndpoints
{
    public static void MapUserEndpoints(this WebApplication app)
    {
        var group = app.MapGroup("/v1/users").RequireAuthorization();

        group.MapPost("/{userId}/activate", async (
            string userId,
            HttpContext ctx,
            IUserServicePort userService) =>
        {
            var identity = UserContext.FromClaims(ctx.User);
            try
            {
                var user = await userService.ActivateUserAsync(userId, identity);
                return Results.Ok(new ApiResponse<UserDto>(UserDto.From(user), null));
            }
            catch (UserNotFoundException)
            {
                return Results.NotFound();
            }
            catch (UserAlreadyActiveException ex)
            {
                return Results.BadRequest(new ApiResponse<UserDto>(null,
                    new ErrorInfo("USER_ALREADY_ACTIVE", ex.Message)));
            }
        });
    }
}
```

### Hard Rules

- **Thin adapters** — validate input, call inbound port, translate response
- **No business logic** — all logic lives in the domain
- **Port delegation** — all work goes through inbound ports
- **Type translation** — convert HTTP types to domain types before calling port
- **Exception mapping** — catch domain exceptions, translate to `IResult` / `ProblemDetails`
- **Authentication/validation first** — validate and authenticate before calling the port

### Testing

- Test each handler using `WebApplicationFactory<Program>` (TestServer)
- Substitute the inbound port with NSubstitute
- Verify HTTP status codes and response formats
- Verify exception → HTTP status code mapping

**Reference:** `docs/backend/architecture/API_CONVENTIONS.md`

---

## 4. Outbound Adapter Layer

**Location:** `src/Adapters/`

**Role:** Implement outbound ports. Connect the domain to external systems (databases, APIs, caches).

### Structure

```
Adapters/
├── Postgres/              # Database adapter (EF Core)
│   ├── UserRepository.cs
│   └── AppDbContext.cs
├── Redis/                 # Cache adapter
│   └── CacheAdapter.cs
├── Stripe/                # External API adapter
│   └── PaymentAdapter.cs
└── Email/                 # Email service adapter
    └── EmailAdapter.cs
```

### Example Implementation

```csharp
// Adapters/Postgres/UserRepository.cs
public class UserRepository(AppDbContext db) : IUserRepository
{
    public async Task<User?> GetAsync(string userId)
    {
        var row = await db.Users.FindAsync(userId);
        if (row is null) return null;
        return new User(row.Id, row.Email, row.Status);
    }

    public async Task SaveAsync(User user)
    {
        var row = await db.Users.FindAsync(user.Id);
        if (row is null)
        {
            db.Users.Add(new UserRow { Id = user.Id, Email = user.Email, Status = user.Status });
        }
        else
        {
            row.Email = user.Email;
            row.Status = user.Status;
        }
        await db.SaveChangesAsync();
    }
}
```

### Hard Rules

- **Port implementation only** — implement the interface you're adapting
- **No business logic** — translation and integration only
- **No cross-adapter calls** — each adapter is independent
- **Framework types stay here** — don't leak EF Core, StackExchange.Redis, or HTTP library types to the domain
- **Dependency injection** — adapters wired up in composition root, not instantiated inline
- **Exception translation** — catch infrastructure exceptions, raise domain exceptions

### Testing

- **Unit tests:** Substitute external services (NSubstitute) or use EF Core in-memory provider for DB-only tests
- **Integration tests:** Use real infrastructure (Testcontainers for PostgreSQL/Redis)
- **Contract tests:** Verify adapter satisfies its port interface

**Reference:** `docs/backend/architecture/BOUNDARIES.md`

---

## 5. Composition Root (Dependency Injection)

**Location:** `src/Program.cs` or `src/Config/ServiceExtensions.cs`

**Role:** Wire up all adapters and ports. This is the only place framework and adapter instantiation happens.

```csharp
// Program.cs
var builder = WebApplication.CreateBuilder(args);

// Register ports and their implementations
builder.Services.AddScoped<IUserRepository, UserRepository>();
builder.Services.AddScoped<IUserServicePort, UserService>();
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("Postgres")));

var app = builder.Build();
app.MapUserEndpoints();
app.Run();
```

### Hard Rules

- **Single location** — all wiring in one place (or in clearly scoped extension methods)
- **No adapters in domain** — adapters only instantiated here
- **Dependency chain clear** — easy to see what depends on what

---

## 6. Cross-Cutting Concerns

**Location:** `src/Common/`

**Role:** Shared utilities, DTOs, logging, tracing, error handling.

```
Common/
├── Dto.cs              # Data transfer objects
├── Exceptions.cs       # Domain exceptions
├── Logging.cs          # Logging helpers
├── Observability.cs    # Tracing, metrics helpers
└── Validators.cs       # Reusable validation
```

### Hard Rules

- **Dependency-free** — Common cannot import from any other layer
- **No business logic** — utilities and shared types only
- **Used by all layers** — domain, ports, adapters all use Common

---

## 7. Dependency Rules

All dependencies flow **downward only** (with exceptions for ports):

```
┌──────────────────────────┐
│  API Adapters            │  ↓ can reference Domain, Ports, Common
├──────────────────────────┤
│  Ports (Inbound/Outbound)│  ↓ can reference Domain, Common
├──────────────────────────┤
│  Domain Services         │  ↓ can reference Common only
├──────────────────────────┤
│  Outbound Adapters       │  ↓ can reference Domain, Ports, Common
├──────────────────────────┤
│  Common (Utils)          │  ↓ no dependencies
└──────────────────────────┘
```

### Forbidden Imports

- ❌ Domain → Adapters
- ❌ Domain → Api
- ❌ Adapter → Adapter (cross-adapter)
- ❌ Common → Anything

Enforced via **ArchUnitNET**. Violations require an ADR.

---

## 8. Testing by Layer

| Layer | Type | Dependencies | Speed |
|-------|------|--------------|-------|
| Domain | Unit | All mocked (NSubstitute) | Fast |
| Ports | Contract | N/A | N/A |
| API | Unit + Integration | Mocked + WebApplicationFactory | Medium |
| Outbound Adapters | Unit + Integration | Mocked + Testcontainers | Medium/Slow |

All tests must satisfy **FIRST principles** and be deterministic.

See `docs/backend/architecture/TESTING.md` for complete testing guidance.

---

## 9. Summary Table

| Layer | Owns | References | Cannot Reference | Key Responsibility |
|-------|------|------------|-----------------|-------------------|
| **Domain** | Services, Models | Common | Adapters, Ports, Frameworks | Business logic |
| **Ports** | Inbound, Outbound | Domain, Common | Adapters, Frameworks | Contracts |
| **Api** | Endpoints, Handlers | Ports, Common | Domain impl | HTTP concerns |
| **Adapters** | DB, Cache, External | Domain, Ports, Common | Other Adapters | Infrastructure |
| **Common** | Utils, DTOs, Errors | (none) | Any layer | Shared types |

---

## 10. References

- **High-level architecture:** `ARCH_CONTRACT.md`
- **Module boundaries:** `BOUNDARIES.md`
- **API conventions:** `API_CONVENTIONS.md`
- **Testing standards:** `TESTING.md`
- **Error handling:** `ERROR_MAPPING.md`

---

## 11. Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---------|----------------|-----|
| Domain references EF Core | Couples domain to infrastructure | Use outbound ports |
| Adapter calls another adapter | Creates implicit dependencies | Go through ports |
| API calls service directly | Violates port contract | Call inbound port |
| Putting logic in API layer | Mixes concerns | Move to domain service |
| Not injecting dependencies | Makes testing hard | Use constructor injection |
| Circular project references | Breaks architecture | Refactor to use ports |
| Putting exceptions in Common | Couples layers inappropriately | Domain exceptions in Domain |
