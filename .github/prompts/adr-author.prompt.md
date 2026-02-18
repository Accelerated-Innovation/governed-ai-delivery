# ADR Author Prompt

You are writing an Architecture Decision Record (ADR) to document a change or exception to the architecture.

Follow this structure and reasoning model:

---

## Title
Short, action-oriented statement. Example: “Introduce Redis-based session store for authentication”

## Context
- What triggered this decision?
- What is the current architecture?
- What constraints or standards are being revisited?
- Which specs or plans does this relate to?

## Decision
- What are we changing, introducing, or formalizing?
- What is the new design pattern, tool, service, or contract?
- What boundaries or dependencies are affected?

## Status
- Proposed / Approved / Rejected / Deprecated

## Consequences
- Positive: list expected benefits (e.g., simpler auth flow, more scalable caching)
- Negative: list tradeoffs (e.g., added latency, new failure points, increased cost)

## Alternatives Considered
- What were the top 2 alternatives?
- Why were they rejected?

## Impacted Modules
- List the layers or services that must change
- Flag any migration, deprecation, or compatibility work

## Compliance Notes
- Does this violate any part of:
  - `ARCH_CONTRACT.md`
  - `BOUNDARIES.md`
  - `SECURITY_AUTH_PATTERNS.md`
  - `API_CONVENTIONS.md`?
- If yes, state why and who approved the exception

## Review
- Required reviewers: team lead, architect, or security lead (based on scope)
- Link to PR or issue that implements the decision

---

Respond with a full ADR in Markdown using the above headings. If required information is missing, stop and request clarification before writing the draft.



