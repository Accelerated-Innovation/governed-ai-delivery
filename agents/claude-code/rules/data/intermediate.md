---
paths_template: layers.domain
paths:
  - "**/models/intermediate/**"
  - "**/intermediate/**"
---

# Intermediate Layer — Business Logic

**Authority:**
- `docs/data/architecture/BOUNDARIES.md`
- `docs/data/architecture/MODEL_LAYERING.md` (stack overlay)

Intermediate models compose staging models into reusable business entities.
This is WHERE business logic lives — not in staging, not in marts.

## Rules

- Reads from staging models OR other intermediate models, via `{{ ref(...) }}`
- May NOT read from `marts/` (creates cycles + downstream dependencies)
- Materialization: `ephemeral` (default) or `view`
- Naming: `int_<business_concept>__<verb>.sql`
- Cross-source joins go HERE, not in staging

## Required documentation

Every intermediate model declares:
- Description ≥ 1 sentence on what business concept it represents
- For joins: the join key + cardinality
- If consumed by exactly one mart: consider inlining instead

## When in doubt

- If an intermediate model is referenced by exactly one mart → inline it
  into the mart
- If an intermediate model has > 5 downstream consumers → it's a building
  block, fine to keep
- If two intermediate models compute overlapping concepts → consolidate

## Anti-patterns

- Intermediate referenced by zero models (dead code; delete)
- Intermediate with the same shape as a staging model (no business logic
  added — delete and let consumers ref staging)
- Intermediate that aggregates AND filters AND joins (split into smaller
  composable steps)
