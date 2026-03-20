# Features

This directory contains feature starters and fully worked reference examples.

---

## Starters

Copy the appropriate starter when beginning a new feature. Every starter contains the five required artifacts with instructions and placeholder content.

| Starter | Use for | Copy from |
|---|---|---|
| `starter_backend/` | Python / Hexagonal Architecture features | `features/starter_backend/` |
| `starter_ui/` | React or Angular UI features (MVVM) | `features/starter_ui/` |

---

## Worked Examples

Fully populated end-to-end references showing every artifact completed. Use these to understand what "done" looks like before you start.

| Example | Domain | Type | ADR |
|---|---|---|---|
| `schema_contract_example/` | Schema contract publication service | Backend — Hexagonal | [ADR-001](../docs/backend/architecture/ADR/ADR-001-schema-contract-ownership.md) |
| `ui_task_dashboard/` | Task dashboard with filter and optimistic update | React UI — MVVM | None required |

---

## Required Artifacts (all features)

Every feature folder must contain these five files before Architecture Preflight begins:

| File | Purpose |
|---|---|
| `acceptance.feature` | Gherkin scenarios tagged with `@nfr-*`, `@e2e`, `@accessibility`, `@contract` |
| `nfrs.md` | Non-functional requirements — no TBD entries permitted |
| `eval_criteria.yaml` | Evaluation configuration validated against the agent's schema |
| `architecture_preflight.md` | Pre-implementation alignment check |
| `plan.md` | Incremental plan including mandatory Evaluation Compliance Summary |

See the main [README](../README.md) for the full feature workflow.
