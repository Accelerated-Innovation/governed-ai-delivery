# Data Stack and Databricks Plan

> Produced 2026-06-06. This is the source of truth for the next data-stack
> implementation work. Each increment is intended to be independently
> reviewable and shippable.

---

## Context

GovKit now supports `--type data` for all production agents, with the existing
`python-dbt` stack governing dbt-layered projects. A client planning to use the
data stack runs on Databricks and also wants to use the public
`databricks/databricks-agent-skills` package.

The product boundary needs to stay crisp:

- GovKit is the repo-local governance layer: architecture contracts,
  acceptance criteria, NFRs, preflight, plans, test expectations, CI gates, and
  approval boundaries.
- Databricks agent skills are the platform usage layer: Databricks CLI,
  authentication, Asset Bundles, Jobs, Lakeflow Pipelines, Unity Catalog,
  model serving, vector search, and similar Databricks-specific workflows.

The current `python-dbt` stack remains useful for dbt projects, including dbt
projects that target Databricks. It should not become the generic Databricks
stack. Databricks-native delivery needs a separate stack overlay.

---

## Decisions

### D1 - Data supports L3 and L4 only

`--type data` does not support Level 5. Level 5 is GenAI Operations for LLM
application delivery: LLM gateway, guardrails, prompt/model evaluation,
observability, and multi-agent topology. Data projects have advanced concerns,
but they are data quality, lineage, warehouse/runtime, cost, and PII concerns,
not the L5 GenAI-Ops operating model.

Supported matrix:

| Type | L3 | L4 | L5 |
|------|----|----|----|
| `data` | yes | yes | no |

Future advanced data capabilities should ship as stack overlays or extensions,
not by stretching L5.

### D2 - Keep `python-dbt`

`python-dbt` remains the data stack for dbt projects:

- dbt Core or dbt-compatible workflows
- staging -> intermediate -> marts
- dbt tests and schema YAML
- source freshness and mart contracts
- dbt-on-Databricks where dbt remains the primary project shape

### D3 - Add `databricks-lakehouse`

Add a second data stack named `databricks-lakehouse`.

Rationale: "Lakehouse" is broad enough to cover the Databricks-native operating
model without overfitting to Lakeflow alone. The stack can cover Unity Catalog,
Delta tables, PySpark/SQL, Databricks Asset Bundles, Jobs, Lakeflow Pipelines,
notebooks, serverless compute, and data governance. Lakeflow should be an
important section inside the stack, not the stack name.

### D4 - Data CI should be conservative but not empty

Data installs should get a small, blocking common governance gate and
stack-specific static gates. Anything that needs warehouse/workspace
credentials, cloud compute, or meaningful cost is opt-in.

Default behavior:

- Blocking: local/static governance checks.
- Blocking: stack config validation that does not execute paid compute.
- Opt-in: dbt warehouse execution, Databricks job execution, source freshness,
  workspace deployment, or pipeline runs.

---

## Current Findings to Fix

These were found during the 0.12.0 data-stack review and should be addressed
before adding the Databricks stack.

| Finding | Impact | Target Increment |
|---------|--------|------------------|
| `--type data --level 5` is accepted and silently falls back to base data files while writing an L5 marker | Incoherent install | Increment 1 |
| Agent manifest stack choices omit `python-dbt` even though data defaults to it | `govkit list` and help are misleading | Increment 1 |
| `apply --stack` help says default is `python-fastapi`, ignoring data's default | Misleading UX | Increment 1 |
| Docs say data CI is intentionally empty, but installs include `repo-scope-check.yml` through base CI merge | Docs/behavior drift | Increment 2 |
| Data CI is type-aware but not stack-aware | Cannot automatically choose dbt vs Databricks gates | Increment 3 |

---

## Increment 1: Data Boundary and Discoverability Fixes

**Goal:** Make the current data stack behavior coherent before adding new
capability.

### Changes

- Reject `govkit apply --type data --level 5` with a clear error.
- Reject `govkit init --starter data --level 5` or normalize it only if a
  deliberate product decision is made; preferred behavior is reject.
