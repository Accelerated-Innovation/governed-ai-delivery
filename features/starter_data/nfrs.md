# NFRs — customer_dim daily refresh

This file defines the non-functional requirements for the
`customer_dim_daily` pipeline. Every category below must have at least one
tagged scenario in `acceptance.feature` covering it.

Replace every **TBD** with a real value before this feature ships.

---

## Repository Scope

- [ ] **This repository only**
- [ ] **Multiple repositories** — list each repo, its owner, the modules
  involved, and the contracts exposed:

| Repo | Owner | Module | Contract |
|---|---|---|---|

**Primary Owner:** analytics-eng@example.com
**Key Cross-Repo Contracts:** N/A (data project; source contracts owned by
the Stripe ingestion team — `stripe-sync@example.com`)

---

## @nfr-freshness

| Concern | Target |
|---|---|
| Schedule | Daily 06:00 UTC |
| Max staleness at query time | 1 hour after scheduled completion |
| Alert threshold | 2× max staleness (2 hours) → Slack #data-oncall |
| Block threshold | 4× max staleness (4 hours) → PagerDuty |

Measurement source: `max(dim_loaded_at)` on every query OR a freshness
metric emitted to the observability tool.

---

## @nfr-quality

| Concern | Target |
|---|---|
| Primary key uniqueness | `customer_id` unique, severity `error` |
| Non-null on PK + load time | `customer_id`, `dim_loaded_at` non-null, severity `error` |
| Row count drift vs source | Within 10% of source.customers row count, severity `warn` |
| Required column population | `customer_id`, `dim_loaded_at`, `is_active` non-null, severity `error` |
| Distribution: customers per state | TBD (calibrate after 2 weeks of stable runs) |

Tests live in `models/marts/_customer_dim.yml` (schema tests) +
`tests/dim_customers_*.sql` (custom singular tests).

---

## @nfr-pii

| Column | Category | Non-prod treatment | Prod access |
|---|---|---|---|
| `customer_email` | contact | Hashed (`pii.` + md5) | `pii_unmask` warehouse role |
| `customer_phone` | contact | Hashed | `pii_unmask` warehouse role |
| `billing_address` | identity | Synthetic equivalent | `pii_unmask` warehouse role |
| `tax_id_last4` | sensitive | `REDACTED` literal | `pii_finance` warehouse role |

Masking macro: `{{ mask_pii('customer_email', 'contact') }}` per
`docs/data/architecture/PII_HANDLING.md` (stack overlay).

CI gate: `scripts/check_pii_tags.py` confirms every column matching the
PII keyword list is tagged + masked.

---

## @nfr-lineage

| Concern | Target |
|---|---|
| Source-to-mart capture | Every prod run |
| Column lineage for PII | Required for `customer_email`, `customer_phone`, `billing_address`, `tax_id_last4` |
| Exposure tracking | `models/marts/_exposures.yml` lists every downstream consumer |
| Retention | 90 days in lineage tool, 1 year in warehouse audit table |

Lineage destination: TBD (Datahub / OpenLineage / dbt Cloud — pick one).

---

## @nfr-reliability

| Concern | Target |
|---|---|
| Idempotency | Re-running the same date range produces identical output |
| Backfill correctness | Backfills produce the same row count as scheduled runs |
| Partial-failure recovery | On `error` test failure, refresh paused; next run re-attempts |
| Schema drift response | New source column → manual review; removed source column → ADR |

Backfill instructions: `dbt build --select state:modified+ --vars '{"start_date": "...", "end_date": "..."}'`

---

## @nfr-cost

| Concern | Target |
|---|---|
| Rolling 7-day median credit usage | Baseline TBD after 2 weeks |
| Per-run cost alert threshold | 2× the median |
| Storage growth target | < 10% month-over-month |

Cost source: warehouse's `QUERY_HISTORY` / `INFORMATION_SCHEMA.JOBS`
aggregated daily into the `dbt_observability` schema.

---

## @nfr-observability

| Signal | Destination | Alert? |
|---|---|---|
| Job success/failure | Slack #data-oncall | YES on failure |
| Job duration | dashboard `dbt_observability` | warn on >2× median |
| Source freshness breach | Slack #data-oncall + source owner | YES (warn) |
| Schema test failure | Slack #data-oncall | YES on `error` |
| Row count anomaly | dashboard | warn |
| PII tag drift (CI) | PR comment | YES (blocks merge) |

---

## @nfr-compliance

| Concern | Required |
|---|---|
| GDPR right-to-be-forgotten | Deletion in source propagates within 24 hours |
| Audit log retention | 1 year minimum |
| Data residency | TBD (US-only? EU separate region? confirm with security) |
| Consent tracking | TBD (does source carry consent flags? do marts need to filter?) |

This category often needs a separate security review beyond what the
data team owns.

---

## Out of scope (this NFRs file)

- Source system reliability (owned by `stripe-sync@example.com`)
- Dashboard performance (owned by the BI team; SLAs in their NFRs file)
- Cross-region replication (warehouse-team concern)
