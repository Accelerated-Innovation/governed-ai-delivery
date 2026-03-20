---
description: "Author an Architecture Decision Record for a React UI architectural decision"
agent: "ask"
---

# ADR Author — React UI

You are authoring an Architecture Decision Record for a React UI architectural decision.

Before writing, read all existing accepted ADRs in `docs/ui/architecture/ADR/`. Do not contradict an accepted ADR without explicitly superseding it.

Produce the ADR in `docs/ui/architecture/ADR/` using this structure:

## ADR-NNN — [Decision Title]

**Status:** Proposed
**Date:** [YYYY-MM-DD]

### Context
What situation requires this decision? What constraints apply?

### Decision
What is being decided and why?

### MVVM Impact
Which layers are affected? Do any boundary rules change?

### Consequences
- What becomes easier?
- What becomes harder?
- What is the rollback path?

### Alternatives Considered
At least two alternatives with reasons for rejection.

---

The ADR is not Accepted until reviewed. Implementation must not begin on dependent features until status is Accepted and the ADR is referenced in `plan.md`.
