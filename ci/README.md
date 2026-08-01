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
| `boundary-gate-python.yml` | `python-fastapi` | `python-fastapi` | — | — |
| `boundary-gate-node.yml` | `nodejs-fastify` | `nodejs-fastify` | — | — |
| `ui-quality-gate.yml` | — | — | ✓ | — |
| `ui-eval-gate.yml` (L4+) | — | — | ✓ | — |
| `l3-ui-nextjs-quality-gate.yml` | — | — | Next.js L3 | — |
| `ui-nextjs-quality-gate.yml` | — | — | Next.js L4/L5 | — |
| `ui-nextjs-eval-gate.yml` | — | — | Next.js L4/L5 | — |
| `l3-ui-nextjs-quality-gate.yml` | — | — | Next.js L3 | — |
| `ui-nextjs-quality-gate.yml` | — | — | Next.js L4/L5 | — |
| `ui-nextjs-eval-gate.yml` | — | — | Next.js L4/L5 | — |
| `data-common-gate.yml` | — | — | — | ✓ |
| `dbt-gate.yml` | — | — | — | `python-dbt` |
| `databricks-gate.yml` | — | — | — | `databricks-lakehouse` |

### Quick Checklist

- [ ] Copy `repo-scope-check.yml` and set `REPO_OWNER`
- [ ] Copy project-type workflow(s) from the table above
- [ ] Commit and push
- [ ] Verify `repo-scope-check` runs on next PR to `features/*/nfrs.md`
- [ ] Configure required secrets (see [Required Secrets](#required-secrets) below)

---

### Boundary enforcement is selected by stack

Boundary enforcement needs a tool that can read your language, so it is **not**
part of the shared quality gate. govkit installs a boundary gate chosen by
`--stack`:

| Stack | Gate file | Tool | Reference contract |
|---|---|---|---|
| `python-fastapi` | `boundary-gate-python.yml` | `import-linter` | `governance/backend/importlinter-reference.toml` |
| `nodejs-fastify` | `boundary-gate-node.yml` | `dependency-cruiser` | `governance/backend/dependency-cruiser-reference.cjs` |
| `go-gin`, `java-spring-boot`, `dotnet-aspnet` | *none yet* | tracked separately | — |

A stack with no gate receives **no boundary workflow at all**, rather than one
that silently skips. Shipping a Python linter to a Go repo enforces nothing
whether it fails or skips, and the architecture docs would still be promising
enforcement that does not exist.

Boundary enforcement ships from **L3** upward. L3 has no `features/` model, but
it does carry the architecture contracts, and this is what enforces them.

**Every boundary gate is opt-in.** govkit ships the reference contract as a
**template**; the gate skips until you copy it in, so a fresh install is green.
Each logs a notice telling you how to enable it.

- **Python** — copy `governance/backend/importlinter-reference.toml` into your
  `pyproject.toml` (or `.importlinter` / `setup.cfg` / `tox.ini`) and replace
  `myservice` with your package name.
- **Node** — copy `governance/backend/dependency-cruiser-reference.cjs` to
  `.dependency-cruiser.cjs`. No placeholders: the rules key on layer folder
  names, and they accept both `src/<layer>/` and `src/<package>/<layer>/`.

**Confirm your gate analysed something.** Both linters report success on an
empty analysis, so a misconfigured contract looks exactly like a clean repo:

- `import-linter` prints `Analyzed N files, 0 dependencies` and reports every
  contract KEPT when the package name is wrong.
- `dependency-cruiser` cruises `0 modules` and exits 0 when it cannot parse
  your sources — which is what happens on **TypeScript 7**, since
  dependency-cruiser 17 uses the TypeScript 5.x compiler API.

`boundary-gate-node.yml` fails the build on a zero module count rather than
trusting the exit code. If you adapt these gates, keep that check.

---

## Level 3 vs Level 4 CI

Levels are additive, and so are these files: an L4 install receives the L3
gate **and** the L4 gate. `quality-gate.yml` therefore contributes only what
`l3-quality-gate.yml` does not — boundary enforcement, SonarQube, Snyk and
commit format come from the L3 gate at every level. Defining them in both
files made L4+ repos run each twice on every push.

| Pipeline | Level 3 | Level 4 |
|----------|---------|---------|
| `l3-quality-gate.yml` | Governance artifacts (3), commit format, SonarQube, Snyk | — |
| `boundary-gate-python.yml` | Architecture boundary enforcement (`python-fastapi`) | — |
| `boundary-gate-node.yml` | Architecture boundary enforcement (`nodejs-fastify`) | — |
| `quality-gate.yml` | — | Schema validation, contract compatibility, governance artifacts (5) |
| `eval-gate.yml` | — | FIRST/Virtue prediction thresholds, LLM eval |
| `ui-quality-gate.yml` | — | Type check, ESLint, component tests, bundle size |
| `ui-eval-gate.yml` | — | FIRST/Virtue prediction, Playwright E2E, axe scans |
| `l3-ui-nextjs-quality-gate.yml` | Next.js typecheck, lint, tests, build, and API/database boundary | — |
| `ui-nextjs-quality-gate.yml` | — | Next.js typecheck, lint, tests, build, feature validation, and API/database boundary |
| `ui-nextjs-eval-gate.yml` | — | Next.js Playwright + axe, with opt-in stable screenshot comparisons |
| `data-common-gate.yml` | Static governance artifact, PII policy, and `govkit validate` checks | Static governance artifact, PII policy, and `govkit validate` checks |
| `dbt-gate.yml` | dbt dependency install, `dbt deps`, `dbt parse`, `dbt compile`, SQLFluff when configured, static model YAML checks | Same conservative checks; warehouse-backed test/source freshness execution remains opt-in |
| `databricks-gate.yml` | Databricks bundle/config static checks, optional `databricks bundle validate` when CLI auth exists, secret/path/PII scans, pytest when configured | Same conservative checks; deploys, jobs, pipelines, and warehouse-backed data-quality checks remain opt-in |

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
| Architecture boundaries | boundary-gate-python | Runs `import-linter` to enforce hexagonal layering (`python-fastapi` only) |
| Security vulnerabilities | l3-quality-gate | Snyk dependency scan |
| Code quality metrics | l3-quality-gate | SonarQube duplication and complexity |

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

## Databricks Gate

**File:** `databricks-gate.yml` (GitHub: `ci/github/databricks-gate.yml`, Azure: `ci/azure/databricks-gate.yml`)

**Purpose:** Runs conservative `databricks-lakehouse` stack checks:

- detect Databricks Asset Bundle files such as `databricks.yml`
- run `databricks bundle validate` only when the Databricks CLI and auth are configured
- scan Databricks configs, notebooks, pipelines, and source for hardcoded
  workspace URLs, tokens, secrets, and personal workspace paths
- warn on missing catalog/schema placeholders and PII metadata gaps
- run `pytest` for pure transformation modules when tests are configured

**Boundary:** This gate documents but does not enable `databricks bundle deploy
--target dev`, `databricks jobs run-now`, `databricks pipelines start-update`,
or Databricks SQL warehouse data-quality checks. Enable those only after CI has
a safe workspace identity, target catalog/schema, secret management, compute
policy, and cost controls.

---

## Pipeline Structure

### Backend

```
l3-quality-gate.yml       → commit format, SonarQube, Snyk
boundary-gate-python.yml  → import-linter boundaries (python-fastapi only)
quality-gate.yml          → schema validation, contract compatibility, artifacts
eval-gate.yml             → FIRST/Virtue prediction check, LLM eval suite
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
