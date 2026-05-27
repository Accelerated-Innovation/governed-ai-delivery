# Layer Implementation Guide

This document provides a consolidated reference for implementing each layer in the hexagonal architecture.

---

## Overview

The system uses **Hexagonal Architecture** with these layers:

```
┌─────────────────────────┐
│   Adapters (Inbound)    │  api/
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

**Location:** `src/main/java/.../domain/services/`, `.../domain/models/`

**Role:** Pure business logic and state management. The core of the system.

### Hard Rules

- **No external dependencies** — only Java BCL, no Spring, JPA, or Logback
- **No framework annotations** — `@Service`, `@Repository`, `@Component` must not appear in the domain
- **Dependency injection only** — all external systems injected via constructor
- **Stateless functions** — business logic as pure methods where possible
- **Domain-specific exceptions** — throw exceptions that adapters can translate
- **Interfaces (ports) only** — no implementation details in domain code

### Examples

```java
// ✓ Good — pure domain logic, injected dependencies
public class UserService implements UserServicePort {
    private final UserRepository repo;

    public UserService(UserRepository repo) {
        this.repo = repo;
    }

    public User activateUser(String userId, UserContext identity) {
        var user = repo.findById(userId)
            .orElseThrow(() -> new UserNotFoundException(userId));
        user.activate();
        repo.save(user);
        return user;
    }
}

// ✗ Bad — framework annotations in domain, hardcoded dependency
@Service                                   // Spring annotation in domain
public class UserService {
    @Autowired EntityManager em;           // hardcoded JPA dependency

    @GetMapping("/users/{id}/activate")    // web annotation in domain
    public ResponseEntity<?> activate(@PathVariable String id) { ... }
}
```

### Testing

- Unit test all public methods with JUnit 5
- Mock all injected port dependencies with Mockito
- No database, HTTP, or external service calls
- Fast and isolated

**Reference:** `docs/backend/architecture/ARCH_CONTRACT.md`

---

## 2. Port Layer

**Location:** `src/main/java/.../ports/inbound/`, `.../ports/outbound/`

**Role:** Define contracts between domain and adapters.

### Inbound Ports

```java
// ports/inbound/UserServicePort.java
public interface UserServicePort {
    User activateUser(String userId, UserContext identity);
    Optional<User> getUser(String userId);
}
```

### Outbound Ports

```java
// ports/outbound/UserRepository.java
public interface UserRepository {
    Optional<User> findById(String userId);
    void save(User user);
}
```

### Hard Rules

- **Interface only** — no implementation logic
- **Framework-agnostic** — no Spring, JPA, or infrastructure references
- **Domain types only** — use domain models, DTOs, exceptions
- **Single concern** — one port per interface/contract

**Reference:** `docs/backend/architecture/BOUNDARIES.md`

---

## 3. Inbound Adapter Layer (API)

**Location:** `src/main/java/.../api/`

**Role:** Handle HTTP requests and delegate to domain via inbound ports.

```java
// api/UserController.java
@RestController
@RequestMapping("/v1/users")
@RequiredArgsConstructor
public class UserController {

    private final UserServicePort userService;

    @PostMapping("/{userId}/activate")
    public ResponseEntity<ApiResponse<UserDto>> activateUser(
            @PathVariable String userId,
            @AuthenticationPrincipal Jwt jwt) {
        var identity = UserContext.fromJwt(jwt);
        try {
            var user = userService.activateUser(userId, identity);
            return ResponseEntity.ok(ApiResponse.ok(UserDto.from(user)));
        } catch (UserNotFoundException e) {
            return ResponseEntity.notFound().build();
        } catch (UserAlreadyActiveException e) {
            return ResponseEntity.badRequest()
                .body(ApiResponse.error("USER_ALREADY_ACTIVE", e.getMessage()));
        }
    }
}
```

### Hard Rules

- **Thin adapters** — validate input, call inbound port, translate response
- **No business logic** — all logic lives in the domain
- **Exception mapping** — catch domain exceptions, translate to `ResponseEntity` / `ProblemDetail`
- **Authentication/validation first** — validate and authenticate before calling the port

### Testing

- Use `@SpringBootTest` + `MockMvc` or `@WebMvcTest` + `@MockBean`
- Verify HTTP status codes and response formats

**Reference:** `docs/backend/architecture/API_CONVENTIONS.md`

---

## 4. Outbound Adapter Layer

**Location:** `src/main/java/.../adapters/`

**Role:** Implement outbound ports. Connect domain to external systems.

### Structure

```
adapters/
├── postgres/          # JPA-based repository adapter
│   ├── JpaUserRepository.java    (Spring Data JPA interface)
│   └── UserRepositoryAdapter.java (implements UserRepository port)
├── redis/             # Cache adapter
│   └── RedisCacheAdapter.java
├── stripe/            # External API adapter
│   └── StripePaymentAdapter.java
└── email/             # Email service adapter
    └── SmtpEmailAdapter.java
