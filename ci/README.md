# CI Pipelines — Enforcement Reference

This directory contains CI pipeline templates for both GitHub Actions and Azure DevOps. These are installed into target projects by `govkit apply`.

## Level 3 vs Level 4 CI

| Pipeline | Level 3 | Level 4 |
|----------|---------|---------|
| `l3-quality-gate.yml` | Governance artifacts (3), commit format, SonarQube, Snyk | — |
| `quality-gate.yml` | — | Schema validation, boundary enforcement, SonarQube, Snyk, contract compatibility, governance artifacts (5), commit format |
| `eval-gate.yml` | — | FIRST/Virtue prediction thresholds, LLM eval |
| `ui-quality-gate.yml` | — | Type check, ESLint, component tests, bundle size |
| `ui-eval-gate.yml` | — | FIRST/Virtue prediction, Playwright E2E, axe scans |

Level 3 projects receive only `l3-quality-gate.yml`. Level 4 projects receive the full set.

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
| LLM eval suite | eval-gate | Wire up your eval runner (e.g., LangSmith, custom script) |
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
