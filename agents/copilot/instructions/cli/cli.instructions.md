---
applyTo: "**/cli/**,**/commands/**"
---

# CLI Layer — Inbound Adapter

**Your project's CLI conventions:** `docs/backend/architecture/CLI_CONVENTIONS.md`

Read this document before implementing any CLI command. It defines your project's command structure, argument handling, output format, and error reporting.

**Universal constraints (apply to any language):**
- CLI commands are inbound adapters — delegate all business logic to inbound ports in `ports/inbound/`
- Validate and parse arguments according to your CLI framework before calling ports
- Map CLI arguments to domain objects (DTOs, value objects) before passing to ports
- Commands must remain thin — no business logic inline
- Never expose domain types directly in output; translate at the boundary
- Use universal exit codes: 0 = success, 1 = user error (invalid input, business rule violation), 2 = system error (infrastructure failure)
- Send structured output to stdout; send diagnostic/error messages to stderr
- Provide structured output formats (`--format json|table|plain`) for machine-readable results
- Include `--verbose` flag to enable debug-level logging
- Never expose stack traces in normal mode
- Domain layer must not depend on CLI framework types or libraries
