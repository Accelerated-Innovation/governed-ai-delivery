# Pipeline Contract - Databricks Lakehouse

This document defines deployment and orchestration expectations for Databricks
Jobs and Lakeflow Pipelines.

---

# 1. Asset Bundle Contract

Databricks Asset Bundles are the preferred packaging contract.

Required when bundles are used:

- `databricks.yml` at the repo root or documented bundle root
- named targets for dev, ci, staging, and prod where applicable
- resource definitions in reviewable YAML files
- variables for catalog, schema, workspace host, and environment names
- no personal workspace paths or user-specific compute in committed resources

If the repo does not use Asset Bundles, document the alternate deployment
contract and why it is acceptable.

---

# 2. Job and Pipeline Rules

Jobs and Lakeflow Pipelines must define:

- owner and on-call/support expectation
- schedule or trigger policy
- input and output data assets
- retry and timeout behavior
- compute policy or serverless/runtime expectation
- alerting or failure notification route

Production schedules require approval and should not be inferred from examples
or development notebooks.

---

# 3. CI Boundary

Allowed by default:

- static bundle/config checks
- source linting and unit tests
- validation commands that do not require paid compute when credentials are
  absent

Opt-in only:

- `databricks bundle deploy`
- Jobs or Lakeflow Pipeline runs
- data quality checks against a live warehouse
- source freshness or table scans

Opt-in execution requires documented identity, target environment, isolated
schema/catalog, and cost controls.

---

# 4. Rollback and Replay

Every production pipeline must document the rollback or replay path:

- how to disable a schedule or trigger
- how to rerun a bounded date/key range
- how to repair partially written Delta tables
- how downstream consumers are notified