- Add `python-dbt` to all production agent manifest stack choices:
  - `agents/claude-code/manifest.json`
  - `agents/copilot/manifest.json`
  - `agents/codex/manifest.json`
- Update `apply --stack` help text so it does not claim the universal default
  is `python-fastapi`.
- Update README and changelog language:
  - data supports L3/L4 only
  - L5 is GenAI-Ops for LLM application shapes
  - `python-dbt` is the default stack for `--type data`

### Tests

- Applying `--type data --level 5` fails for each production agent.
- `govkit list` includes `python-dbt` in stack choices.
- `govkit apply --detect --type data` still reports `python-dbt`.
- Existing stack-selection tests remain green.

### Verification

- `pytest tests/test_stack_select.py tests/test_govkit.py tests/test_main_dispatch.py`
- Full `pytest` before merge.

---

## Increment 2: Data CI Contract Clarification

**Goal:** Decide and encode the conservative CI model for data projects.

### Changes

- Replace "data CI intentionally empty" language with:
  - data gets a common governance gate
  - stack-specific execution gates are conservative and opt-in where cloud
    credentials or compute are required
- Decide whether `repo-scope-check.yml` remains part of all data installs.
  Recommended: yes, but document it as part of the common governance gate.
- Update manifests so data CI behavior is explicit, not an accidental result of
  base CI merging.
- Add tests asserting the resolved data CI governed files for all agents and
  levels L3/L4.

### Tests

- `resolve_variant_files(... type=data, ci=github, level=3/4)` returns the
  documented common data CI files.
- Same for Azure.
- No L5 data CI path is possible after Increment 1.

### Verification

- `pytest tests/test_govkit.py tests/test_schemas.py`

---

## Increment 3: Stack-Aware Data CI Selection

**Goal:** Let data installs select CI templates by both `type` and `stack`.

Today CI dispatch is `ci.<platform>.by_type.<type>`. That is enough for backend
vs UI vs data, but not enough for data stack variants.

### Changes

- Extend manifest resolution or install finalization to support stack-aware CI.
- Preferred shape:

```json
{
  "by_type": {
    "data": {
      "governed": ["ci/github/data-common-gate.yml"],
      "by_stack": {
        "python-dbt": {
          "governed": ["ci/github/dbt-gate.yml"]
        },
        "databricks-lakehouse": {
          "governed": ["ci/github/databricks-gate.yml"]
        }
      }
    }
  }
}
```

- Keep backward compatibility for manifests that do not declare `by_stack`.
- Thread the resolved stack id into variant resolution, or add a small
  post-resolution CI augmentation step after stack selection.

### Tests

- `type=data, stack=python-dbt` resolves common + dbt CI.
- `type=data, stack=databricks-lakehouse` resolves common + Databricks CI.
- Non-data types are unaffected.
- Unknown future stacks do not crash; they receive common data CI only unless
  explicitly mapped.

### Verification

- `pytest tests/test_govkit.py tests/test_schemas.py tests/test_stack_select.py`

---

## Increment 4: Data Common CI Gate

**Goal:** Add a conservative common governance gate for all data stacks.

### New files

- `ci/github/data-common-gate.yml`
- `ci/azure/data-common-gate.yml`

### Blocking checks

- Run `govkit validate --target .` for L4 data installs.
- Validate L4 feature artifact completeness.
- Fail on `TBD` in data NFRs.
- Require `acceptance.feature` scenarios for changed data features.
- Require `architecture_preflight.md` before `plan.md`.
- Run repository scope validation.
- Check that PII policy artifacts exist:
  - `docs/data/architecture/PII_HANDLING_CONTRACT.md`
  - stack-specific `docs/data/architecture/PII_HANDLING.md`
- Warn or fail when `architecture_preflight.md` says ADR required but no ADR is
  linked. Recommended first release: warning in docs, blocking once the ADR
  marker convention is standardized.

### Non-goals

- No warehouse queries.
- No Databricks workspace calls.
- No cloud credentials.
- No source freshness execution.

