# Tech Stacks

This directory contains ready-to-use replacements for the 6 stack-specific architecture docs in `docs/backend/architecture/`. The default installed stack is **Python / FastAPI**. Copy any stack here to switch languages without touching any agent rules, manifests, or CLI configuration.

---

## Why only 6 files?

The agent rules (`agents/*/rules/`) and the majority of architecture docs are already language-agnostic — they enforce hexagonal architecture, FIRST principles, and the 7 Code Virtues regardless of language. Only these 6 files contain language- or framework-specific details:

| File | What it defines |
|---|---|
| `TECH_STACK.md` | Languages, versions, approved frameworks |
| `API_CONVENTIONS.md` | Route patterns and request/response idioms |
| `TESTING.md` | Test framework, mocking library, BDD tool |
| `LAYER_IMPLEMENTATION.md` | DI patterns, interface idioms, DTO style |
| `SECURITY_AUTH_PATTERNS.md` | Auth libraries, token handling, hashing |
| `OBSERVABILITY_PORT_CONTRACT.md` | Structured logging library, OTel SDK |

All other docs (DESIGN_PRINCIPLES, ARCH_CONTRACT, BOUNDARIES, GHERKIN_CONVENTIONS, ERROR_MAPPING, etc.) are universal and stay as-is.

---

## Available stacks

| Directory | Stack |
|---|---|
| `dotnet-aspnet/` | C# 12 / .NET 8 / ASP.NET Core Minimal APIs |
| `java-spring-boot/` | Java 21 / Spring Boot 3 / Spring Web MVC |
| `nodejs-fastify/` | Node.js 20 LTS / TypeScript 5 / Fastify 4 |
| `go-gin/` | Go 1.22+ / Gin |

---

## How to switch stacks

Copy the 6 files from your chosen stack directory over the corresponding files in `docs/backend/architecture/`:

```bash
# Example: switch to C# / ASP.NET Core
cp docs/stacks/dotnet-aspnet/* docs/backend/architecture/
```

That's it. The AI agents (Claude Code, Copilot, Codex) read `docs/backend/architecture/` for stack specifics and will immediately pick up the new conventions on the next session.

> **Tip:** Consider raising an ADR (`docs/backend/architecture/ADR/`) to record the stack decision and rationale. Use the template at `docs/backend/architecture/ADR/TEMPLATE.md`.

---

## Adding a new stack

To add a stack not listed here:

1. Create a new directory: `docs/stacks/<stack-name>/`
2. Author all 6 files, mirroring the section structure of the Python originals in `docs/backend/architecture/`
3. Submit a PR — the only constraint is that each file must preserve the same headings so the agent rules can reference them consistently
