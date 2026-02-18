# Adapter Layer Instructions

These rules apply to all files under `/adapters/**`.
Adapters implement technical integrations that satisfy port interfaces.

---

## 1. Purpose

- Implement outbound ports (e.g., database, cache, email, APIs)
- Translate domain models to/from infrastructure-specific formats
- Remain infrastructure-aware, but domain-agnostic

---

## 2. Structure

- Group by technology (e.g., `sqlalchemy_adapter`, `redis_adapter`, `s3_adapter`)
- Each adapter must implement one or more outbound ports from `/ports/outbound/`
- Do not leak adapter-specific types into service or domain layers

---

## 3. Dependency Rules

- Adapters may import:
  - Port interfaces
  - Domain DTOs and value objects
  - Libraries required to interface with the external system
- Adapters must not import from:
  - `/services/**`
  - `/api/**`
  - Other adapters

---

## 4. Implementation Guidelines

- Adapters must be initialized outside of the domain (e.g., in a DI container or app factory)
- Return domain types or DTOs—not raw ORM or SDK objects
- Handle all infrastructure exceptions locally and raise clean errors

---

## 5. Logging and Observability

- Log integration-specific events with `adapter_name`, `operation`, and `duration_ms`
- Mask sensitive data in logs
- Emit Prometheus-compatible metrics where relevant (e.g., latency, retries)

---

## 6. Testing

- Use mock infrastructure clients in unit tests
- Include integration tests (if side effects are testable)
- Validate compliance with expected port behaviors

---

## 7. Violations

- Direct calls to external services from domain or service layers are forbidden
- Reusing adapter logic without a port contract is disallowed
- All adapter usage must be mediated by the port it implements