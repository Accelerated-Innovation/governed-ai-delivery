# Model Layering - Databricks Lakehouse

This document defines how Databricks-native data assets are layered.

---

# 1. Default Layering

Use medallion layering unless the team documents a different convention:

- bronze: raw or lightly normalized source-shaped data
- silver: cleaned, conformed, deduplicated, and quality-checked data
- gold: serving models for BI, ML, operational consumers, or published data
  products

The repository may use folder names such as `src/bronze`, `src/silver`, and
`src/gold`, or bundle resource names that make the layer explicit.

---

# 2. Dependency Rules

Layer rules:

- gold assets should not read directly from bronze unless an ADR approves it.
- bronze assets should avoid business joins and derived metrics.
- silver assets own standardization, deduplication, and entity conformance.
- gold assets own consumer contracts, metric definitions, and serving shape.

Cross-layer shortcuts require a documented rationale because they make lineage,
quality ownership, and rollback harder to reason about.

---

# 3. Delta Table Contracts

Each durable table should document:

- owner and support channel
- catalog, schema, and table naming convention
- primary key or uniqueness expectation
- partitioning or clustering rationale when used
- update mode: append, merge, overwrite, streaming, or materialized view
- retention, vacuum, and backfill expectations

Schema evolution must be explicit. Breaking changes need an ADR and downstream
consumer notification.

---

# 4. Notebooks and Modules

Notebooks may orchestrate or demonstrate a transformation, but reusable logic
belongs in versioned modules under `src/` when feasible.

Notebook-only production logic must still satisfy review, testing, PII, and
lineage requirements.