```

### Example Implementation

```java
// adapters/postgres/UserRepositoryAdapter.java
@Component
public class UserRepositoryAdapter implements UserRepository {

    private final JpaUserRepository jpa;

    public UserRepositoryAdapter(JpaUserRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    public Optional<User> findById(String userId) {
        return jpa.findById(userId).map(UserRow::toDomain);
    }

    @Override
    @Transactional
    public void save(User user) {
        jpa.save(UserRow.fromDomain(user));
    }
}
```

Note: `@Transactional` lives in the adapter layer, never in domain services.

### Hard Rules

- **Port implementation only** — implement the interface you're adapting
- **No business logic** — translation and integration only
- **No cross-adapter calls** — each adapter is independent
- **JPA types stay here** — don't leak `@Entity` classes or Spring Data types to the domain
- **Exception translation** — catch infrastructure exceptions, throw domain exceptions

### Testing

- **Unit tests:** Mock JPA repositories with Mockito
- **Integration tests:** Use Testcontainers for real PostgreSQL / Redis
- **Contract tests:** Verify adapter satisfies its port interface

**Reference:** `docs/backend/architecture/BOUNDARIES.md`

---

## 5. Composition Root (Dependency Injection)

**Location:** `src/main/java/.../config/`

Spring Boot's `@SpringBootApplication` auto-configuration handles most wiring. Explicit `@Bean` definitions live in `@Configuration` classes:

```java
@Configuration
public class DomainConfig {

    @Bean
    public UserServicePort userServicePort(UserRepository userRepository) {
        return new UserService(userRepository);
    }
}
```

Note: `UserService` (domain) is wired here, NOT annotated with `@Service` — keeping the domain Spring-free.

### Hard Rules

- **No Spring annotations in domain** — `@Service`, `@Component`, `@Autowired` only in config and adapters
- **Single location** — all domain wiring in `config/`
- **Dependency chain clear** — easy to see what depends on what

---

## 6. Cross-Cutting Concerns

**Location:** `src/main/java/.../common/`

```
common/
├── dto/            # Data transfer objects
├── exception/      # Domain exceptions
├── logging/        # Logging helpers / MDC utilities
├── observability/  # Tracing, metrics helpers
└── validation/     # Reusable validation utilities
```

### Hard Rules

- **Dependency-free** — common cannot import from any other layer
- **No business logic** — utilities and shared types only

---

## 7. Dependency Rules

```
┌──────────────────────────┐
│  API Adapters            │  → can import Domain, Ports, Common + Spring Web
├──────────────────────────┤
│  Ports (Inbound/Outbound)│  → can import Domain, Common
├──────────────────────────┤
│  Domain Services         │  → can import Common only (no Spring, no JPA)
├──────────────────────────┤
│  Outbound Adapters       │  → can import Domain, Ports, Common + Spring Data
├──────────────────────────┤
│  Common (Utils)          │  → no dependencies
└──────────────────────────┘
```

Enforced via **ArchUnit**. Violations require an ADR.

---

## 8. Testing by Layer

| Layer | Type | Dependencies | Speed |
|-------|------|--------------|-------|
| Domain | Unit | All mocked (Mockito) | Fast |
| Ports | Contract | N/A | N/A |
| API | Unit + Integration | Mocked + MockMvc | Medium |
| Outbound Adapters | Unit + Integration | Mocked + Testcontainers | Medium/Slow |

---

## 9. Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---------|----------------|-----|
| Domain imports JPA `@Entity` | Couples domain to infrastructure | Use outbound ports + adapter row classes |
| Domain class annotated `@Service` | Couples domain to Spring | Wire via `@Bean` in config |
| Adapter calls another adapter | Creates implicit dependencies | Go through ports |
| `@Transactional` in domain service | Leaks infrastructure concern | Put in adapter layer |
| Putting logic in `@RestController` | Mixes concerns | Move to domain service |
| Circular package dependencies | Breaks architecture | Refactor to use ports |
