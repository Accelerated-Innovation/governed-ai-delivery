# Features

This directory contains feature starters and fully worked reference examples.

---

## Starters

Copy the appropriate starter when beginning a new feature. Backend/data
starters contain the five common artifacts. UI starters add `design.md` and
reference-image guidance as a sixth governed input.

Not every change is a feature. A defect that *restores* behavior something
already established uses the defect lane instead — one record at
`fixes/<id>/fix.yaml` from `govkit fix init <id>`, not five artifacts here.
See the defect lifecycle in the root README.

| Starter | Use for | Copy from |
|---|---|---|
| `starter_backend/` | Python / Hexagonal Architecture API features | `features/starter_backend/` |
| `starter_cli/` | Python CLI tools (Click/Typer, Hexagonal Architecture) | `features/starter_cli/` |
| `starter_ui/` | React or Angular UI features (MVVM) | `features/starter_ui/` |
| `starter_ui_nextjs/` | Next.js App Router + Tailwind CSS features | `features/starter_ui_nextjs/` |

---

## Worked Examples

Fully populated end-to-end references showing every artifact completed. Use these to understand what "done" looks like before you start.

| Example | Domain | Type | ADR |
|---|---|---|---|
| `schema_contract_example/` | Schema contract publication service | Backend — Hexagonal | [ADR-001](../docs/backend/architecture/ADR/ADR-001-schema-contract-ownership.md) |
| `ui_task_dashboard/` | Task dashboard with filter and optimistic update | React UI — MVVM | None required |

---

## Required Artifacts

Every feature folder must contain these five files before Architecture Preflight begins:

| File | Purpose |
|---|---|
| `acceptance.feature` | Gherkin scenarios tagged with `@nfr-*`, `@e2e`, `@accessibility`, `@contract` |
| `nfrs.md` | Non-functional requirements — no TBD entries permitted |
| `eval_criteria.yaml` | Evaluation configuration validated against the agent's schema |
| `architecture_preflight.md` | Pre-implementation alignment check |
| `plan.md` | Incremental plan including mandatory Evaluation Compliance Summary |

UI feature folders must also contain:

| File | Purpose |
|---|---|
| `design.md` | Screens/states, brand application, responsive/accessibility behavior, and reference authority |

UI starters include `design/references/README.md`. Screenshots, sketches, and
mockups placed there are advisory unless `design.md` explicitly promotes a
named property to an accepted requirement.

See the main [README](../README.md) for the full feature workflow.
