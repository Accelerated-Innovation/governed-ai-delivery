# Environments

This document defines the environment isolation contract for data work
in this repository. Stack-specific implementation (profiles.yml,
orchestrator targets, schedule definitions) lives in the overlay docs.

---

# 1. The Four Environments

| Environment | Purpose | Schedule | PII | Alerts |
|---|---|---|---|---|
| `dev` | Developer-personal scratch | On demand | Masked | None |
| `ci` | PR-ephemeral validation | On PR + main push | Masked | None (CI logs only) |
| `staging` | Pre-prod rehearsal | Same as prod | Masked by default; role-based un-mask | Soft alerts to team |
| `prod` | Production | Per the pipeline contract | RBAC-controlled | Hard alerts to oncall |

Each environment is its own warehouse target (separate schema or separate
database; never sharing tables).

---

# 2. Isolation Boundaries

- A `dev` query MUST NOT read from a `prod` table directly (defer pattern
  is acceptable: `dev` reads `prod` artifacts but writes its own outputs)
- A `ci` schema is created at PR open + dropped at PR close/merge
- `staging` runs the same code as `prod`; differences are limited to
  schedule + compute size + alert destinations
- `prod` is the only environment that may serve external consumers
  (dashboards, services, exports)

---

# 3. Promotion Rules

Code moves: `dev` → PR → `ci` → merge → `staging` → manual approval →
`prod`.

Data does NOT move between environments directly:
- `staging` rebuilds from sources (or from prod artifacts via defer)
- `prod` rebuilds from sources
- One-off copies (snapshot prod → staging for debugging) go through the
  masking macro; an ADR documents the copy

---

# 4. PII Masking

`dev` and `ci` ALWAYS mask PII per `PII_HANDLING_CONTRACT.md`. No flag,
no override. The masking macro is unconditional in those env contexts.

`staging` masks by default; the un-mask role is granted on a per-analyst
basis with quarterly access review.

`prod` un-masks; access is RBAC-controlled and audited.

---

# 5. Schedule + Compute

- `dev`: on-demand only; no scheduled runs
- `ci`: triggered by VCS events; bounded compute (slim CI: state:modified+)
- `staging`: same cadence as prod, smaller warehouse size
- `prod`: scheduled per pipeline contract; alerts on failure / duration spike

Cost tracking is environment-aware: `prod` costs are budgeted; `dev` + `ci`
are bounded by per-developer quotas + per-PR limits.

---

# 6. Credentials + Secrets

- Never committed (`profiles.yml` with creds → `.gitignore`)
- Loaded from environment variables OR a secrets manager
- One credential per environment; service accounts in `staging` + `prod`
  (never personal credentials in non-dev)

The credential rotation policy lives elsewhere (the team's security
runbook). This file just declares the principle.

---

# 7. Failure Containment

A failure in a lower environment must NOT impact a higher one:
- A `dev` query running out of memory: blast radius is the dev's schema
- A `ci` test failure: blast radius is the PR; merge is blocked
- A `staging` run failure: alert to team; doesn't impact `prod`
- A `prod` run failure: alert to oncall; investigate before next run

Cross-environment dependencies (e.g., `staging` reading from `prod`
exposures) require explicit ADRs.
