# Port Layer Rules

Ports define interfaces that decouple domain logic from framework and infrastructure details.

## Purpose

- Inbound ports define how the domain is invoked (use cases)
- Outbound ports define what the domain depends on (storage, messaging)

## Structure

- Use `ports/inbound/` for service-facing interfaces
- Use `ports/outbound/` for external dependency contracts
- Each file should define a single interface (abstract base class or Protocol)

## Guidelines

- Do not implement logic in port files
- Ports must be framework-agnostic (no FastAPI, SQLAlchemy, etc.)
- Define type-safe method signatures and docstrings
- Accept and return domain types or DTOs — not raw infra types

## Dependencies

Ports may import domain models, value objects, DTOs, and standard Python typing. Ports must not import from `api/`, `adapters/`, `services/`, or infra libraries.

## Testing

Ports themselves do not require tests. All adapter implementations must be testable against the interface.

## Violations

- Logic or side effects in a port file
- Leaking adapter types into method signatures
- Circular imports from adapters or services
