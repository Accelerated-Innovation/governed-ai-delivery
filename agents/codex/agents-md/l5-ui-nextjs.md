# Governed AI Delivery — Next.js UI (Level 5)

Apply all Level 4 Next.js UI rules plus GenAI operational discipline.
Repository artifacts and backend API contracts are authoritative.

## Mandatory Workflow

Read `docs/ui/architecture/nextjs/`, `docs/ui/design/BRAND.md`, the feature's
six artifacts, and the versioned backend contract. Run architecture, spec, and
implementation planning before code. Use the GenAI preflight and evaluation
planning required by installed extensions.

## Architecture and Boundary

Use server-first App Router composition with feature-local `application/`,
`api/`, `components/`, and `types/` layers. All business logic, model access,
guardrails, persistence, and provider SDKs remain behind the backend API.

Never add SQL, a database client/driver, an ORM, migrations, schemas, or
connection strings. Never call an LLM provider SDK directly. Route Handlers
and Server Actions may only form a thin session/token/protocol/aggregation BFF.
No ADR can waive the database boundary.

## LLM UI Responsibilities

- Represent streaming, rate-limit, guardrail-rejection, fallback, timeout, and
  unavailable states as typed UI states.
- Preserve backend safety metadata and citations.
- Do not render untrusted model output as executable HTML.
- Keep prompts, provider credentials, safety policy, and model selection out of
  client bundles.
- Reference the backend evaluation suite for every LLM-backed user flow.

## Design, Accessibility, and Evaluation

Follow the approved brand and feature design. References remain advisory.
Test keyboard, focus, reduced motion, loading, partial streaming, error,
fallback, and recovery behavior. Required gates include typecheck, lint,
Vitest, Playwright, axe, API/database boundary checks, and applicable backend
quality/adversarial/retrieval evaluation evidence.

Report contracts used, server/client choices, API-boundary compliance,
evaluation evidence, and ADR status after each increment.