### Tests

- CI template files install for data projects through stack-aware CI.
- Static smoke test validates required commands/sections are present.

### Verification

- `pytest tests/test_govkit.py`
- Manual smoke apply for all three agents with `--type data --level 4`.

---

## Increment 5: Conservative `python-dbt` CI Gate

**Goal:** Add dbt-specific CI that is useful by default and does not surprise
users with warehouse spend.

### New files

- `ci/github/dbt-gate.yml`
- `ci/azure/dbt-gate.yml`

### Blocking checks when dbt is present

- Install dbt dependencies as documented by the target project.
- `dbt deps`
- `dbt parse`
- `dbt compile`
- SQLFluff lint for changed SQL models when SQLFluff config is present.
- YAML/static checks for:
  - model descriptions
  - column descriptions
  - primary key `unique` + `not_null`
  - PII `meta.contains_pii` and `pii_category`

### Opt-in checks

- `dbt test --select state:modified+`
- source freshness
- warehouse-backed model build or test execution

These require target profile/secrets and should be clearly marked as disabled
until the team configures them.

### Tests

- `python-dbt` data install includes common + dbt gates.
- Databricks stack install does not include `dbt-gate.yml` unless explicitly
  requested.

### Verification

- `pytest tests/test_govkit.py tests/test_fixtures.py`

---

## Increment 6: `databricks-lakehouse` Stack Overlay

**Goal:** Add a Databricks-native data stack without mutating the dbt stack.

### New directory

