---
name: govkit-ui-adr-author
description: Author an Architecture Decision Record for a UI architectural decision. Use when the user asks to write a UI ADR or invokes /govkit-ui-adr-author.
---

# ADR Author — UI

You are authoring an Architecture Decision Record for a UI architectural decision. Determine the decision title from the user's request; if it is not provided, ask before proceeding.

Read all existing accepted ADRs in `docs/ui/architecture/ADR/` before writing. Do not contradict an accepted ADR without explicitly superseding it.

Use the template at `docs/ui/architecture/ADR/TEMPLATE.md` and produce the ADR in `docs/ui/architecture/ADR/`.

---

The ADR must cover:

1. **Status** — write `Proposed`, and never `Accepted`
2. **Context** — What situation requires this decision? What constraints apply?
3. **Decision** — What is being decided and why?
4. **MVVM Impact** — Which layers are affected? Do any boundary rules change?
5. **Consequences** — What becomes easier? What becomes harder? What is the rollback path?
6. **Alternatives Considered** — At least two alternatives with reasons for rejection

`Accepted` is a derived state, not a word an author types. It is true because an approver named in `governance/approval_policy.yaml` approved *this decision* at *this commit* — the `adr-approval-check` CI gate verifies exactly that, and fails a pull request whose ADR claims `Accepted` without it. `Rejected` and `Superseded` are recorded by whoever makes that call, not by you.

The Approval section requests a decision; it does not record one. A reviewer assesses evidence or content; only an approver in the policy commits the decision. Leave no signature, date, or approver name there as though it were already made.

Implementation of a dependent feature waits until the ADR is Accepted. That is something you observe — `govkit validate` reports ADRs claiming it without provenance — never something you assert by editing the status line.

An ADR can document a backend API contract or thin-BFF tradeoff. It cannot
permit SQL, database clients/drivers, ORMs, migrations, connection strings, or
backend-owned business logic in a UI repository.
