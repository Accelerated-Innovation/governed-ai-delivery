# Technology Stack - Databricks Lakehouse

This document defines the approved Databricks-native stack for this data
repository. GovKit governs repository delivery contracts; Databricks provides
the platform runtime.

---

# 1. Platform Boundary

Approved platform surfaces:

- Unity Catalog for catalog, schema, table, volume, permission, and lineage
  governance
- Delta tables for durable storage contracts
- Databricks Asset Bundles for deployable configuration
- Databricks Jobs and Lakeflow Pipelines for orchestration
- PySpark and SQL for transformations
- Notebooks only when source-controlled and reviewable

Workspace calls, deployments, and pipeline/job execution are not assumed to be
available in CI. Treat them as opt-in once service principals, secrets, target
schemas, and cost controls are configured.

---

# 2. Repository Layout

Preferred layout:

```text
databricks.yml
resources/
  jobs.yml
  pipelines.yml
src/
  transforms/
  quality/
  shared/
notebooks/
tests/
docs/data/architecture/
```

Rules:

- Put reusable transformation logic in `src/`, not only in notebooks.
- Keep bundle resources in `resources/` or another documented bundle include.
- Keep environment-specific names in bundle targets or variables.
- Do not commit workspace personal paths, tokens, or ad hoc cluster ids.

---

# 3. Runtime Defaults

Approved defaults:

- Python 3.11 or the Databricks Runtime default documented by the platform team
- PySpark APIs for production transformations
- SQL for simple views, quality checks, and analyst-owned transformations
- Delta table constraints and expectations where the runtime supports them

New runtime families, external orchestrators, or non-Delta storage contracts
require an ADR.

---

# 4. Environment Separation

Each environment must have an explicit catalog and schema strategy:

- dev: individual or team-isolated schemas
- ci: short-lived schemas or validation-only targets
- staging: production-like permissions and data shape
- prod: least-privilege production catalog/schema permissions

CI must not deploy or execute Databricks workloads unless the repo documents
the target workspace, identity, isolation strategy, and cost guardrails.
