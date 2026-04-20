---
paths:
  - "**/services/**"
---

# Service Layer — Domain Logic

**Your project's architecture contract:** `docs/backend/architecture/ARCH_CONTRACT.md`

Services implement the business logic of your domain. Review the architecture contract for layer structure and boundaries.

**Universal constraints (apply to any language):**
- Services contain business logic, state transitions, and orchestration — nothing else
- Services must not directly handle HTTP, serialization, database, or network concerns
- Services must not import from the inbound adapter layer (API, CLI) or the adapter/infrastructure layer
- All external dependencies must be injected via constructor (no singleton global access, no hardcoded instantiation)
- Services may only depend on ports and pure domain models
- Services raise domain-specific exceptions; adapters convert these to API responses
- One service per domain area; methods should be named after business operations
- All domain logic that produces business value lives here

**Testing:**
- Unit test all service public methods in isolation
- Mock all injected port dependencies
- Test business logic, not infrastructure details
