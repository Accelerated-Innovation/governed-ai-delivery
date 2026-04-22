# Port Layer — Domain Contracts

**Your project's architecture contract:** `docs/backend/architecture/ARCH_CONTRACT.md` and `BOUNDARIES.md`

Ports define the contracts between the domain and its adapters. Review the architecture docs for interface guidelines and dependency rules.

**Universal constraints (apply to any language):**
- Inbound ports (`ports/inbound/`) define how the domain logic is called (use cases, command handlers)
- Outbound ports (`ports/outbound/`) define what external systems the domain depends on (storage, APIs, messaging)
- Ports are pure interfaces/contracts — no implementation logic, no side effects
- Ports must be framework-agnostic: no web framework, ORM, or infrastructure library references
- Port method signatures must use domain types or DTOs, never raw framework or infrastructure types
- Ports may import domain models, value objects, exceptions, and standard language types only
- Each port file defines a single interface/contract
- Adapters must implement outbound port interfaces; inbound ports are called by adapters

**Testing:**
- Port files do not themselves require tests
- All adapter implementations must satisfy their port interface contract (testable in isolation)
