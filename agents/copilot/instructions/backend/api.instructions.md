---
applyTo: "**/api/**"
---

# API Layer — Inbound Adapter

**Your project's API conventions:** `docs/backend/architecture/API_CONVENTIONS.md`

Read this document before implementing any route. It defines your project's routing style, request/response models, authentication mechanism, error handling, and testing approach.

**Universal constraints (apply to any language):**
- Routes are inbound adapters — delegate all business logic to inbound ports in `ports/inbound/**`
- Validate and authenticate requests before calling the port layer
- Map domain exceptions to HTTP responses at this layer, not inside domain code
- Routes must remain thin — no business logic inline
- Never expose domain types directly in HTTP responses; translate at the boundary
- Support both sync and async execution depending on your framework
- Include metadata in HTTP responses for API documentation (swagger/OpenAPI equivalent)
