# Lineage + Observability — dbt Implementation

This document defines how lineage and observability are emitted from dbt
models in this repository. The universal contract lives at
`docs/data/architecture/LINEAGE_CONTRACT.md`; this file is the dbt-specific HOW.

---

# 1. dbt Artifacts

Every CI run produces:
- `target/manifest.json` — the DAG, model SQL, descriptions, tests, columns
- `target/run_results.json` — what ran, when, success/failure, duration
- `target/catalog.json` — column-level metadata from the warehouse

Rules:
- ALL three artifacts uploaded to artifact storage on every CI run
- `prod` runs additionally upload to the lineage tool of choice (see §3)
- Artifacts retained for at least 30 days (lineage retention contract)

Standard CI step:
```bash
dbt docs generate
# Upload target/manifest.json + target/run_results.json + target/catalog.json
```

---

# 2. Exposures (Downstream Documentation)

Declare every downstream consumer in `models/marts/_exposures.yml`:

```yaml
exposures:
  - name: customer_360_dashboard
    type: dashboard
    url: https://looker.example.com/dashboards/42
    description: Sales team's primary customer-health view
    depends_on:
      - ref('dim_customers')
      - ref('fct_orders')
      - ref('fct_subscriptions')
    owner:
      name: Analytics Team
      email: analytics@example.com

  - name: customer_lifecycle_email_export
    type: application
    description: Reverse-ETL job populating Hightouch → Marketo
    depends_on:
      - ref('dim_customers')
    owner:
      name: Marketing Eng
      email: martech@example.com
```

Rule: every mart consumed by a downstream system has an exposure entry.
`dbt docs serve` then visualizes "what breaks if I change this mart" —
the foundation for impact analysis.

---

# 3. Lineage Destination

One of (declared in TECH_STACK.md, ADR if changing):

| Tool | Integration |
|---|---|
| **dbt Cloud** | Native — `manifest.json` ingested automatically |
| **OpenLineage** | `dbt-ol` wrapper around `dbt run`/`dbt test`; emits OpenLineage events |
| **Datahub** | `datahub-dbt` ingestion job, scheduled post-CI |
| **Atlan / Collibra** | Vendor-specific ingestion of `manifest.json` |
| **Custom** | Parse `manifest.json` + `run_results.json` and push to internal API |

Whichever is chosen:
- Mart-level lineage MUST be captured (which sources feed which marts)
- Column-level lineage is required for PII-tagged columns
- Lineage refreshed at least daily

---

# 4. Operational Observability

Beyond lineage, the team needs **operational** signals:

| Signal | Where it comes from | Alerts on |
|---|---|---|
| Job success/failure | `run_results.json` post-job | Failure |
| Job duration | `run_results.json` `execution_time` | >2× the rolling 7-day median |
| Source freshness | `dbt source freshness` | `error` threshold breach |
| Row count anomalies | `dbt-expectations` + warehouse metrics | Outside expected range |
| PII tag drift | CI script | Missing tag on a known PII column |

Wire these into PagerDuty / Slack / whatever the team uses. Configure in
`.github/workflows/dbt-prod.yml` or your scheduler of choice.

---

# 5. Warehouse-Side Metrics

Beyond dbt's own outputs, capture from the warehouse:

- **Query duration** of mart-reading dashboards (helps identify slow marts)
- **Storage growth** per dataset (helps prune unused intermediate tables)
- **Cost attribution** per dbt run (Snowflake's `QUERY_HISTORY`, BigQuery's
  `INFORMATION_SCHEMA.JOBS`)

These belong in a dashboard, not in dbt. Recommended: a single `dbt_observability`
schema in the warehouse populated by a daily job that aggregates the above.

---

# 6. Incident Response

When a data-quality alert fires:

1. **Triage** — is it a real issue or a test threshold miscalibration?
2. **Identify blast radius** — query `manifest.json` for downstream models
   + exposures; notify those owners
3. **Decide: pause or patch** — pause the affected mart's refresh OR ship
   a hotfix PR (skip CI? require ADR per the universal contract)
4. **Document** — record incident in the team's incident log; if the root
   cause is structural, raise an ADR for the structural fix

---

# 7. What NOT to Track

- Per-row audit logs (too much data, low value — use sampling)
- Every column lineage (only PII + key columns; rest is overhead)
- Dashboard interactions (different tool surface — that's BI's job)
- Source system internals (the upstream owner's responsibility)

---

# 8. Required `dbt_project.yml` Settings

```yaml
# dbt_project.yml
on-run-end:
  - "{{ create_audit_table_if_not_exists() }}"
  - "{{ insert_run_audit_record() }}"
```

Where `audit_table` captures: run_id, started_at, finished_at, status,
invocation_args. Lets the team query "show me all dbt runs in the last
24 hours and which failed" without leaving the warehouse.
