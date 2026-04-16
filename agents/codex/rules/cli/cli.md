# CLI Layer Rules

Follow the CLI conventions defined in `docs/backend/architecture/CLI_CONVENTIONS.md`.

All commands in `cli/` or `commands/` must:

- Use Click or Typer for argument parsing and command structure
- Delegate all logic to inbound ports (`ports/inbound/`)
- Never access domain services, repositories, or adapter logic directly
- Validate arguments using Click/Typer parameter types before calling ports
- Map CLI arguments to domain objects (DTOs or value objects) before port calls
- Use exit code 0 for success, 1 for user errors, 2 for system errors
- Send structured output to stdout, error/status messages to stderr
- Support `--format json|table|plain` for commands that produce data output
- Include `--verbose` flag for debug-level logging
- Never expose stack traces or internal details in normal mode
- Avoid leaking Click/Typer types into service or port layers

All CLI commands are inbound adapters. They must stay thin and port-driven.
