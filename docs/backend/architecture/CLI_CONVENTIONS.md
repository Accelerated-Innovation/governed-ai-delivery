# CLI Design Instructions

Applies to all inbound adapter files under `/cli/**` or `/commands/**`. CLI commands are responsible for user interaction concerns only. All domain logic must be delegated to inbound ports.

---

## 0. Interaction with Domain

* Commands must call **inbound ports** (interfaces) from `ports/inbound/`
* Do **not** call service implementations or business logic directly
* Use dependency injection or wiring to bind ports to adapter implementations
* Inputs (e.g., CLI arguments, options, config values) must be mapped to domain objects before calling ports
* Ports return results or raise domain exceptions; commands translate those into output and exit codes
* CLI commands are inbound adapters — the same role API routes play in HTTP-based projects

---

## 1. Command Structure

* Use **Click** or **Typer** for argument parsing and command groups
* Group related commands under command groups (e.g., `govkit apply`, `govkit validate`)
* Use descriptive, unambiguous names — `govkit apply` not `govkit a`
* Keep each command function thin: parse input, map to domain objects, call port, format output
* Avoid inline command definitions in the entry point; organize commands in modules under `src/cli/` or `src/commands/`
* Register command groups using Click `@group.command()` or Typer `app.add_command()`

---

## 2. Arguments and Options

* Required inputs are **positional arguments**
* Optional inputs are **flags** with `--` prefix (e.g., `--format json`, `--verbose`)
* Use Click/Typer parameter types for validation (`click.Path`, `click.Choice`, `typer.Option`)
* Provide sensible defaults where applicable
* Document every argument and option with `help=` strings
* Avoid boolean positional arguments — use `--flag` / `--no-flag` instead
* Example:

```python
@cli.command()
@click.argument("target", type=click.Path(exists=True))
@click.option("--format", type=click.Choice(["json", "table", "plain"]), default="plain")
@click.option("--verbose", is_flag=True, default=False, help="Enable debug output")
def apply(target: str, format: str, verbose: bool):
    ...
```

---

## 3. Exit Codes

* `0` — Success
* `1` — User or input error (bad arguments, validation failure, missing config)
* `2` — System or runtime error (network failure, file I/O error, unexpected exception)

Rules:

* Never `sys.exit(0)` on failure
* Never `sys.exit(1)` on success
* Use `click.exceptions.Exit` or `raise SystemExit(code)` for explicit exits
* Document exit codes in `--help` output where applicable

---

## 4. Output Formatting

* Support `--format json|table|plain` for commands that produce data output
* Structured data (JSON, tables) goes to **stdout**
* Human-readable status messages, progress, and diagnostics go to **stderr**
* Suppress color codes when stdout is not a TTY (`sys.stdout.isatty()`)
* JSON output must be valid, parseable JSON — no extra decoration
* Table output should use consistent column alignment
* Plain output is the default for interactive use

```python
if format == "json":
    click.echo(json.dumps(result, indent=2))
elif format == "table":
    click.echo(tabulate(result, headers="keys"))
else:
    click.echo(result.summary)
```

---

## 5. Error Handling

* Domain exceptions from ports must be caught and converted to:
  * A human-readable message on **stderr**
  * An appropriate exit code (1 for user errors, 2 for system errors)
* Never expose stack traces to users in normal mode
* Use `--verbose` to enable traceback output for debugging
* Centralize exception handling in a decorator or wrapper

```python
try:
    result = port.execute(command_input)
except DomainValidationError as e:
    click.echo(f"Error: {e.message}", err=True)
    raise SystemExit(1)
except Exception as e:
    click.echo(f"Internal error: {e}", err=True)
    if verbose:
        import traceback
        traceback.print_exc(file=sys.stderr)
    raise SystemExit(2)
```

---

## 6. Configuration

* Support three configuration sources in this precedence order (highest to lowest):
  1. **CLI flags** (`--option value`)
  2. **Environment variables** (`GOVKIT_OPTION=value`)
  3. **Config files** (TOML or YAML, e.g., `govkit.toml`, `.govkit.yaml`)

* Use `pydantic.BaseSettings` for configuration models with env var support
* Store secrets only in environment variables — never in config files
* Provide a `govkit config show` or equivalent command to display resolved configuration (redacting secrets)
* Document all configuration options and their sources

---

## 7. Observability

* Use **structured logging** directed to **stderr** (never stdout)
* Include at minimum: `command`, `subcommand`, `duration_ms`, `exit_code`
* Support log level control via flags:
  * `--verbose` — DEBUG level
  * `--quiet` — suppress all non-error output
  * Default — INFO level
* Use `structlog` or `logging` with JSON formatter for machine-readable logs
* Include timestamps in ISO 8601 format
* Do not log secrets or sensitive configuration values

```python
logger.info("command_completed", command="apply", target=target, duration_ms=elapsed)
```

---

## 8. Testing

* Use `click.testing.CliRunner` (Click) or `typer.testing.CliRunner` (Typer) for integration tests
* Use `subprocess.run` for end-to-end tests that verify the installed CLI binary

Every command must have tests covering:

* **Exit codes** — 0 on success, 1 on user error, 2 on system error
* **stdout content** — verify structured output (JSON validity, expected fields)
* **stderr content** — verify error messages and diagnostic output
* **Argument validation** — missing required args, invalid types, unknown flags
* **Port mock assertions** — verify correct domain objects are passed to ports

```python
def test_apply_success():
    runner = CliRunner()
    result = runner.invoke(cli, ["apply", "target_path"])
    assert result.exit_code == 0
    assert "Applied" in result.output

def test_apply_missing_target():
    runner = CliRunner()
    result = runner.invoke(cli, ["apply"])
    assert result.exit_code != 0
    assert "Error" in result.output
```

---

## 9. Adapter Boundaries

The CLI layer is an inbound adapter located under:
```
src/cli/
```
or
```
src/commands/
```

CLI commands must:

* Live in `src/cli/` or `src/commands/` — never in domain, service, or adapter directories
* Import only from `ports/inbound/` and shared domain models
* Never import from `services/`, `adapters/`, or `ports/outbound/`
* Never leak Click/Typer types (decorators, contexts, parameters) into port or service layers
* Map all CLI-specific types to domain objects before crossing the port boundary
