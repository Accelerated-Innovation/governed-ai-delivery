# Governed AI Delivery — Next.js UI (Level 5)

Apply the Level 4 Next.js UI contract plus applicable GenAI extension
contracts. Read architecture, brand/design, feature artifacts, and versioned
backend API contracts before planning or code.

Use server-first App Router feature slices. All business logic, persistence,
model access, provider SDKs, guardrails, prompts, and model controls remain
behind the backend API. Never add SQL, database dependencies, an ORM,
migrations, schemas, or connection strings. A thin BFF may only handle
session/token/protocol/limited aggregation concerns. No ADR waives this rule.

Represent streaming, guardrail rejection, fallback, rate-limit, timeout, and
unavailable states as typed UI states. Preserve backend safety metadata and
citations. Never render untrusted model output as executable HTML or expose
secrets in client bundles.

Follow approved visual direction; references stay advisory. Test accessibility,
reduced motion, streaming and recovery states. Pass typecheck, lint, Vitest,
Playwright, axe, API/database boundary checks, and referenced backend
quality/adversarial/retrieval evaluation gates.
