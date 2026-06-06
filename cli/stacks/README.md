# Stack Overlays

This directory contains GovKit's bundled stack overlays. Each overlay is a small bundle of stack-specific architecture docs plus an `overlay.yaml` describing metadata, default assumptions, skill context, and a review checklist.

These overlays ship inside the GovKit Python wheel under `cli/stacks/`. Client repos never see this directory directly - they receive only the docs from the selected overlay, copied into their own `docs/backend/architecture/` or `docs/data/architecture/`.

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

`govkit stack apply` honors edit-protection - any stack docs you've modified since the last apply are preserved unless you pass `--force`. The chosen stack is recorded in `.govkit/marker.json` under `stack` and as a `stack.id` assumption.

---

## Why Stack Docs?

The agent rules (`agents/*/rules/`) and the majority of architecture docs are shape-agnostic. Stack overlays provide only the docs that vary by runtime, framework, data platform, or delivery surface.

Backend/API stacks typically vary these files:

| File | What it defines |
|---|---|
| `TECH_STACK.md` | Languages, versions, approved frameworks |
| `API_CONVENTIONS.md` | Route patterns and request/response idioms |
| `TESTING.md` | Test framework, mocking library, BDD tool |
| `LAYER_IMPLEMENTATION.md` | DI patterns, interface idioms, DTO style |
| `SECURITY_AUTH_PATTERNS.md` | Auth libraries, token handling, hashing |
| `OBSERVABILITY_PORT_CONTRACT.md` | Structured logging library, OTel SDK |

All other docs (DESIGN_PRINCIPLES, ARCH_CONTRACT, BOUNDARIES, GHERKIN_CONVENTIONS, ERROR_MAPPING, etc.) are universal and ship from the baseline `governed` install.

Data stacks install their stack-specific docs under `docs/data/architecture/` and may use data-oriented names such as `MODEL_LAYERING.md`, `PIPELINE_CONTRACT.md`, and `PII_HANDLING.md`.

---

## Bundled overlays

| Id | Stack |
|---|---|
| `python-fastapi` | Python 3.11+ / FastAPI / pytest (default) |
| `dotnet-aspnet` | C# 12 / .NET 8 / ASP.NET Core Minimal APIs / xUnit |
| `java-spring-boot` | Java 21 / Spring Boot 3 / Spring Web MVC / JUnit 5 |
| `nodejs-fastify` | Node.js 20 LTS / TypeScript 5 / Fastify 4 / Vitest |
| `go-gin` | Go 1.22+ / Gin / standard library testing + testify |
| `python-dbt` | Python 3.11+ / dbt-core / dbt tests |
| `databricks-lakehouse` | Databricks Lakehouse / Unity Catalog / Delta / Asset Bundles |

---

## Adding a new overlay

To add a stack not listed here:

1. Create `cli/stacks/<id>/` with the stack docs the overlay declares (mirror the section structure of a similar overlay for consistency).
2. Add `cli/stacks/<id>/overlay.yaml` declaring `id`, `version`, `display_name`, `summary`, `default_assumptions`, `docs`, `skill_context`, and `review_checklist`. See [`python-fastapi/overlay.yaml`](python-fastapi/overlay.yaml) as a template.
3. Submit a PR — the only constraint is that each doc must preserve the section headings so the agent rules can reference them consistently.

After adding, `govkit stack list` will discover the new overlay automatically.
