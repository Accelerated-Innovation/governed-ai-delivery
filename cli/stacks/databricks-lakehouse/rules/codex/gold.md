# Gold Layer — Serving Contracts

**Authority:**
- `docs/data/architecture/BOUNDARIES.md` — what gold may read + write
- `docs/data/architecture/MODEL_LAYERING.md` (stack overlay) — consumer contracts + change control

Gold assets are the public API of the lakehouse: BI, ML, operational
consumers, and published data products read gold only.

## Rules

- Gold reads from silver (and other gold) — reading bronze directly
  requires an ADR
- Treat every gold column list as a public contract: renames and removals
  are breaking changes requiring a deprecation notice, consumer
  coordination, and an ADR (per `MODEL_LAYERING.md` change control)
- Every gold asset declares its downstream consumers (exposure/lineage
  registration per `docs/data/architecture/LINEAGE_OBSERVABILITY.md`)
- Metric definitions live in gold, defined once — two gold assets must not
  redefine the same metric

## When in doubt

- If no consumer is known → don't ship the asset (no exposure means dead
  code or an undocumented consumer)
- If the change alters a served column → treat it as breaking until proven
  otherwise

## Anti-patterns

- A gold asset that is never queried (delete it)
- Two gold assets with overlapping concepts (consolidate)
- Consumer-specific one-off shapes proliferating instead of a shared
  contract + view
