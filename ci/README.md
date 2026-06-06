# CI Pipelines — Enforcement Reference

This directory contains CI pipeline templates for both GitHub Actions and Azure DevOps. These are installed into target projects by `govkit apply`.

---

## Quick Start — First-Time CI Setup

Run this once after `govkit apply` to wire up CI in your project.

### 1. Enable Repository Scope Validation

Copy the template to your project's workflow directory:

- **GitHub:** `ci/github/repo-scope-check.yml` → `.github/workflows/repo-scope-check.yml`
- **Azure:** `ci/azure/repo-scope-check.yml` → your Azure Pipelines definition

Then set your repository name in the workflow file:

```yaml
REPO_OWNER: your-repo-name   # e.g. api-service, frontend-app, auth-service
```

Commit and push. The job runs automatically on every PR that modifies `features/*/nfrs.md`.

### 2. Enable Project-Type Workflows

Copy the relevant templates for your project type:

| Workflow | Backend | CLI | UI | Data |
|---|:---:|:---:|:---:|:---:|
| `quality-gate.yml` | ✓ | ✓ | optional | — |
| `eval-gate.yml` (L4+) | ✓ | ✓ | — | — |
| `l3-quality-gate.yml` (L3 only) | ✓ | ✓ | — | — |
| `ui-quality-gate.yml` | — | — | ✓ | — |
| `ui-eval-gate.yml` (L4+) | — | — | ✓ | — |
| `data-common-gate.yml` | — | — | — | ✓ |
| `dbt-gate.yml` | — | — | — | `python-dbt` |

### Quick Checklist

