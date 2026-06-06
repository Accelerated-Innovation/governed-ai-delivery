# Testing - Databricks Lakehouse

This document defines the testing floor for Databricks-native data delivery.

---

# 1. Local Static Checks

Blocking by default:

- Python unit tests for pure transformation modules with `pytest`
- import and syntax checks for source-controlled notebooks when tooling exists
- bundle configuration validation when Databricks CLI authentication is
  available
- static scans for secrets, personal paths, hardcoded workspace URLs, and
  unreviewed catalog/schema names

Tests that require Databricks compute are opt-in until CI identity, workspace,
target schema, and cost controls are approved.

---

# 2. Transformation Unit Tests

Write business logic in testable Python modules whenever possible.

Rules:

- Isolate DataFrame transformation functions from Jobs/Pipeline wiring.
- Test schema changes, null behavior, joins, deduplication, and error branches.
- Use small in-memory fixtures; do not require production data for unit tests.
- Keep notebooks as orchestration or exploration surfaces, not the only testable
  implementation.

---

# 3. Data Quality Tests

Required data quality coverage:

- primary key uniqueness where a table has a natural or surrogate key
- not-null checks for required columns
- referential integrity or documented exceptions
- freshness or latency expectations for externally consumed tables
- PII tag and masking expectations for sensitive columns

Warehouse-backed data quality execution is opt-in in CI. If enabled, it must
run against isolated schemas with bounded data and compute.

---

# 4. Acceptance Criteria

Every governed data feature should include acceptance criteria that name:

- affected tables, views, jobs, or pipelines
- expected input and output data shape
- quality checks that must block release
- lineage or downstream consumers impacted
- rollback or replay expectations
