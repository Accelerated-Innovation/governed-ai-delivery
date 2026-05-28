---
paths_template: layers.inbound
paths:
  - "**/models/staging/**"
  - "**/staging/**"
---

# Staging Layer — Source-Shaped Cleanup

**Authority:**
- `docs/data/architecture/BOUNDARIES.md` — what staging may read + write
- `docs/data/architecture/MODEL_LAYERING.md` (stack overlay) — naming + materialization

Staging models present source data with light cleaning. They are NOT where
business logic happens.

## Rules

- A staging model reads from exactly one `{{ source(...) }}` — never another
  ref(), never a raw warehouse table
- Allowed transformations: renames, type casts, light value cleanup
  (`lower(email)`, `trim(name)`), filtering NULL primary keys
- Forbidden: joins across sources, aggregations, business-logic conditionals
- Model name pattern: `stg_<source>__<table>.sql`
- Materialization: `view` (default)

## PII at the staging boundary

Every column matching the team's PII keyword list (`email`, `phone`, `ssn`,
`dob`, `name`, `address` by default) MUST be:
1. Tagged with `meta.contains_pii: true` in the `_<model>.yml`
2. Wrapped in the project's masking macro per
   `docs/data/architecture/PII_HANDLING.md` (stack overlay)

Generating a staging model that exposes raw PII fails the PII tag check
in CI.

## When in doubt

- If the transformation crosses sources → it belongs in `intermediate/`, not
  staging
- If the transformation aggregates → it belongs in `intermediate/` or `marts/`
- If the source layout is unusual → flag in the PR, don't invent a new
  staging convention

## Anti-patterns

- A staging model that joins two `{{ source(...) }}` calls
- A staging model whose name doesn't mirror the source (`stg_users` when the
  source table is `customers` — misleading)
- A staging model that filters business-logic-relevant rows (e.g., excludes
  test accounts) — that's an intermediate concern
