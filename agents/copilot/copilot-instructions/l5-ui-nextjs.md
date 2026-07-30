---
applyTo: "**"
---
# GitHub Copilot Instructions — Next.js UI (Level 5)

Apply Level 4 Next.js rules and installed GenAI extension contracts. All
business logic, persistence, model/provider access, guardrails, prompts, and
model controls remain behind versioned backend APIs.

Never generate SQL, database dependencies, ORMs, migrations, schemas,
connection strings, or direct provider SDK calls. Thin BFF code may only adapt
session, token, protocol, or limited aggregation concerns. No ADR waives this.

Model streaming, guardrail rejection, fallback, rate-limit, timeout, and
unavailable states must be typed and accessible. Preserve safety metadata and
citations; do not render untrusted output as executable HTML or expose secrets.

Follow approved brand/design and test all server/client, responsive,
accessibility, streaming, and recovery states. Require typecheck, lint, Vitest,
Playwright, axe, API/database boundary enforcement, and referenced backend
evaluation evidence.
