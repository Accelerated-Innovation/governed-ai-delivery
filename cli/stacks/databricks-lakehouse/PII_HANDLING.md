# PII Handling - Databricks Lakehouse

This document defines sensitive data expectations for Databricks-native data
assets.

---

# 1. Classification

Sensitive columns must be classified before release. At minimum, document:

- direct identifiers such as email, phone, address, government id, or account id
- quasi-identifiers such as name, date of birth, postal code, or device id
- financial, health, employment, or other regulated attributes
- derived features that can reveal sensitive status

Unknown classification is not acceptable for gold/public serving assets.

---

# 2. Unity Catalog Controls

Use Unity Catalog as the governance boundary where available:

- catalog/schema/table ownership must be explicit
- permissions must follow least privilege
- sensitive columns should use tags or documented policy metadata
- row filters, column masks, or views should be used where appropriate
- non-prod access to sensitive data must be minimized or masked

Repos without Unity Catalog need a documented transitional control plan.

---

# 3. Development and CI Data

Development and CI must not require production PII by default.

Rules:

- use synthetic, masked, sampled, or isolated data for tests
- never commit extracted production data
- never commit Databricks tokens, PATs, secrets, or workspace credentials
- avoid personal workspace paths in bundle/job/pipeline configs

If live data access is required, document the identity, table scope, purpose,
and approval path.

---

# 4. Release Expectations

Before release, every sensitive table or column must have:

- classification
- owner
- masking or access policy
- downstream consumer awareness
- retention or deletion expectation when applicable
