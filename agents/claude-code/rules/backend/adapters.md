---
paths:
  - "**/adapters/**"
---

# Adapter Layer — Infrastructure Integration

**Your project's architecture contract:** `docs/backend/architecture/ARCH_CONTRACT.md` and `BOUNDARIES.md`

Adapters implement outbound port contracts, connecting your domain to external systems (databases, APIs, caches). Review the architecture docs for integration patterns and dependency rules.

**Universal constraints (apply to any language):**
- Adapters implement outbound port interfaces from `ports/outbound/`
- Adapters translate between domain/port types and external system types (ORM objects, API responses, etc.)
- Group adapters by technology/concern (e.g., `postgres_adapter`, `redis_adapter`, `http_client_adapter`)
- Adapters must not import from services, API layer, or other adapters
- Adapters must not be called directly; all access goes through their port interface
- Adapters handle all infrastructure-level error translation and convert to clean domain exceptions
- Adapters return domain types or DTOs, never raw external library objects
- Initialization and wiring of adapters happens in a composition root (factory, dependency injection, etc.), not scattered through services

**Error handling:**
- Catch all infrastructure exceptions (connection errors, timeouts, SDK errors)
- Translate to domain exception types that services can handle
- Never leak external library types to the domain

**Testing:**
- Mock external service clients (database, API, cache) in unit tests
- Integration tests use real infrastructure for side-effect validation
- Verify adapter compliance with port contract
