# Architecture Contract — Data Shape

This document defines the top-level architecture for data work in this
repository. It applies regardless of which stack overlay is installed
(dbt, Airflow, Dagster, Spark, etc.).

This is a **starter contract** — review and adapt to your team's reality.

---

# 1. The Shape

A data project ships:
- **Pipelines** that move + transform data on a schedule (or in response to events)
- **Models** that codify the transformations (declaratively where possible)
- **Tests** that codify the correctness invariants
- **Marts** (or equivalent serving layer) that downstream consumers read

What is NOT in scope for this kit (yet):
- ML training + serving (different shape; coming as a separate type)
- Real-time event processing (different shape; coming as `--type stream`)
- Notebook-only exploratory work (different scoping — see DESIGN_PRINCIPLES)

---

# 2. The Layering Convention

Source → **staging** → **intermediate** → **marts** → consumers.

Each layer has a clear purpose (see `MODEL_LAYERING.md` for the stack-specific
guide). The boundary rules in `BOUNDARIES.md` are enforced by code review.

Teams using medallion (bronze/silver/gold) can keep that vocabulary and edit
`skill_context.architecture.layers` accordingly — the contracts in this dir
still apply.

---

# 3. Ownership

Every dataset (mart, intermediate, source) has:
- A named owner (team or individual)
- A documented purpose
- Declared downstream consumers (`exposures.yml` in dbt; equivalent elsewhere)

Datasets with no declared owner are scheduled for deprecation at the next
calibration review.

---

# 4. Reproducibility

Every dataset must be reproducible from its inputs:
- Source data + dbt project (or equivalent) at a known revision → identical mart
- No manual overrides in production tables
- Backfills go through the same code path as scheduled runs

Hot patches require an ADR + a follow-up PR that codifies the fix.

---

# 5. Change Control

| Change | Required |
|---|---|
| New staging model | Code review |
| New intermediate model | Code review |
| New mart | Code review + downstream owner sign-off |
| Mart column removal/rename | ADR + deprecation period |
| New source | Code review + source owner contact |
| New ML model in production | ADR + model card (when ML type ships) |
| Cross-environment promotion of new data product | ADR |

---

# 6. ADR Triggers

An ADR is required when:
- Introducing a new framework (Airflow → Dagster, dbt → SQLMesh)
- Introducing a new persistence layer (warehouse swap, new data lake)
- Crossing a layer boundary (mart reading staging directly)
- Bypassing the test gate (severity downgrade, skipped test in CI)
- Changing PII handling rules

ADRs live at `docs/data/architecture/ADR/`. Use the template.
