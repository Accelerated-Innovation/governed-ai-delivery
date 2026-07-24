---
paths_template: layers.inbound
paths:
  - "**/bronze/**"
---

# Bronze Layer — Source-Shaped Ingest

**Authority:**
- `docs/data/architecture/BOUNDARIES.md` — what bronze may read + write
- `docs/data/architecture/MODEL_LAYERING.md` (stack overlay) — medallion naming + storage

Bronze assets land source data as Delta tables with light normalization.
They are NOT where business logic happens.

## Rules

- A bronze asset reads from exactly one external source (Auto Loader,
  `read_files`, or a declared ingest job) — never from another lakehouse
  layer
- Allowed transformations: renames, type casts, light value cleanup
  (`lower(email)`, `trim(name)`), filtering NULL primary keys
- Forbidden: joins across sources, aggregations, business-logic conditionals
- Write as Delta with schema evolution handled explicitly — no silent
  `mergeSchema` in production paths
- Asset naming and catalog placement follow
  `docs/data/architecture/MODEL_LAYERING.md`

## PII at the bronze boundary

Every column matching the team's PII keyword list MUST be tagged and masked
per `docs/data/architecture/PII_HANDLING.md` (stack overlay) before the data
is readable outside the ingest schema. Generating a bronze asset that
exposes raw PII fails the PII check in CI.

## When in doubt

- If the transformation crosses sources → it belongs in silver, not bronze
- If the transformation aggregates → it belongs in silver or gold
- If the source layout is unusual → flag in the PR, don't invent a new
  ingest convention

## Anti-patterns

- A bronze asset that joins two sources
- A bronze asset whose name doesn't mirror the source (misleading)
- A bronze asset that filters business-relevant rows (e.g., excludes test
  accounts) — that's a silver concern
