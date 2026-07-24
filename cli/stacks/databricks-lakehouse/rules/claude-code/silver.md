---
paths_template: layers.domain
paths:
  - "**/silver/**"
---

# Silver Layer — Conformed Business Entities

**Authority:**
- `docs/data/architecture/BOUNDARIES.md` — what silver may read + write
- `docs/data/architecture/MODEL_LAYERING.md` (stack overlay) — medallion layering

Silver assets own standardization, deduplication, and entity conformance.
This is where business transformations live.

## Rules

- Silver reads from bronze and other silver assets — never directly from
  external sources, never from gold
- Deduplicate and conform entities here: one silver asset per business
  concept, not per consumer
- Enforce data-quality expectations at silver (per
  `docs/data/architecture/DATA_QUALITY_CONTRACT.md`) — quality-checked data
  is this layer's contract
- Prefer PySpark/SQL transformations tracked in source control; notebooks
  follow the team's notebook policy in
  `docs/data/architecture/TECH_STACK.md`

## When in doubt

- If it is consumer- or serving-shaped → it belongs in gold
- If it reads an external source → the ingest belongs in bronze
- If two silver assets overlap conceptually → consolidate before adding a
  third

## Anti-patterns

- A silver asset referenced by exactly one gold asset that only renames
  columns (inline it)
- Bypassing bronze to "save a hop" (breaks lineage + replayability)
- Quality checks deferred to gold (consumers see unchecked data)
