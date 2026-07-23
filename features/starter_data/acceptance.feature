Feature: customer_dim daily refresh

  The customer_dim mart is the canonical view of customer state, refreshed
  daily from source.customers. Downstream consumers (Looker dashboards,
  the marketing reverse-ETL job) depend on it being fresh, unique on
  customer_id, and PII-masked outside production.

  Background:
    Given the customer_dim_daily pipeline is owned by analytics-eng@example.com
    And the source dataset stripe.customers has a freshness SLA of 24 hours

  Scenario: New customers propagate to the mart on the next refresh
    Given a customer is inserted into source.customers at "2026-05-27T14:00:00 UTC"
    When the customer_dim_daily pipeline completes its next run
    Then the customer SHALL be present in marts.customer_dim
    And the dim_loaded_at column SHALL be the pipeline completion time

  Scenario: Deletions in source propagate
    Given a customer is hard-deleted from source.customers
    When the customer_dim_daily pipeline runs
    Then the customer SHALL NOT be present in marts.customer_dim

  @nfr-freshness
  Scenario: Most recent refresh no older than 1 hour after expected run
    Given the customer_dim_daily pipeline is scheduled for 06:00 UTC
    When the analytics team queries marts.customer_dim at 07:00 UTC
    Then the max(dim_loaded_at) SHALL be ≥ today 06:00 UTC
    And the staleness metric SHALL be ≤ 1 hour

  @nfr-quality
  Scenario: Uniqueness invariant on the natural key
    Given a successful refresh of marts.customer_dim
    Then customer_id SHALL be unique
    And customer_id SHALL be non-null for every row
    And the row count SHALL be within 10% of the source.customers row count

  @nfr-quality
  Scenario: Required columns are populated
    Given a successful refresh of marts.customer_dim
    Then customer_id, dim_loaded_at, and is_active SHALL be non-null for every row
    And dim_loaded_at SHALL be ≥ the previous refresh's dim_loaded_at

  @nfr-pii
  Scenario: PII columns masked outside production
    Given an analyst querying marts.customer_dim in the "staging" environment
    Then customer_email SHALL be masked per docs/data/architecture/PII_HANDLING_CONTRACT.md
    And customer_phone SHALL be masked
    And the analyst SHALL see "pii.<md5-of-original>" style values, not real PII

  @nfr-pii
  Scenario: PII unmasked only with the un-mask role
    Given an analyst with the "pii_unmask" warehouse role queries marts.customer_dim
    When the analyst queries in the "prod" environment
    Then customer_email SHALL return the real value
    And the query SHALL be recorded in the access audit log

  @nfr-lineage
  Scenario: Lineage captured on every prod run
    Given the customer_dim_daily pipeline completes a prod run
    Then the lineage tool SHALL show source.customers as an upstream dataset
    And the lineage tool SHALL show marts.customer_dim's downstream exposures
    And the lineage SHALL include column-level edges for PII-tagged columns

  @nfr-reliability
  Scenario: Backfill is idempotent
    Given marts.customer_dim was last refreshed at "2026-05-27T06:00:00 UTC"
    When operators run a backfill from "2026-05-20" to "2026-05-27"
    Then marts.customer_dim row count SHALL be identical to the pre-backfill state
    And no duplicate customer_ids SHALL appear
    And every dim_loaded_at SHALL be ≤ the backfill completion time

  @nfr-cost
  Scenario: Refresh stays within cost envelope
    Given the customer_dim_daily pipeline's rolling 7-day median credit usage is X
    When a daily refresh completes
    Then the credit usage SHALL be ≤ 2 × X
    And exceedances SHALL alert oncall (warn, not block)

  @nfr-observability
  Scenario: Pipeline failure alerts oncall
    Given the customer_dim_daily pipeline fails a scheduled run
    Then Slack #data-oncall SHALL receive a failure alert
    And the run SHALL appear in the dbt_observability dashboard with its duration

  @nfr-compliance
  Scenario: Right-to-be-forgotten propagates through the mart
    Given a customer exercises GDPR deletion in the source system
    When the deletion lands in source.customers
    Then the customer SHALL be absent from marts.customer_dim within 24 hours
    And the deletion SHALL be recorded in the audit log for 1 year
