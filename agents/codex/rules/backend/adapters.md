# Adapter Layer Rules

Adapters implement technical integrations that satisfy port interfaces.

## Purpose

- Implement outbound ports (database, cache, email, external APIs)
- Translate domain models to/from infrastructure-specific formats
- Remain infrastructure-aware, but domain-agnostic

## Structure

- Group by technology (e.g., `sqlalchemy_adapter`, `redis_adapter`, `s3_adapter`)
- Each adapter must implement one or more outbound ports from `ports/outbound/`
- Do not leak adapter-specific types into service or domain layers

## Dependency Rules

Adapters may import port interfaces, domain DTOs, and libraries for the external system. Adapters must not import from `services/`, `api/`, or other adapters.

## Implementation Guidelines

- Initialize adapters outside of the domain (in a DI container or app factory)
- Return domain types or DTOs — not raw ORM or SDK objects
- Handle all infrastructure exceptions locally and raise clean errors

## Testing

- Use mock infrastructure clients in unit tests
- Include integration tests where side effects are testable
- Validate compliance with expected port behaviors

## Violations

- Direct calls to external services from domain or service layers
- Reusing adapter logic without a port contract
- All adapter usage must be mediated by the port it implements