```text
cli/stacks/databricks-lakehouse/
|-- overlay.yaml
|-- TECH_STACK.md
|-- TESTING.md
|-- MODEL_LAYERING.md
|-- PIPELINE_CONTRACT.md
|-- PII_HANDLING.md
`-- LINEAGE_OBSERVABILITY.md
```

### Overlay scope

- Unity Catalog as governance boundary.
- Delta tables as the storage contract.
- Databricks Asset Bundles as deployment/config packaging.
- Jobs and Lakeflow Pipelines as orchestration surfaces.
- PySpark / SQL / notebooks as implementation surfaces, with preference for
  testable `.py` modules where possible.
- Environment separation: dev, ci, staging, prod workspaces/catalogs/schemas.
- PII tagging/masking expectations.
- Lineage through Unity Catalog and Databricks-native metadata where available.
- Cost and compute policy assumptions.

### Assumptions to surface

- Whether the repo uses Asset Bundles.
- Whether notebooks are source-controlled.
- Whether Unity Catalog is enabled.
- Whether CI can authenticate to a Databricks workspace.
- Whether pipeline/job execution is allowed in CI.

### Tests

- `govkit stack list` shows `databricks-lakehouse`.
- `govkit apply --type data --stack databricks-lakehouse` installs the overlay.
- Marker records stack id and assumptions.
- Doctor/calibrate recognize the Databricks stack.

### Verification

- `pytest tests/test_overlay.py tests/test_stack_select.py tests/test_fixtures.py`

---

## Increment 7: Conservative Databricks CI Gate

**Goal:** Add Databricks static/config CI without running paid workspace compute
by default.

### New files

- `ci/github/databricks-gate.yml`
- `ci/azure/databricks-gate.yml`

### Blocking checks

- Detect Databricks Asset Bundle files, for example `databricks.yml`.
- If a bundle exists and the CLI is configured, run:
  - `databricks bundle validate`
- Static checks for:
  - no hardcoded workspace URLs or tokens
  - no hardcoded personal paths
  - expected catalog/schema naming placeholders
  - no secrets in notebooks, job configs, or pipeline configs
  - PII tags or documented exceptions for sensitive columns
- Run Python unit tests for pure transformation modules when a test runner is
  configured.

### Opt-in checks

- `databricks bundle deploy --target dev`
- job dry-run or pipeline validation that needs workspace credentials
- actual Lakeflow/Jobs execution
- data-quality checks against a Databricks SQL warehouse

### Tests

- `databricks-lakehouse` install includes common + Databricks gates.
- `python-dbt` install does not include Databricks gate.
- Template text makes workspace execution opt-in.

### Verification

- `pytest tests/test_govkit.py`

---

## Increment 8: Databricks Agent Skills Integration Guidance

**Goal:** Document how GovKit and Databricks agent skills work together.

### Changes

- Add README section under data stacks:
  - GovKit governs repo delivery.
  - Databricks skills provide platform-specific assistant guidance.
  - Recommended install: `databricks aitools install`.
- Add stack doc guidance in `databricks-lakehouse/TECH_STACK.md`:
  - Agents should use Databricks skills for CLI/platform workflows.
  - GovKit contracts remain authoritative for acceptance criteria, boundaries,
    PII, lineage, CI, and approvals.
- Add agent instruction snippets if needed:
  - "When Databricks skills are installed, use them for Databricks-specific
    commands and patterns. Do not let them override GovKit governance
    contracts."

### Tests

- Documentation link/check tests if available.
- Fixture smoke confirms generated Databricks stack docs mention the integration
  but do not require the skills to be installed.

### Verification

- `pytest tests/test_fixtures.py`

---

## Increment 9: Data Stack Demo Fixtures

**Goal:** Provide confidence that the data stacks behave differently and
intentionally.

### New or updated fixtures

- dbt fixture:
  - `dbt_project.yml`
  - `models/staging`
  - `models/intermediate`
  - `models/marts`
- Databricks fixture:
  - `databricks.yml`
  - representative `src/` or `notebooks/`
  - `resources/jobs.yml` or pipeline config
  - no dbt project file unless testing mixed signals

### Tests

- Detection prefers `python-dbt` for dbt signals.
- Detection prefers `databricks-lakehouse` for Databricks-native signals once
  implemented.
- Explicit `--stack` wins over inference.
- `--type data` rejects incompatible backend stack inference.
- Mixed dbt + Databricks signals produce documented precedence or a warning.

### Verification

- `pytest tests/test_detect.py tests/test_stack_select.py tests/test_fixtures.py`

---

## Open Questions

1. Should `databricks-lakehouse` be inferred automatically from `databricks.yml`
   in the first release, or require explicit `--stack databricks-lakehouse`
   until real client feedback confirms detection signals?
2. Should repo-scope CI be considered part of the common data gate, or should
   it remain a separate optional template?
3. Should dbt-on-Databricks default to `python-dbt` whenever `dbt_project.yml`
   exists, even if `databricks.yml` also exists?
4. What is the minimum Databricks CLI version to document for bundle validation?
5. Should the Databricks stack assume Unity Catalog, or allow a documented
   non-UC transitional mode with stronger warnings?

---

## Recommended PR Sequence

| PR | Increment | Why this order |
|----|-----------|----------------|
| 1 | Data boundary and discoverability fixes | Removes known incoherence before adding new surface area |
| 2 | Data CI contract clarification | Aligns docs and manifests before adding templates |
| 3 | Stack-aware data CI selection | Enables clean stack-specific gates |
| 4 | Data common CI gate | Adds conservative protection for all data projects |
| 5 | Conservative `python-dbt` CI gate | Completes current stack before introducing another |
| 6 | `databricks-lakehouse` stack overlay | Adds Databricks-native guidance |
| 7 | Conservative Databricks CI gate | Adds stack-specific validation after the stack exists |
| 8 | Databricks skills integration guidance | Documents the operating model clearly |
| 9 | Data stack demo fixtures | Hardens detection and examples after both stacks exist |

---

## Definition of Done

- Data L5 is impossible to install accidentally.
- `govkit list` and CLI help accurately advertise data stack choices.
- Data CI behavior is explicit, conservative, and documented.
- `python-dbt` and `databricks-lakehouse` are distinct stack overlays with
  different docs, assumptions, and CI gates.
- Databricks workspace or warehouse execution is never run by default.
- Databricks agent skills are documented as complementary to, not replacing,
  GovKit governance.
- Full test suite passes.
