# Stack Overlays

This directory contains GovKit's bundled stack overlays. Each overlay is a small bundle of 6 stack-specific architecture docs (`TECH_STACK.md`, `API_CONVENTIONS.md`, `TESTING.md`, `LAYER_IMPLEMENTATION.md`, `SECURITY_AUTH_PATTERNS.md`, `OBSERVABILITY_PORT_CONTRACT.md`) plus an `overlay.yaml` describing metadata, default assumptions, skill context, and a review checklist.

These overlays ship inside the GovKit Python wheel under `cli/stacks/`. Client repos never see this directory directly — they receive only the docs from the selected overlay, copied into their own `docs/backend/architecture/`.

---

## Picking an overlay

```bash
# Discover what's available
govkit stack list

# Pick at install time
govkit apply --agent claude-code --target . --level 4 --type api --ci github \
             --stack dotnet-aspnet

# Swap on an existing install
govkit stack apply java-spring-boot --target .
```

`govkit stack apply` honors edit-protection — any of the 6 stack docs you've modified since the last apply are preserved unless you pass `--force`. The chosen stack is recorded in `.govkit/marker.json` under `stack` and as a `stack.id` assumption.

---

## Why only 6 files?

The agent rules (`agents/*/rules/`) and the majority of architecture docs are language-agnostic — they enforce hexagonal architecture, FIRST principles, and the 7 Code Virtues regardless of language. Only these 6 vary per stack:

| File | What it defines |
|---|---|
| `TECH_STACK.md` | Languages, versions, approved frameworks |
| `API_CONVENTIONS.md` | Route patterns and request/response idioms |
| `TESTING.md` | Test framework, mocking library, BDD tool |
| `LAYER_IMPLEMENTATION.md` | DI patterns, interface idioms, DTO style |
| `SECURITY_AUTH_PATTERNS.md` | Auth libraries, token handling, hashing |
| `OBSERVABILITY_PORT_CONTRACT.md` | Structured logging library, OTel SDK |

All other docs (DESIGN_PRINCIPLES, ARCH_CONTRACT, BOUNDARIES, GHERKIN_CONVENTIONS, ERROR_MAPPING, etc.) are universal and ship from the baseline `governed` install.

---

## Bundled overlays

| Id | Stack |
|---|---|
| `python-fastapi` | Python 3.11+ / FastAPI / pytest (default) |
| `dotnet-aspnet` | C# 12 / .NET 8 / ASP.NET Core Minimal APIs / xUnit |
| `java-spring-boot` | Java 21 / Spring Boot 3 / Spring Web MVC / JUnit 5 |
| `nodejs-fastify` | Node.js 20 LTS / TypeScript 5 / Fastify 4 / Vitest |
| `go-gin` | Go 1.22+ / Gin / standard library testing + testify |

---

## Adding a new overlay

To add a stack not listed here:

1. Create `cli/stacks/<id>/` with all 6 stack docs (mirror the section structure of an existing overlay for consistency).
2. Add `cli/stacks/<id>/overlay.yaml` declaring `id`, `version`, `display_name`, `summary`, `default_assumptions`, `docs`, `skill_context`, and `review_checklist`. See [`python-fastapi/overlay.yaml`](python-fastapi/overlay.yaml) as a template.
3. Submit a PR — the only constraint is that each doc must preserve the section headings so the agent rules can reference them consistently.

After adding, `govkit stack list` will discover the new overlay automatically.
