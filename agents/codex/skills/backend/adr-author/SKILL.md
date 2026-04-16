---
name: adr-author
description: Author an Architecture Decision Record for a new pattern, exception, or boundary change
---

# ADR Author

You are writing an Architecture Decision Record (ADR). Determine the ADR title from the user's request; if it is not provided, ask before proceeding.

Follow the template at `docs/backend/architecture/ADR/TEMPLATE.md`. Produce a complete ADR using these sections:

## Title

Short, action-oriented statement describing the decision.

## Context

- What triggered this decision?
- What is the current architecture?
- What constraints or standards are being revisited?
- Which specs or plans does this relate to?

## Decision

- What are we changing, introducing, or formalizing?
- What boundaries or dependencies are affected?

## Status

Proposed / Approved / Rejected / Deprecated

## Consequences

- Positive: expected benefits
- Negative: tradeoffs (latency, failure points, cost, complexity)

## Alternatives Considered

Top 2 alternatives and why they were rejected.

## Impacted Modules

Layers or services that must change. Flag any migration, deprecation, or compatibility work.

## Compliance Notes

Does this violate any part of `ARCH_CONTRACT.md`, `BOUNDARIES.md`, `SECURITY_AUTH_PATTERNS.md`, or `API_CONVENTIONS.md`? If yes, state why and who approved the exception.

## Review

Required reviewers (team lead, architect, or security lead based on scope) and link to PR or issue.

---

Write the ADR to `docs/backend/architecture/ADR/<slug>.md`. If required information is missing, stop and ask before drafting.
