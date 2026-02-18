# Port Layer Instructions

These rules apply to all files under `/ports/**`. Ports define interfaces that decouple the domain logic from framework and infrastructure details.

---

## 1. Purpose

- Declare clear boundaries between domain and technical layers
- Inbound ports define how the domain is invoked (e.g., use cases)
- Outbound ports define what the domain depends on (e.g., storage, messaging)

---

## 2. Structure

- Use `ports/inbound/**` for service-facing interfaces
- Use `ports/outbound/**` for external dependency contracts
- Each file should define a single interface (abstract base class or Protocol)

---

## 3. Guidelines

- Do not implement logic in port files
- Ports must be framework-agnostic (no FastAPI, SQLAlchemy, etc.)
- Define type-safe method signatures and docstrings
- Accept and return domain types or DTOs—not raw infra types

---

## 4. Dependencies

- Ports may import:
  - Domain models, value objects, DTOs
  - Standard Python typing
- Ports must not import:
  - `/api/**`
  - `/adapters/**`
  - `/services/**`
  - Infra libraries (e.g., boto3, SQLAlchemy)

---

## 5. Design Expectations

- Keep interfaces minimal and focused
- Use composition over inheritance for complex flows
- Apply versioning if ports evolve (e.g., `v1/`, `v2/` folders)

---

## 6. Testing

- Ports themselves do not require tests
- All implementations (adapters) must be testable against the interface

---

## 7. Violations

- Logic or side effects in a port file
- Leaking adapter types into method signatures
- Circular imports from adapters or services

All port contracts are subject to review and must remain stable for consumers.