- [ ] Copy `repo-scope-check.yml` and set `REPO_OWNER`
- [ ] Copy project-type workflow(s) from the table above
- [ ] Commit and push
- [ ] Verify `repo-scope-check` runs on next PR to `features/*/nfrs.md`
- [ ] Configure required secrets (see [Required Secrets](#required-secrets) below)

---

## Level 3 vs Level 4 CI

| Pipeline | Level 3 | Level 4 |
|----------|---------|---------|
| `l3-quality-gate.yml` | Governance artifacts (3), commit format, SonarQube, Snyk | — |
| `quality-gate.yml` | — | Schema validation, boundary enforcement, SonarQube, Snyk, contract compatibility, governance artifacts (5), commit format |
| `eval-gate.yml` | — | FIRST/Virtue prediction thresholds, LLM eval |
| `ui-quality-gate.yml` | — | Type check, ESLint, component tests, bundle size |
| `ui-eval-gate.yml` | — | FIRST/Virtue prediction, Playwright E2E, axe scans |
| `data-common-gate.yml` | Static governance artifact, PII policy, and `govkit validate` checks | Static governance artifact, PII policy, and `govkit validate` checks |
| `dbt-gate.yml` | dbt dependency install, `dbt deps`, `dbt parse`, `dbt compile`, SQLFluff when configured, static model YAML checks | Same conservative checks; warehouse-backed test/source freshness execution remains opt-in |

Level 3 projects receive only `l3-quality-gate.yml`. Level 4 projects receive the full set. Level 5 projects receive L4 gates plus 3 additional GenAI gates.

### Level 5 CI Gates

| Pipeline | Purpose | Secrets Required |
|----------|---------|-----------------|
| `deepeval-gate.yml` | Runs DeepEval LLM quality tests for features with `deepeval_*` eval_class | `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` |
| `promptfoo-gate.yml` | Runs Promptfoo adversarial/regression suites for features with `promptfoo_*` eval_class | `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` |
| `guardrails-check.yml` | Validates NeMo Colang and Guardrails AI configurations (structural only) | None |

---

## What's Enforced vs What's Predicted

A critical distinction in this governance framework: some checks enforce **actual outcomes**, while others enforce **predicted scores** from `plan.md`. Teams should work toward closing this gap by wiring up actual test results.

### Enforced (actual outcomes verified)

| Check | Pipeline | What it does |
|---|---|---|
| Schema validation | quality-gate | Validates `eval_criteria.yaml` against JSON Schema |
| Architecture boundaries | quality-gate | Runs `import-linter` to enforce hexagonal layering |
| Security vulnerabilities | quality-gate | Snyk dependency scan |
| Code quality metrics | quality-gate | SonarQube duplication and complexity |

### Prediction-only (plan.md scores, not actuals)

| Check | Pipeline | What it does | How to close the gap |
|---|---|---|---|
| FIRST scores | eval-gate | Checks predicted averages >= 4.0 in `plan.md` | Add a post-test job that scores actual test suites against the [FIRST rubric](../docs/backend/evaluation/FIRST_SCORING_RUBRIC.md) |
| Virtue scores | eval-gate | Checks predicted averages >= 4.0 in `plan.md` | Add static analysis metrics (complexity, duplication, coverage) and compare to thresholds |
| Accessibility | ui-eval-gate | Checks predicted axe violations == 0 | Already partially enforced — Playwright axe scans run. Ensure `continue-on-error` is false. |

### Stubbed (require team configuration)

| Check | Pipeline | What to configure |
|---|---|---|
| Contract backward compatibility | quality-gate | Wire up a schema diff tool (e.g., `json-schema-diff-validator`) |
| LLM eval suite | eval-gate | Wire up your eval runner (e.g., DeepEval, Langfuse, custom script) |
| LLM regression check | eval-gate | Compare eval results against stored baselines |
| Bundle size budget | ui-quality-gate | Set a size threshold and change `continue-on-error` to `false` |

---

## Not Enforced by CI (agent-side governance only)

These governance rules are communicated to agents via CLAUDE.md / copilot-instructions but have no CI verification:

| Rule | Why no CI gate | Recommendation |
|---|---|---|
| Architecture preflight must exist before planning | No file existence check | Add a job that checks `features/*/architecture_preflight.md` exists for any feature with a `plan.md` |
| ADR required when preflight flags it | No ADR validation | Add a job that checks for ADR files when preflight contains "ADR required" |
| One increment per commit | No commit granularity check | Add commit message format validation (`feat(<scope>): increment N — ...`) |
| Gherkin scenarios must map to tests | No test coverage gate | Add a job that cross-references `@nfr-*` tags with test files |

---

## Repository Scope Validation

**File:** `repo-scope-check.yml` (GitHub: `ci/github/repo-scope-check.yml`, Azure: `ci/azure/repo-scope-check.yml`)

**Purpose:** Validates that features declaring cross-repository scope explicitly list this repository as owner. Prevents agents from implementing features in the wrong repository.

**When to use:** Every project should enable this check. It ensures team members don't accidentally write code that belongs in another repository.

**How to enable:**

1. Copy `ci/github/repo-scope-check.yml` to `.github/workflows/repo-scope-check.yml` (GitHub)
   OR add it to your Azure Pipelines definition
2. Set the `REPO_OWNER` variable to your repository's name
   - Examples: `auth-service`, `api-gateway`, `frontend-app`, `client-sdk`
3. Commit and push
4. The job runs on every PR that modifies `features/*/nfrs.md`

**What it checks:**

- ✅ "Repository Scope" section exists in `nfrs.md`
- ✅ Section has a checked box: `[x] This repository only` OR `[x] Multiple repositories`
- ✅ For multi-repo features: this repo is listed in the "Multi-Repository Details" table
- ❌ Fails if any feature is missing repo scope or doesn't list this repo as owner

**Typical failures and fixes:**

| Error | Fix |
|---|---|
| Missing "## Repository Scope" section | Add the section to the NFR template in progress |
| No checked box | Check either "This repository only" or "Multiple repositories" |
| "Multi-repo but does not list <repo> as owner" | Add your repo to the ownership table |

See: `docs/REPO_SCOPE_ANALYSIS_GUIDANCE.md` for complete repo scope semantics.

---

## Data Common Gate

**File:** `data-common-gate.yml` (GitHub: `ci/github/data-common-gate.yml`, Azure: `ci/azure/data-common-gate.yml`)

**Purpose:** Runs conservative static governance checks for data projects:

- `govkit validate --target .`
- `architecture_preflight.md` exists before `plan.md`
- non-starter features have `acceptance.feature` scenarios
- `features/*/nfrs.md` has no `TBD`
- PII policy artifacts exist:
  - `docs/data/architecture/PII_HANDLING_CONTRACT.md`
  - `docs/data/architecture/PII_HANDLING.md`

**Boundary:** This gate does not query warehouses, call Databricks workspaces,
deploy bundles, run jobs, execute pipelines, or require cloud credentials.
Those checks belong in opt-in stack-specific gates.

---

## dbt Gate

**File:** `dbt-gate.yml` (GitHub: `ci/github/dbt-gate.yml`, Azure: `ci/azure/dbt-gate.yml`)

**Purpose:** Runs conservative `python-dbt` stack checks:

- install dbt dependencies declared by the project
- `dbt deps`
- `dbt parse`
- `dbt compile`
- `sqlfluff lint` when SQLFluff is configured
- static model YAML checks for model descriptions, column descriptions,
  `unique` + `not_null` primary-key tests, and PII metadata

**Boundary:** This gate documents but does not enable `dbt test --select
state:modified+`, `dbt source freshness`, warehouse-backed model builds, or
warehouse-backed data-quality execution. Enable those only after CI profiles,
secrets, isolated schemas, and cost controls are configured.

---

## Pipeline Structure

### Backend

```
quality-gate.yml    → schema validation, boundaries, SonarQube, Snyk, contracts
eval-gate.yml       → FIRST/Virtue prediction check, LLM eval suite
```

### UI

```
ui-quality-gate.yml → schema validation, lint, type-check, accessibility, bundle size
ui-eval-gate.yml    → FIRST prediction check, accessibility prediction, E2E
```

---

## Required Secrets

| Secret | Used by | Required? |
|---|---|---|
| `SONAR_TOKEN` | quality-gate (SonarQube) | Only if using SonarQube |
| `SONAR_HOST_URL` | quality-gate (SonarQube) | Only if using SonarQube |
| `SNYK_TOKEN` | quality-gate (Snyk) | Only if using Snyk |
| `ANTHROPIC_API_KEY` | eval-gate (LLM eval) | Only if features use `mode: llm` |

If your team doesn't use SonarQube or Snyk, remove or skip those jobs rather than letting them fail.
