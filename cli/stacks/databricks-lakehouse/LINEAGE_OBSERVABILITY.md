# Lineage and Observability - Databricks Lakehouse

This document defines the minimum observability and lineage expectations for
Databricks-native data delivery.

---

# 1. Lineage

Unity Catalog lineage is the preferred lineage source where available.

Each governed change should identify:

- upstream tables, files, streams, or external sources
- transformed Delta tables or views
- downstream jobs, dashboards, ML features, or consumers
- ownership and support route for each published asset

When automated lineage is unavailable, document manual lineage in the feature
plan or architecture notes.

---

# 2. Operational Observability

Jobs and pipelines should expose:

- success/failure status
- duration and retry count
- rows read/written where available
- late, missing, or duplicated source data indicators
- data quality failures and quarantined records
- cost or compute usage signals for expensive workloads

Alerts must route to an accountable team, not only to an individual developer.

---

# 3. Data Quality Signals

Data quality findings should name:

- asset and layer
- failed expectation
- affected row count or bounded sample
- severity and release impact
- owner and remediation path

Warnings may be acceptable for exploratory or bronze assets. Published silver
and gold assets need explicit blocking criteria.

---

# 4. Cost and Runtime Review

Expensive workloads require a review of:

- cluster/serverless policy
- expected schedule and concurrency
- input data volume
- backfill behavior
- budget or alert threshold

Pipeline execution should not be enabled in CI until these controls are
documented.
