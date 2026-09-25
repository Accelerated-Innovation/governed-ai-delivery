---
name: govkit-adr-author
description: Author an Architecture Decision Record for a new pattern, exception, or boundary change. Use when the user asks to write an ADR or invokes /govkit-adr-author.
---

# ADR Author

You are writing an Architecture Decision Record (ADR). Determine the ADR title from the user's request; if it is not provided, ask before proceeding.

Follow the template at `docs/{{docs_area}}/architecture/ADR/TEMPLATE.md`. Produce a complete ADR using these sections:

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

Write `Proposed`. Never write `Accepted`.

`Accepted` is a derived state, not a word an author types. It is true because an
approver named in `governance/approval_policy.yaml` approved *this decision* at
*this commit* — the `adr-approval-check` CI gate verifies exactly that, and fails
a pull request whose ADR claims `Accepted` without it. `Rejected` and
`Superseded` are recorded by whoever makes that call, not by you.

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

Naming someone here *requests* a decision; it does not record one. A reviewer assesses evidence or content; only an approver listed in `governance/approval_policy.yaml` commits the decision, and only their approving review — bound to the head commit — makes the ADR Accepted. Leave no signature, date, or approver name here as though the decision were already made.

---

Write the ADR to `docs/{{docs_area}}/architecture/ADR/<slug>.md` with status `Proposed`. If required information is missing, stop and ask before drafting.

Implementation of a dependent feature waits until the ADR is Accepted. That is something you observe — `govkit validate` reports ADRs claiming it without provenance, and `adr-approval-check` proves it — never something you assert by editing the status line.
