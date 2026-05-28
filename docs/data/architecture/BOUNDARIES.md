# Boundaries — Data Layer Rules

This document defines the layer boundary rules. Violations require an ADR.

The default layer vocabulary is **staging / intermediate / marts**. Teams
using medallion (bronze / silver / gold) edit this file + the
`skill_context.architecture.layers` block to swap names — the directionality
rules below still apply.

---

# 1. Allowed Reads

| From | May read |
|---|---|
| staging | sources only |
| intermediate | staging + other intermediate |
| marts | intermediate + other marts |
| snapshots | sources only |
| exposures | marts only |

**Forbidden:**
- marts reading staging directly (bypasses business logic)
- intermediate reading marts (downstream reference; creates cycles)
- any model reading raw warehouse tables without going through a source
- exposures depending on intermediate or staging (consumers must see the
  serving layer)

---

# 2. Cross-Source Constraint

Joins across SOURCES live in `intermediate/`, never in `staging/`. A staging
model presents one source one-to-one (with light cleanup); intermediate is
where the source-crossing business logic happens.

---

# 3. Lineage Direction

Data flows in one direction: source → staging → intermediate → marts →
consumers. A model that violates this direction (e.g., a staging model
reading from an intermediate model) must be refactored OR get an ADR
explaining why the inversion is correct.

---

# 4. PII Crossings

Per-row PII columns must not flow into marts unless:
- The mart is access-controlled by warehouse RBAC AND
- The column is tagged + masked per `PII_HANDLING_CONTRACT.md`

Aggregate marts (no individual-level PII) have no such restriction.

---

# 5. Snapshot Boundaries

Snapshots read directly from sources (not staging) so captured timestamps
reflect when the source actually changed, not when dbt ran. Snapshots feed
intermediate or marts; nothing should feed BACK into snapshots.

---

# 6. CI Enforcement

The following should be wired into CI (per stack overlay's TESTING.md):
- Layer-boundary checks (dbt-project-evaluator, or custom)
- PII tag presence on staging columns
- New mart without an exposure entry (warns; blocks if persistent across releases)

---

# 7. When to Add a New Layer

Adding a layer between staging and intermediate (or between intermediate
and marts) requires an ADR. Three-layer is the default for a reason:
each additional layer is another hop for the agent to reason about, and
the marginal value drops fast after 3.

Common temptations + the usual answer:
- "We need a 'shared dimensions' layer" → that's intermediate
- "We need a 'reporting' layer above marts" → that's exposures + dashboards
- "We need a 'cleaning' layer below staging" → that belongs to the source owner
