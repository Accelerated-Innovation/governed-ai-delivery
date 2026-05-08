# Maturity Model Refactor: L3 = Foundations, L4 = Spec-Driven Add-On

**Status:** Plan only — no implementation yet.
**Author:** govkit refactor working group
**Created:** 2026-05-07
**Target version:** govkit v0.7.0 (current v0.6.0 per pyproject.toml)

---

## 1. Summary

Reframe the maturity ladder so each level commits the team to a different **way of working**, not just a different artifact count. The boundary between L3 and L4 moves to the most meaningful place: whether the team adopts a `features/` directory model and per-feature spec contracts.

| Level | Name | What it ships | What the team commits to |
|---|---|---|---|
| **L3** | Governed AI Delivery (Foundations) | Agent rules, architecture contracts under `docs/*/architecture/`, non-feature-coupled skills (`/adr-author`, optionally `/architecture-review`), lean CI gate (lint, tests, import-linter, optional sonar/snyk). **No `features/` directory, no per-feature artifacts.** | "Our AI agents follow our architecture contracts." Lowest-friction entry. |
| **L4** | Spec-Driven Add-On | Adds the `features/<name>/` 5-artifact contract (`acceptance.feature`, `nfrs.md`, `eval_criteria.yaml`, `plan.md`, `architecture_preflight.md`), the feature-coupled skills (`/spec-planning`, `/architecture-preflight`, `/implementation-plan`), test-first + spec-compliance rules, governance CI jobs (artifact check, eval schema, prediction thresholds), and `governance/<area>/templates/` + `governance/<area>/schemas/`. `govkit init` becomes meaningful here. | "We adopt spec-first, test-first feature delivery on top of L3." |
| **L5** | GenAI Operations | Unchanged content: LLM-specific NFR categories, `agent_topology.md` when multi-agent, deepeval/promptfoo/guardrails CI gates, LLM gateway/observability/multi-agent rules. | "Our LLM features are governed (routing, evaluation, safety)." Builds on L4. |

**Additive boundary:** L3 → L4 is genuinely additive (merge semantics). L5 currently retains the existing **replace** semantics for backward compatibility — its manifest blocks are full self-contained replacements, not merges over L4. Converting L5 to merge is deferred to v0.8.0; called out explicitly in §13. Within L3 → L4, the agent entry-point file (`CLAUDE.md` / `.github/copilot-instructions.md` / `AGENTS.md`) is the one path that intentionally collides on `dest` so the L4 entry overrides the L3 entry — see §4.3 for the collision rule.

### Why this design

The previous v0.6 model put L3, L4, and L5 on a single artifact-count axis (3 artifacts, 5 artifacts, 5 + LLM artifacts). That made the levels feel like "less or more of the same thing" and made the L4 add-on hard to name. Splitting on workflow commitment — *do you have a `features/` directory or not?* — gives each level a sharp, defensible identity:

- L3 is appealing for teams that want governed AI agents without restructuring their codebase.
- L4 is appealing for teams ready to commit to spec-first feature delivery and wire up evaluation prediction.
- L5 is appealing for teams shipping LLM-powered features that need governed routing, evaluation, and safety.

---

## 2. Current maturity model references

### 2.1 CLI code

- [cli/govkit.py:198](cli/govkit.py#L198) — `level_key = f"level_{level}" if level != "4" else None` (L4 is the "no override" default)
- [cli/govkit.py:224](cli/govkit.py#L224), [cli/govkit.py:347](cli/govkit.py#L347), [cli/govkit.py:391](cli/govkit.py#L391) — L4 default literals
- [cli/govkit.py:323-330](cli/govkit.py#L323-L330) — `_resolve_starter_dir` looks for `_l3` and `_l5` suffixes
- [cli/govkit.py:250-253](cli/govkit.py#L250-L253) — Apply unconditionally creates an empty `features/` dir (this becomes L4-only)
- [cli/govkit.py:336-339](cli/govkit.py#L336-L339) — `cmd_init` errors if `features/` is absent (this becomes L4-gated)
- [cli/govkit.py:361-367](cli/govkit.py#L361-L367) — Next-step messaging by level
- [cli/govkit.py:449,467,473](cli/govkit.py#L449) — argparse `choices=["3","4","5"]`
- [cli/validate.py:48-60](cli/validate.py#L48-L60) — `L3_REQUIRED_ARTIFACTS` (3 items), `L4_REQUIRED_ARTIFACTS` (5 items)
- [cli/validate.py:69-73](cli/validate.py#L69-L73) — `STARTERS` set
- [cli/validate.py:401-436](cli/validate.py#L401-L436) — `_build_checks` per-level routing
- [cli/validate.py:481](cli/validate.py#L481) — `level_labels`
- [cli/validate.py:462-465](cli/validate.py#L462-L465) — Hard errors when `features/` is missing (this becomes "no-op success" at L3)

### 2.2 Tests

- [tests/test_govkit.py:282-391](tests/test_govkit.py#L282-L391) — Variant resolution (`test_level_3_override`, `test_level_default_is_4`, etc.)
- [tests/test_govkit.py:445-522](tests/test_govkit.py#L445-L522) — `TestLevel5VariantResolution`
- [tests/test_govkit.py:563-657](tests/test_govkit.py#L563-L657) — `TestSmokeApply`, `TestSmokeInit` (asserts `features/` dir always created on apply)
- [tests/test_validate.py:465-636](tests/test_validate.py#L465-L636) — `TestL3Validation` assumes 3-artifact spec-driven model
- [tests/test_validate.py:769-894](tests/test_validate.py#L769-L894) — `TestL5Validation`
- [tests/test_validate.py:457-462](tests/test_validate.py#L457-L462) — `test_missing_features_dir_returns_one` (becomes "returns 0 at L3")

### 2.3 Schemas

- [governance/schemas/agent-manifest.schema.json:87-94](governance/schemas/agent-manifest.schema.json#L87-L94) — Defines `level_3` and `level_5` keys; sets `additionalProperties: false` but never lists `governed`. **Schema is already broken** — every live manifest uses `governed`. Fix is bundled with this refactor.

### 2.4 Manifests (3 agents, identical structure)

- [agents/claude-code/manifest.json](agents/claude-code/manifest.json), [agents/copilot/manifest.json](agents/copilot/manifest.json), [agents/codex/manifest.json](agents/codex/manifest.json)

Top-level `files`/`shared`/`governed` = current L4. `level_3` block = current L3 simpler set. `level_5` block = L5 GenAI ops.

### 2.5 Agent instruction files (markdown)

L3 simpler variants (current):
- `agents/<a>/<inst>/l3-backend-{api,cli}.md`, `l3-ui-{react,angular}.md`

L4 governed variants (current top-level):
- `agents/<a>/<inst>/backend-{api,cli}.md`, `ui-{react,angular}.md`

L5:
- `agents/<a>/<inst>/l5-backend-{api,cli}.md`

### 2.6 Skills

Architecture-aware (no `features/` references):
- `agents/<a>/skills/backend/adr-author/`, `skills/ui/adr-author/`

Feature-coupled (read or write `features/$ARGUMENTS/...`):
- `skills/backend/{spec-planning,architecture-preflight,implementation-plan,l3-spec-planning,l3-implementation-plan}/`
- `skills/ui/{spec-planning,architecture-preflight,implementation-plan,l3-spec-planning,l3-implementation-plan}/`

L5-only:
- `skills/backend/{genai-preflight,eval-suite-planning,multi-agent-design}/`

### 2.7 Generic rules

All three agents already ship full-parity generic rules (the kit's design invariant — no per-agent gaps in production content):

- claude-code: `agents/claude-code/rules/generic/{test-first.md,spec-compliance.md,repo-scope.md}`
- copilot: `agents/copilot/instructions/generic/{test-first.instructions.md,spec-compliance.instructions.md,repo-scope.instructions.md}`
- codex: `agents/codex/rules/generic/{test-first.md,spec-compliance.md,repo-scope.md}`

Manifest dispatch decides which level surfaces these rules; the files themselves exist for all three agents today.

### 2.8 Templates

- `governance/backend/templates/{plan.md,architecture_preflight.md,l3-plan.md,l5-plan.md,l5-architecture-preflight.md}`
- `governance/ui/templates/l3-plan.md`

### 2.9 Feature starters

- `features/{starter_backend,starter_cli,starter_ui}/` — 5 artifacts (current L4)
- `features/{starter_backend_l3,starter_cli_l3,starter_ui_l3}/` — 3 artifacts (current L3)
- `features/{starter_backend_l5,starter_cli_l5}/` — 5 artifacts + L5 extras

### 2.10 CI workflows

- `ci/{github,azure}/l3-quality-gate.yml` — current simpler gate; checks 3-artifact existence
- `ci/{github,azure}/quality-gate.yml` and friends — full L4 governance gate
- `ci/{github,azure}/{deepeval,promptfoo,guardrails,multi-agent}-*.yml` — L5

### 2.11 Documentation

- [README.md](README.md) lines 78,81,84,93,208,216-260,313-317,592,610,617,658-660,673-675
- [CHANGELOG.md](CHANGELOG.md), [PARITY_TEST.md](PARITY_TEST.md), [docs/backend/architecture/GHERKIN_TAGS.md](docs/backend/architecture/GHERKIN_TAGS.md), [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 3. Target mapping (per-level, concrete)

### 3.1 L3 — Governed AI Delivery (Foundations)

**Installed in target:**
- Agent entry-point file: `CLAUDE.md` / `.github/copilot-instructions.md` / `AGENTS.md` (NEW L3 content — see §5.1)
- Path-scoped agent rules (the rule files under `.claude/rules/`, `.github/instructions/`, or nested `AGENTS.md`)
- Architecture-aware skills only:
  - `/adr-author` (existing — no changes needed)
- Architecture contracts copied to target: full `docs/<area>/architecture/` tree
- CI: `ci/<provider>/l3-quality-gate.yml` (rewritten — see §3.4)

**NOT installed at L3:**
- `features/` directory (not even an empty one)
- `governance/<area>/templates/` (those describe per-feature artifact structure)
- `governance/<area>/schemas/` (validate per-feature artifacts)
- `governance/schemas/evaluation_prediction.schema.json`
- Feature-coupled skills (`/spec-planning`, `/architecture-preflight`, `/implementation-plan`)
- `test-first.md`, `spec-compliance.md` rules (these enforce a workflow that requires features/)

**`govkit` command behavior at L3:**
- `govkit apply --level 3` — installs the above; does NOT create `features/`
- `govkit init` — exits with: "Error: `govkit init` requires Level 4 or higher (spec-driven add-on). Run `govkit apply --level 4` to enable the features/ workflow."
- `govkit validate` — prints "Level 3 has no per-feature artifacts to validate. CI gate is the compliance surface." and returns 0.

### 3.2 L4 — Spec-Driven Add-On

**Adds on top of L3 (additive, via merge):**
- Replaces the agent entry-point file with the L4 version (more directives — feature lifecycle, evaluation prediction discipline, ADR rules)
- Feature-coupled skills:
  - `/spec-planning`, `/architecture-preflight`, `/implementation-plan`
- Workflow rules (already exist for all three agents — manifest moves them from "not referenced" to "referenced at L4"):
  - `test-first` rule
  - `spec-compliance` rule
- Templates: `governance/<area>/templates/{plan.md,architecture_preflight.md}`
- Schemas: `governance/<area>/schemas/`, `governance/schemas/evaluation_prediction.schema.json`
- CI: `ci/<provider>/quality-gate.yml` (full governance gate — replaces L3's lean gate at the workflow level)
- Feature starters: `features/starter_<type>/` bundled with govkit (used by `govkit init`, NOT copied during apply — same as today)

**`govkit` command behavior at L4:**
- `govkit apply --level 4` — installs L3 contents + L4 add-on; creates an empty `features/` dir as a placeholder
- `govkit init <feature> --starter <type>` — scaffolds `features/<feature>/` from `starter_<type>/`
- `govkit validate` — runs the full 5-artifact governance check on every directory under `features/`

### 3.3 L5 — GenAI Operations

**Adds on top of L4 (replace semantics — same as today):**
- L5 agent entry-point file (replaces L4's)
- L5 rules: `llm-gateway.md`, `guardrails.md`, `llm-evaluation.md`, `llm-observability.md`, `multi-agent.md`
- L5 skills: `/genai-preflight`, `/eval-suite-planning`, `/multi-agent-design`
- L5 starters: `features/starter_<type>_l5/`
- L5 templates: `l5-plan.md`, `l5-architecture-preflight.md`
- L5 CI: `deepeval-gate.yml`, `promptfoo-gate.yml`, `guardrails-check.yml`, `multi-agent-gate.yml`

**`govkit` command behavior at L5:** same as L4 plus the additional L5 jobs in CI; validate runs the L5 LLM-NFR / topology checks.

### 3.4 CI gate split

The current `ci/<provider>/l3-quality-gate.yml` checks 3-artifact existence — that has no meaning at new-L3. **Rewrite** the file rather than delete it.

**Critical: source files have different names but install at the same `dest` so L4 overrides L3 via merge-mode `dest` collision.**

- L3 source: `ci/github/l3-quality-gate.yml` → installs to `dest: .github/workflows/quality-gate.yml`
  - Lean gate: `commit-format`, `lint`, `tests`, `import-linter`, optional `sonarqube`, `security-scan`
- L4 source: `ci/github/quality-gate.yml` → installs to **the same `dest: .github/workflows/quality-gate.yml`**
  - Full governance gate: everything in L3 *plus* `governance-artifacts` (5 files per feature), `eval-criteria-schema`, `evaluation-prediction-thresholds`, `contract-compatibility`
  - Authored as a self-contained workflow (not "L3 + diff"), since it physically replaces the L3 workflow at the target.
- L5 source files (`deepeval-gate.yml` etc.) install at distinct `dest` paths (`.github/workflows/deepeval-gate.yml` etc.) — additive at the destination, no collision.

Same shape for Azure (`.azuredevops/pipelines/quality-gate.yml`).

The manifest's `level_4.files` (or `level_4.governed`) entry for the CI workflow uses the same `dest` as the L3 entry; merge-mode collision resolution (§4.3) ensures L4 wins.

---

## 4. Manifest semantics change

### 4.1 New rules

- L3 = top-level entries (no level key needed). **This is the new default.**
- `level_4` block applies **additively**: its `files`, `shared`, `governed` arrays are appended to the L3 base. When two `files` entries collide on `dest`, the L4 entry wins (this is how L4 replaces the L3 agent entry-point file `CLAUDE.md`).
- `level_5` block continues to **replace** the L4 base entirely (existing behavior).

### 4.2 CLI implementation (in `_select_variant` and `_collect_entries`)

Two-step rewrite:
1. `_select_variant` returns a tuple `(block: dict, mode: str)` where `mode ∈ {"base", "merge", "replace"}`. Today the function returns just `dict`, so this is a typed-return-shape change — every call site must update.
2. `_collect_entries` honors the mode: `base` and `merge` both append to the running collection; `replace` empties the per-call accumulator and re-fills.

Mode semantics:
- L3 (no level key) → mode = `"base"`.
- L4 `level_4` block → default `mode: "merge"`.
- L5 `level_5` block → default `mode: "replace"` (preserves today's behavior — no L5 manifest changes required).
- The `mode` field is optional in the schema; if absent, default = `"merge"` for `level_4`, `"replace"` for `level_5`.

### 4.3 Collision and dedup rules for merge mode

**This is a behavior change to the existing dedup logic.** Today, `_collect_entries` dedups `files` by `(src, dest)` tuple ([cli/govkit.py:168-171](cli/govkit.py#L168-L171)). Under merge mode, `files` must dedup by `dest` alone so L4 entries can override L3 entries at the same destination.

Audit step (Increment 2): grep all live manifests for any pair `{src1, dest}` + `{src2, dest}` — i.e. two distinct sources targeting the same destination. If any are found, both entries are kept today but only one would survive under the new logic. Verify intent and reconcile before merging Increment 2.

**`files` (per-`dest` collision):**
1. Add base entries to `all_files`, keyed by `dest`.
2. For each merge-mode override entry: if its `dest` matches an existing entry, **replace** that entry (later wins). Otherwise, **append**.
3. Existing `(src, dest)` dedup is replaced by `dest`-only dedup.

**`shared` (string array):**
- Append + dedup by string equality. No collision concept (paths are bare strings).
- A merge-mode override cannot remove a base `shared` entry. If that's needed in the future, add an explicit `removes` array — out of scope for v0.7.0.

**`governed` (string array):**
- Same as `shared`: append + dedup by string equality. No removal.

**Verification:** §8.1 tests #11–#12 cover `files`. Add tests for `shared` (`test_l4_merge_appends_shared`, `test_l4_merge_dedups_shared`) and `governed` (`test_l4_merge_appends_governed`, `test_l4_merge_dedups_governed`).

**`replace` mode (L5):** unchanged from today. The L5 block fully empties and refills `files`/`shared`/`governed` for that variant dimension.

### 4.4 `_resolve_starter_dir` simplification

After this refactor:
- L3: `_resolve_starter_dir` is never called (init is L4+ only).
- L4: returns `features/starter_<type>/`.
- L5: returns `features/starter_<type>_l5/` if it exists, else `features/starter_<type>/`.

The `_l3` lookup branch is deleted.

---

## 5. Authoring tasks (new content needed)

These are real authoring chunks, not mechanical edits. Call them out so the work is visible.

### 5.1 New L3 agent entry-point files (12 files total)

Per-agent × project type:
- `agents/claude-code/claude-md/{backend-api,backend-cli,ui-react,ui-angular}.md` — REWRITE as L3 foundations content
- `agents/copilot/copilot-instructions/{backend-api,backend-cli,ui-react,ui-angular}.md` — REWRITE
- `agents/codex/agents-md/{backend-api,backend-cli,ui-react,ui-angular}.md` — REWRITE

Content sketch (per file): a short directive doc that:
- Describes operating mode: read `docs/<area>/architecture/`, follow contracts as binding constraints.
- Lists the architecture documents to read on each turn.
- States when an ADR is required (`/adr-author` is the only governance skill at L3).
- Recommends test-first as a practice (not enforced — that's L4).
- Explicitly notes "feature artifacts are not part of L3; if your team adopts spec-driven delivery, run `govkit apply --level 4`."

The current top-level files (those that today represent L4 governed) are renamed to `l4-*.md` and stay as the L4 entry-point.

### 5.2 (Optional) `/architecture-review` skill at L3

A new architecture-aware skill that takes a code path or PR description (not a feature dir) and reviews against `docs/<area>/architecture/`. Useful for L3 teams that want agent-driven architecture review without committing to feature artifacts. **Defer to a follow-up release.** Not part of v0.7.0 scope.

### 5.3 Rewrite `ci/<provider>/l3-quality-gate.yml`

Replace the artifact-existence checks with a lean gate (commit-format, lint, tests, import-linter, optional sonar/snyk). Comment header explains "Level 3 (Foundations) — codebase-wide checks; no per-feature artifact validation."

### 5.4 (Optional) `/adr-author` parameter audit

Verify the existing `/adr-author` skill prompts make sense in a target without `features/`. Quick audit; likely no changes needed.

---

## 6. Impacted files

### 6.1 CLI (`cli/`)

- `cli/govkit.py`:
  - `level_key` default: L3 (no override key). L4 is the override.
  - `level` default flips `"4"` → `"3"` everywhere.
  - `_select_variant`: return-shape changes from `dict` to `(dict, mode)` tuple where `mode ∈ {"base","merge","replace"}`. Update all call sites.
  - `_collect_entries`: dedup `files` by `dest` only (not `(src, dest)` tuple). Append+dedup-by-string for `shared` and `governed`.
  - `cmd_apply`: don't auto-create `features/` at L3; still write `.govkit` marker at L3.
  - `cmd_init`: error out at L3 with message containing `govkit apply --level 4`; existing behavior at L4+.
  - `cmd_validate`: at L3, print no-op message and return 0.
  - `cmd_upgrade`: add `--migrate-levels` flag (interactive — see §7.2). Without `--migrate-levels`, `cmd_upgrade` keeps current behavior (refresh files at the existing level).
  - `_resolve_starter_dir`: drop `_l3` branch. If called with `level="3"`, raise `ValueError("L3 has no starter; init is L4+")`.
  - argparse `choices` unchanged (`["3","4","5"]`); help text updated. Add `--migrate-levels` to the `upgrade` subparser.
  - `read_govkit_marker`: print one-time migration warning when `version < "0.7.0"` (see §7.2 warning UX), unless env `GOVKIT_NO_MIGRATION_WARNING=1`.

- `cli/validate.py`:
  - `L3_REQUIRED_ARTIFACTS`: deleted (L3 has no artifacts).
  - `L4_REQUIRED_ARTIFACTS`: unchanged.
  - `_build_checks("3")`: returns `(artifacts=[], checks=[])`. The runner short-circuits at L3.
  - `_build_checks("4")`: same as today's L4 path.
  - `_build_checks("5")`: unchanged.
  - `STARTERS` set: drop `starter_*_l3` entries.
  - `level_labels`: `{"3": "L3 Governed AI Delivery (Foundations)", "4": "L4 Spec-Driven Add-On", "5": "L5 GenAI Operations"}`.
  - `run_validation`: at L3, return 0 immediately with informational output (no error if `features/` is absent).

### 6.2 Tests

- `tests/test_govkit.py`:
  - Rewrite `TestResolveVariantFiles::test_level_3_override` → `TestResolveVariantFiles::test_level_4_merge_override`
  - Flip `test_level_default_is_4` → `test_level_default_is_3`
  - Update `test_level_4_uses_default` → `test_level_3_uses_default`
  - Add `TestMergeMode` class: dest-collision resolution, dedup, file-vs-shared independence
  - Add regression `test_level_5_still_replaces`
  - `TestSmokeApply::test_features_dir_created_empty` → split: `test_l3_apply_does_not_create_features_dir` + `test_l4_apply_creates_empty_features_dir`
  - `TestSmokeInit` mostly unchanged (init is L4+ now, but the smoke setup already passes L4)

- `tests/test_validate.py`:
  - Delete `TestL3Validation` (no per-feature L3 validation)
  - Add `TestL3ValidationNoArtifacts`: validate with `level="3"` returns 0 even with no `features/`; with `level="3"` and a `features/` dir present, returns 0 with informational message
  - `TestRunValidation::test_missing_features_dir_returns_one` → behavior depends on level: at L3 returns 0, at L4+ returns 1
  - `test_skips_l3_starters` → delete (`_l3` starters no longer exist)

- New `tests/test_maturity_model.py` (TDD entry point — see §8.1)

- New `tests/test_schemas.py` — runs `check-jsonschema` against every `agents/*/manifest.json`

### 6.3 Schemas

- [governance/schemas/agent-manifest.schema.json](governance/schemas/agent-manifest.schema.json):
  - Replace `level_3` property with `level_4`.
  - Add optional `mode: "merge" | "replace"` to `level_override`.
  - Add `governed` array property to both `variant_config` and `level_override` (fixes existing schema drift).
  - `level_5` retains its current shape.

- `governance/backend/schemas/eval_criteria.schema.json`, `governance/schemas/evaluation_prediction.schema.json`: unchanged (level-agnostic; just live at L4 now).

### 6.4 Manifests (3 agents)

All three [agents/<a>/manifest.json](agents/claude-code/manifest.json) files:
- `options.level.prompt`: `"Maturity level? (3=Governed AI Delivery (Foundations), 4=Spec-Driven Add-On, 5=GenAI Operations)"`
- `options.level.default`: `"3"`
- Top-level `files`/`shared`/`governed` per variant: pared down to L3 foundations content (architecture docs, agent rules, `/adr-author`, lean CI workflow, NEW L3 entry-point file).
- New `level_4` block per variant with `mode: "merge"` containing the L4 add-on entries (feature-coupled skills, test-first/spec-compliance rules, governance templates/schemas, full CI workflow, L4 entry-point file at colliding `dest` to override).
- Existing `level_3` block deleted (its content is no longer relevant — the simpler 3-artifact model is gone).
- `level_5` block retained; behavior unchanged.

### 6.5 Agent instruction files

Operations are split across Increments 5, 6, and 8 to keep each commit's manifest references consistent with on-disk files:

- **Increment 5 (rename + author new — non-deleting):**
  - RENAME: `agents/<a>/<inst>/{backend-api,backend-cli,ui-react,ui-angular}.md` → `agents/<a>/<inst>/l4-{...}.md` (current L4 governed content is preserved at the new path)
  - AUTHOR NEW: `agents/<a>/<inst>/{backend-api,backend-cli,ui-react,ui-angular}.md` (L3 foundations — see §5.1). These now occupy the previous top-level filenames.
- **Increment 6 (manifest update):** manifests start referencing the new L3 top-level files and the renamed `l4-*.md` files.
- **Increment 8 (delete obsolete):**
  - DELETE: `agents/<a>/<inst>/l3-backend-{api,cli}.md`, `l3-ui-{react,angular}.md` (current simpler 3-artifact spec-driven content is no longer used and no manifest references it after Increment 6)
- **Unchanged:** `agents/<a>/<inst>/l5-backend-{api,cli}.md`

Rationale: deleting the `l3-*.md` files in Increment 5 would break any test or smoke run between Increments 5 and 6 because the live manifests still reference them. Deletes therefore happen in Increment 8, after Increment 6 cuts the references.

### 6.6 Skills

- `agents/<a>/skills/backend/{l3-spec-planning,l3-implementation-plan}/` — DELETE
- `agents/<a>/skills/ui/{l3-spec-planning,l3-implementation-plan}/` — DELETE
- All other skill directories — unchanged content; only manifest references move them between L3 (architecture-aware) and L4 (feature-coupled) buckets.

### 6.7 Generic rules

Already exist with full parity across all three agents (see §2.7). Unchanged content; manifest dispatch moves them from "not referenced at the simpler L3" to "referenced at L4 add-on" — for every agent in lockstep.

**Parity invariant:** any change to a generic rule for one agent must be mirrored to the other two as part of the same PR. No agent-specific gaps.

### 6.8 Templates

- `governance/backend/templates/l3-plan.md` → DELETE (no L3 plan template — L3 has no plan.md artifact)
- `governance/ui/templates/l3-plan.md` → DELETE
- `governance/backend/templates/{plan.md,architecture_preflight.md,l5-plan.md,l5-architecture-preflight.md}` — unchanged

### 6.9 Feature starters

- `features/{starter_backend_l3,starter_cli_l3,starter_ui_l3}/` → DELETE
- `features/{starter_backend,starter_cli,starter_ui}/` → unchanged (used by `govkit init` at L4+)
- `features/{starter_backend_l5,starter_cli_l5}/` → unchanged

### 6.10 CI workflows

- `ci/<provider>/l3-quality-gate.yml` → REWRITE (lean gate — see §5.3)
- All other CI files — unchanged content; manifest dispatch routes them to the correct level

### 6.11 Documentation

- [README.md](README.md) — substantive rewrite of Maturity Levels section + propagated wording (lines 78,81,84,93,208,216-260,313-317,673-675)
- [CHANGELOG.md](CHANGELOG.md) — append v0.7.0 entry calling out the breaking change for adopters
- [PARITY_TEST.md](PARITY_TEST.md), [docs/backend/architecture/GHERKIN_TAGS.md](docs/backend/architecture/GHERKIN_TAGS.md), [CONTRIBUTING.md](CONTRIBUTING.md) — mechanical wording updates
- [plans/IMPROVEMENT_PLAN.md](plans/IMPROVEMENT_PLAN.md), [plans/L5_IMPLEMENTATION_PLAN.md](plans/L5_IMPLEMENTATION_PLAN.md) — top-of-file forward note pointing here
- [pyproject.toml](pyproject.toml) — version bump 0.6.0 → 0.7.0

---

## 7. Schema migration

### 7.1 `agent-manifest.schema.json`

Three changes (see §6.3):
1. `level_3` → `level_4` property name.
2. Optional `mode` on `level_override`.
3. Add `governed` to `variant_config` and `level_override` (fixes existing drift).

Bundled with Increment 1 so the rest of the work happens against a valid schema.

### 7.2 `.govkit` marker migration

**A v0.6 L3 user must do real work to migrate.** This is the largest adopter-impact issue in the refactor and warrants the most careful UX.

**The asymmetry:** v0.6 `level: "3"` projects have 3-artifact features (the old simple model). The closest semantic match in v0.7 is **L4** (which has the `features/` directory model). But L4 requires *5* artifacts per feature — meaning every existing feature directory needs `eval_criteria.yaml` and `architecture_preflight.md` authored before validation passes. That's not a marker rewrite; it's a workflow change.

**State matrix:**

| Stored `level` (v0.6) | Project shape | Closest v0.7 match | What the user must do |
|---|---|---|---|
| `"3"` | `features/` with 3-artifact dirs | **L4** | Choose: (a) author the two missing artifacts per feature (or accept stub generation), (b) abandon the features and adopt new-L3 (no `features/`), or (c) abort and pin govkit to v0.6.x. |
| `"4"` | `features/` with 5-artifact dirs | **L4** | None — project shape is correct. Marker `version` rewritten; `level` unchanged. |
| `"5"` | `features/` with 5-artifact dirs + L5 extras | **L5** | None. Marker `version` rewritten; `level` unchanged. |

**`cmd_upgrade --migrate-levels` interactive flow:**

```
$ govkit upgrade --migrate-levels

  Detected .govkit marker: version=0.6.0  level=3
  Project has 4 feature director(ies) under features/, each with 3 artifacts.

  Under govkit v0.7.0, your project's shape (features/ + 3-artifact dirs) maps
  to Level 4 (Spec-Driven Add-On). L4 requires 5 artifacts per feature.

  How would you like to migrate?
    [1] Migrate to L4 — generate stub eval_criteria.yaml and
        architecture_preflight.md in each feature dir (you fill them in later).
        Marker becomes level=4, version=0.7.0.
    [2] Migrate to L4 — do NOT generate stubs. You will author the two new
        artifacts per feature manually. Validation will fail until you do.
        Marker becomes level=4, version=0.7.0.
    [3] Adopt new-L3 (Foundations) — you confirm we should DELETE features/
        and switch to architecture-only governance.
        Marker becomes level=3, version=0.7.0.
    [4] Abort — make no changes. Pin govkit==0.6.0 in your project.

  Choice [1-4]:
```

For `level: "4"` and `level: "5"` cases, no interactive prompt is needed:
```
$ govkit upgrade --migrate-levels

  Detected .govkit marker: version=0.6.0  level=4
  Your project shape is correct under v0.7.0; the level label flips from
  "Governed AI Delivery" to "Spec-Driven Add-On" but no data migration is needed.

  Marker rewritten: version=0.7.0  level=4
```

**Stub generation (option 1) details:**
- `eval_criteria.yaml` stub: header comment ("Auto-generated by govkit migrate; complete before validation"), `version: "1"`, `mode: TBD`, empty `criteria: []`. Fails validation (which is the point — forces the team to fill it in).
- `architecture_preflight.md` stub: header comment, sections 1–9 from `governance/<area>/templates/architecture_preflight.md` populated with `TBD` placeholders.

**Warning UX (when `--migrate-levels` has not yet been run):**
- `read_govkit_marker` prints to stderr exactly **once per `govkit` invocation** when `version < "0.7.0"`. No de-duplication across invocations (each fresh process warns).
- Suppressible via env var `GOVKIT_NO_MIGRATION_WARNING=1` for CI / scripted contexts.
- Auto-suppressed once `cmd_upgrade --migrate-levels` writes a marker with `version: "0.7.0"`.
- Warning text: `"warning: .govkit marker version 0.6.x detected. The L3/L4 maturity model changed in 0.7.0. Run 'govkit upgrade --migrate-levels' to migrate. (Set GOVKIT_NO_MIGRATION_WARNING=1 to suppress.)"`

The migration is **soft** at the warning layer (commands still run) but the user must explicitly choose a path before validation will pass under L4.

---

## 8. Test strategy (test-first)

### 8.1 New file `tests/test_maturity_model.py` — failing tests written first (Increment 0)

These should all FAIL before any production change:

1. `test_l3_label_is_governed_ai_delivery_foundations` — `level_labels["3"]` matches.
2. `test_l4_label_is_spec_driven_addon` — `level_labels["4"]` matches.
3. `test_l5_label_unchanged` — regression guard.
4. `test_default_level_is_3` — argparse default + marker fallback.
5. `test_l3_apply_does_not_create_features_dir` — after `govkit apply --level 3 /tmp/X`, `/tmp/X/features` does NOT exist.
6. `test_l4_apply_creates_empty_features_dir` — after `govkit apply --level 4 /tmp/X`, `/tmp/X/features` exists and is empty.
7. `test_l3_init_errors_helpfully` — `govkit init feat --level 3` exits non-zero with a message containing "Level 4".
8. `test_l3_validate_returns_zero_with_no_features` — `run_validation(target, level="3")` returns 0 even if `features/` is absent.
9. `test_l3_validate_returns_zero_with_features_present` — at L3, even a `features/` dir with broken artifacts returns 0 (L3 doesn't validate features).
10. `test_l4_validate_runs_full_governed_checks` — `run_validation(target, level="4")` over a 5-artifact feature returns 0; with one missing artifact returns 1.
11. `test_manifest_l4_merge_appends_files` — manifest with base `files=[A]` and `level_4: {mode: "merge", files: [B]}` resolves to `[A, B]` at level 4.
12. `test_manifest_l4_merge_dest_collision_later_wins` — base `files=[{src:"a.md", dest:"X"}]` and `level_4: {files:[{src:"b.md", dest:"X"}]}` resolves to a single entry with `src="b.md"` at level 4.
13. `test_manifest_l3_no_override_uses_top_level` — manifest with no `level_3` key resolves at level 3 to top-level entries.
14. `test_manifest_l5_still_replaces` — regression guard.
15. `test_starter_resolution_l3_not_called` — `_resolve_starter_dir` is not invoked from `cmd_init` at L3 (covered by test 7).

### 8.2 Tests to update or replace

(See §6.2 for the full list.)

### 8.3 New tests written during implementation

- `tests/test_govkit.py::TestMergeMode` — formal coverage of merge semantics.
- `tests/test_validate.py::TestL3Validation` rewrite — only the no-op success cases.
- `tests/test_govkit.py::TestUpgradeMigrate` — covers `cmd_upgrade --migrate-levels` for each `(stored_level, stored_version)` combination.
- `tests/test_schemas.py` — `check-jsonschema` over each agent manifest.

### 8.4 Smoke tests

After Increment 6 (last manifest update), run the full matrix:

```
for agent in claude-code copilot codex; do
  for level in 3 4 5; do
    for type in api cli; do
      for ui in none react angular; do
        target=/tmp/govkit-smoke/$agent/l$level/$type-$ui
        rm -rf $target && mkdir -p $target
        govkit apply --agent $agent --level $level --type $type --ui $ui \
                     --ci github --target $target
        govkit validate --target $target
      done
    done
  done
done
```

That's 3 agents × 3 levels × 2 types × 3 UIs = **54 combinations**. Verify per cell:
- L3 cells: no `features/` dir present; `govkit validate` returns 0 with no-op message; agent entry-point file (`CLAUDE.md` / `.github/copilot-instructions.md` / `AGENTS.md`) is the L3 foundations content (grep for "feature artifacts are not part of L3" anchor string from §5.1).
- L4 cells: empty `features/` dir present; agent entry-point file is L4 governed content; `governance/<area>/templates/{plan.md,architecture_preflight.md}` present; `.github/workflows/quality-gate.yml` (or Azure equivalent) is the full governance gate (grep for `governance-artifacts` job).
- L5 cells: agent entry-point file is L5 content; `deepeval-gate.yml` etc. present.

Then for one L4 cell:
```
govkit init demo --target /tmp/govkit-smoke/claude-code/l4/api-none --starter backend
govkit validate --target /tmp/govkit-smoke/claude-code/l4/api-none
# Should fail (stub feature has TBD entries). After authoring, should pass.
```

Smoke also for upgrade migration (Increment 9):
```
# Synthesize a v0.6 L3 project
mkdir -p /tmp/legacy-l3/features/demo
echo '{"version":"0.6.0","level":"3","agent":"claude-code","options":{"type":"api","ui":"none","ci":"github"}}' > /tmp/legacy-l3/.govkit
# (...populate 3-artifact feature dir...)
GOVKIT_NO_MIGRATION_WARNING=0 govkit upgrade --migrate-levels --target /tmp/legacy-l3
# Verify interactive prompt appears with 4 options; choose 1; verify stubs created and marker rewritten.
```

---

## 9. Documentation update strategy

Order:
1. README.md — rewrite Maturity Levels section first (canonical statement). Propagate to surrounding sections.
2. CHANGELOG.md — v0.7.0 entry: breaking change call-out, migration instructions, schema fix, additive merge semantics.
3. PARITY_TEST.md, GHERKIN_TAGS.md, CONTRIBUTING.md — mechanical wording updates.
4. NEW L3 agent entry-point files (the §5.1 authoring task).
5. Top-of-file forward notes in `plans/IMPROVEMENT_PLAN.md` and `plans/L5_IMPLEMENTATION_PLAN.md`.
6. pyproject.toml version bump.

---

## 10. Workflow / CI impact

- `ci/<provider>/l3-quality-gate.yml` — REWRITE as the lean L3 gate (§3.4, §5.4).
- `ci/<provider>/quality-gate.yml` (current top-level governance gate) — unchanged; manifest dispatches it at L4+.
- L5 CI files unchanged.
- This repo's own CI: audit for `_l3` or `level_3` references (currently only in tests, which we're rewriting). Add a CI step that runs `tests/test_schemas.py` (the new schema validator).

---

## 11. Incremental implementation steps

Each increment ends with `pytest tests/` green and a smoke run of `govkit apply` at one level.

| # | Increment | Risk | Verification |
|---|---|---|---|
| 0 | **Add failing tests** in `tests/test_maturity_model.py` (§8.1). | none | `pytest tests/test_maturity_model.py` — all RED; existing tests still GREEN. |
| 1 | **Schema fix** — add `governed` to `agent-manifest.schema.json`, introduce `level_4` and `mode`, keep `level_3` temporarily for back-compat. Add `tests/test_schemas.py`. | low | Schema test green; live manifests still validate. |
| 2 | **CLI semantics — merge mode** — `_select_variant` + `_collect_entries` honor merge with `dest`-collision resolution. Test `TestMergeMode` passes. Production manifests not touched yet. | medium | New unit tests pass; existing variant-resolution tests still pass. |
| 3 | **CLI semantics — defaults flip** — flip `level_key` default from `"4"` to `"3"`; flip default level constants in `cmd_apply`/`cmd_init`/`cmd_upgrade`/`run_validation`. Update `cmd_init` next-step messaging. Make `cmd_apply` skip auto-creating `features/` at L3. Make `cmd_init` error at L3. Make `run_validation` no-op at L3. Update `_resolve_starter_dir`. | medium | Increment-0 CLI tests now pass; existing tests rewritten where needed. |
| 4 | **validate.py update** — delete `L3_REQUIRED_ARTIFACTS`; rewrite `_build_checks`; update `level_labels`; update `STARTERS`. | medium | `pytest tests/test_validate.py` passes. |
| 5 | **Author L3 foundation instructions** (§5.1) — write 12 NEW agent entry-point files. Rename current top-level governed instructions → `l4-*.md`. **Do not delete `l3-*.md` files yet** — that happens in Increment 8 to keep manifest references valid through Increments 6–7. | high | Concrete checklist (all must pass): (a) every new L3 file references `docs/<area>/architecture/`; (b) no new L3 file references `features/$ARGUMENTS` or `features/<feature>/`; (c) every new L3 file mentions when an ADR is required; (d) every new L3 file points to `govkit apply --level 4` for spec-driven adoption; (e) line-count parity across the 12 files (within ±20%); (f) anchor string "feature artifacts are not part of L3" appears in every new L3 file (used by smoke tests in §8.4). Add a unit test `test_l3_instructions_anchor_strings` that greps for these. |
| 6 | **Update all three manifests in lockstep** — flip default level, delete `level_3` block, add `level_4: {mode: "merge", ...}` block, point top-level entries at L3 foundations content. **Single PR covers claude-code, copilot, codex** to preserve agent parity. | medium | `govkit apply --agent <a> --level <3,4,5> --target /tmp/X` for `<a> ∈ {claude-code, copilot, codex}` produces expected trees; smoke `govkit validate` passes at each level. |
| 7 | **Rewrite l3-quality-gate.yml** for both providers (§5.3). | low | Smoke apply at L3 produces a working CI workflow. |
| 8 | **Delete obsolete files** — `features/starter_*_l3/`, `governance/backend/templates/l3-plan.md`, `governance/ui/templates/l3-plan.md`, `agents/<a>/skills/<area>/l3-*` skill dirs (delete for all three agents in the same PR). | low | `pytest`; smoke. |
| 9 | **Marker migration shim** — `read_govkit_marker` warns on `version<"0.7.0"`; `cmd_upgrade --migrate-levels`. New tests in `TestUpgradeMigrate`. | medium | Migration tests pass; manual trial on a synthetic v0.6 marker. |
| 10 | **Documentation** — README.md (Maturity Levels rewrite + propagation), CHANGELOG.md (v0.7.0 entry), PARITY_TEST.md, GHERKIN_TAGS.md, CONTRIBUTING.md, plan-file forwards. Version bump pyproject.toml. | low | Manual review; repo-wide grep for stale wording. |
| 11 | **Schema cleanup** — remove transitional `level_3` key from schema. | low | Schema test still green. |
| 12 | **Final pass** — concrete grep query (run from repo root): `rg -nE 'level_3\|starter_.*_l3\|"3"\s*:\s*"L3 Spec-Driven"\|"4"\s*:\s*"L4 Governed AI Delivery"\|3=Spec-Driven\|4=Governed AI Delivery' --glob '!CHANGELOG.md' --glob '!plans/IMPROVEMENT_PLAN.md' --glob '!plans/L5_IMPLEMENTATION_PLAN.md' --glob '!plans/MATURITY_MODEL_L3_L4_SWAP_PLAN.md'`. Anything that returns is a finding. | low | Grep returns zero hits (or only intentional historical mentions in excluded files). |

Each increment = one PR or one commit on the refactor branch.

---

## 12. Risks and review checkpoints

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **L3 foundations content is harder to author than expected.** New top-level instructions need to clearly describe a "no features/" mode without confusing adopters. | Medium | Medium | Increment 5 is its own PR; reviewer focus on whether the L3 directives are coherent without referencing per-feature artifacts. |
| **Adopter `.govkit` markers with `level: "3"` (v0.6.x)** silently flip meaning. | High | Medium | Increment 12 migration shim + clear CHANGELOG note + soft warning on every command. Don't release v0.7.0 without the migration story. |
| **Merge-mode `dest` collision resolution** introduces subtle bugs (e.g. wrong order, double-add). | Medium | Medium | Increment 2 lands the change behind tests; `TestMergeMode` covers the happy path and edge cases (collision, no-collision append, dedup). Regression guard `test_level_5_still_replaces`. |
| **L3 quality-gate rewrite** breaks adopters who relied on the L3 artifact-existence check. | Low | Low | The L3 artifact check no longer makes sense (no artifacts at L3). Adopters who want artifact validation should be at L4. CHANGELOG explicitly calls this out. |
| **`govkit init` at L3** error message could confuse new users. | Low | Low | Error message includes the exact command to upgrade: `govkit apply --level 4`. Smoke-test message wording. |
| **README drift** — many lines reference the current model. Easy to miss one. | Medium | Low | Increment 15 final grep pass. |
| **The `governed` schema fix** changes the surface that other tools (e.g. `check-jsonschema` in CI) validate against. | Low | Low | Increment 1 isolates the fix; pre-existing manifests must still validate after the change. |
| **Skill `dest` collision in real manifests** (e.g., L4 adds `/spec-planning` to `.claude/skills/spec-planning/` while L3 had something else there). | Low | Low | The L3 set deliberately ships only `/adr-author`. There are no current collisions. Tests `test_manifest_l4_merge_dest_collision_later_wins` lock in the override behavior for `CLAUDE.md`. |
| **Authoring L3 instructions per-agent inconsistently** — three agents could drift in voice/content. | Medium | Medium | **Agent parity is a hard invariant of this kit** — no claude-code-only rules or skills. Author all three L3 entry-point files in the same PR (Increment 5), with shared content scaffolding ported across `agents/{claude-code,copilot,codex}/<inst-dir>/`. Reviewer rejects any per-agent drift. |

### Review checkpoints

- **After Increment 0:** confirm failing tests describe the *target* behavior, not just the inverse of current.
- **After Increment 4:** validate.py + govkit.py pair behaves coherently (no-op at L3, full check at L4).
- **After Increment 5:** L3 foundation instructions read as a complete operating directive without referencing per-feature artifacts; all three agents have parity in their L3 entry-point files.
- **After Increment 6:** all three agents apply cleanly at all three levels in smoke targets; manifest changes shipped together preserve parity.
- **After Increment 10:** README.md reads top-to-bottom without contradicting the new model; CHANGELOG flags the breaking change.
- **Before tagging v0.7.0:** repo-wide grep, marker migration story confirmed, manual smoke on three agents × three levels × three project types (api/cli, none/react/angular).

---

## 13. Release strategy

### 13.1 Release sequence

This is a breaking semantic change. Adopters discovering it via `pip install --upgrade` would be a poor experience. Mitigations:

1. **Pre-announcement.** Open a tracking issue on the repo at the start of Increment 5 ("Authoring L3 foundations"). Pin it. Link from README during the rc window.
2. **Release candidate.** Tag `v0.7.0-rc1` after Increment 12 passes. Announce via the tracking issue. Hold for 2 weeks for adopter feedback.
3. **Final tag.** v0.7.0 after rc feedback is incorporated.
4. **Backports.** v0.6.x receives bug-fix-only backports through the v0.8.0 release (provides ~6 months of overlap based on current cadence). State this explicitly in the v0.7.0 CHANGELOG.
5. **Pin recommendation.** During the rc window, README front-matter includes: `pip install govkit==0.6.* # pin until you're ready to migrate to 0.7`.

### 13.2 Out of scope

- Adding `/architecture-review` skill at L3 (§5.2) — defer to a follow-up release.
- Renaming `govkit` CLI commands or flag names (other than adding `--migrate-levels`).
- Adding new artifacts at L4 or L5.
- Changing L5 content or behavior. Converting L5 to merge semantics is deferred to v0.8.0.
- Refactoring the `.govkit` marker JSON shape (only the `level` field's *meaning* changes; `version` field is already present).
- Re-architecting the manifest variant system beyond adding the `mode` field and merge semantics. Adding a `removes` array for explicit entry removal is deferred.
- Changing the apply/upgrade copy semantics for `governed` or `shared` paths.
- Adding `govkit apply --dry-run` (would mitigate adopter risk, but out of scope for this refactor; tracked separately).

---

## 14. Definition of done

- [ ] L3 is described everywhere as "Governed AI Delivery (Foundations)"; no `features/` directory is created at L3 by `govkit apply`.
- [ ] L4 is described everywhere as "Spec-Driven Add-On"; `govkit apply --level 4` produces an empty `features/` dir + the full 5-artifact contract surface.
- [ ] L5 is described everywhere as "GenAI Operations"; behavior unchanged.
- [ ] `govkit init` at L3 errors with a helpful message pointing to L4.
- [ ] `govkit validate` at L3 returns 0 with an informational message.
- [ ] All `level_3` manifest blocks are removed; all manifests have a `level_4: {mode: "merge", ...}` block.
- [ ] `cli/govkit.py` defaults to L3 throughout.
- [ ] `cli/validate.py` no-ops at L3 and runs the 5-artifact governed check at L4.
- [ ] `tests/test_govkit.py`, `tests/test_validate.py`, and new `tests/test_maturity_model.py` and `tests/test_schemas.py` lock in the new model.
- [ ] No `features/starter_*_l3/` directories remain.
- [ ] No `governance/<area>/templates/l3-plan.md` files remain.
- [ ] `ci/<provider>/l3-quality-gate.yml` is the new lean gate (no per-feature artifact check).
- [ ] `governance/schemas/agent-manifest.schema.json` validates every live manifest and includes `governed`.
- [ ] CHANGELOG.md has a v0.7.0 entry with migration instructions.
- [ ] README.md, CONTRIBUTING.md, PARITY_TEST.md, GHERKIN_TAGS.md align with the new model.
- [ ] `pyproject.toml` version bumped 0.6.0 → 0.7.0.
- [ ] `pytest tests/` is green.
- [ ] Smoke: `govkit apply --agent <a> --level <l> --target /tmp/X` for `<a> ∈ {claude-code, copilot, codex}` × `<l> ∈ {3, 4, 5}` × `<type> ∈ {api, cli}` × `<ui> ∈ {none, react, angular}` produces correct trees.
- [ ] `govkit upgrade --migrate-levels` matches the §7.2 state matrix for all `(stored_level, stored_version)` combinations, with explicit `TestUpgradeMigrate` coverage for each cell.
- [ ] Migration warning fires once per invocation when `version<"0.7.0"`, suppressed by `GOVKIT_NO_MIGRATION_WARNING=1`, auto-cleared after `--migrate-levels` rewrites the marker.
- [ ] L4 stub generation (option 1 in §7.2) produces `eval_criteria.yaml` and `architecture_preflight.md` files that are syntactically valid but fail validation (TBD placeholders). `TestUpgradeMigrate::test_stub_generation_fails_validation` locks this in.
- [ ] v0.7.0-rc1 tagged before v0.7.0 final (per §13.1).

---

## Appendix A — Worked manifest example

This is what one variant entry (`claude-code` × `type: api`) looks like before and after the refactor. The full manifests have additional dimensions (`ui`, `ci`); those follow the same pattern.

### Before (v0.6 — current, abridged)

```jsonc
{
  "agent": "claude-code",
  "options": {
    "level": {
      "prompt": "Maturity level? (3=Spec-Driven, 4=Governed AI Delivery, 5=GenAI Operations)",
      "choices": ["3", "4", "5"],
      "default": "4"
    },
    // ...
  },
  "variants": {
    "type": {
      "api": {
        // Top-level = current L4 governed (default)
        "files": [
          { "src": "claude-md/backend-api.md", "dest": "CLAUDE.md" },
          { "src": "rules/backend/api.md", "dest": ".claude/rules/api.md" },
          { "src": "rules/backend/services.md", "dest": ".claude/rules/services.md" },
          { "src": "rules/backend/ports.md", "dest": ".claude/rules/ports.md" },
          { "src": "rules/backend/adapters.md", "dest": ".claude/rules/adapters.md" },
          { "src": "rules/backend/security.md", "dest": ".claude/rules/security.md" },
          { "src": "skills/backend/spec-planning/", "dest": ".claude/skills/spec-planning/" },
          { "src": "skills/backend/architecture-preflight/", "dest": ".claude/skills/architecture-preflight/" },
          { "src": "skills/backend/implementation-plan/", "dest": ".claude/skills/implementation-plan/" },
          { "src": "skills/backend/adr-author/", "dest": ".claude/skills/adr-author/" }
        ],
        "shared": ["features/starter_backend/", "features/schema_contract_example/"],
        "governed": ["docs/backend/", "governance/backend/"],

        // Override block: simpler L3 spec-driven set
        "level_3": {
          "files": [
            { "src": "claude-md/l3-backend-api.md", "dest": "CLAUDE.md" },
            { "src": "rules/generic/test-first.md", "dest": ".claude/rules/test-first.md" },
            { "src": "rules/generic/spec-compliance.md", "dest": ".claude/rules/spec-compliance.md" },
            { "src": "skills/backend/l3-spec-planning/", "dest": ".claude/skills/spec-planning/" },
            { "src": "skills/backend/l3-implementation-plan/", "dest": ".claude/skills/implementation-plan/" }
          ],
          "shared": ["features/starter_backend_l3/"],
          "governed": [
            "docs/backend/architecture/DESIGN_PRINCIPLES.md",
            "docs/backend/architecture/TESTING.md",
            "docs/backend/architecture/GHERKIN_CONVENTIONS.md",
            "docs/backend/architecture/GHERKIN_TAGS.md",
            "governance/backend/templates/l3-plan.md"
          ]
        },

        // Override block: L5 GenAI ops (replace semantics)
        "level_5": {
          "files": [ /* L5-specific entries */ ],
          "shared": ["features/starter_backend_l5/", "features/schema_contract_example/"],
          "governed": [ /* L5 docs and schemas */ ]
        }
      }
    }
  }
}
```

### After (v0.7 — proposed, abridged)

```jsonc
{
  "agent": "claude-code",
  "options": {
    "level": {
      "prompt": "Maturity level? (3=Governed AI Delivery (Foundations), 4=Spec-Driven Add-On, 5=GenAI Operations)",
      "choices": ["3", "4", "5"],
      "default": "3"
    },
    // ...
  },
  "variants": {
    "type": {
      "api": {
        // Top-level = NEW L3 foundations (architecture-aware, no features/)
        "files": [
          { "src": "claude-md/backend-api.md", "dest": "CLAUDE.md" },                              // NEW L3 content
          { "src": "rules/backend/api.md", "dest": ".claude/rules/api.md" },
          { "src": "rules/backend/services.md", "dest": ".claude/rules/services.md" },
          { "src": "rules/backend/ports.md", "dest": ".claude/rules/ports.md" },
          { "src": "rules/backend/adapters.md", "dest": ".claude/rules/adapters.md" },
          { "src": "rules/backend/security.md", "dest": ".claude/rules/security.md" },
          { "src": "rules/generic/repo-scope.md", "dest": ".claude/rules/repo-scope.md" },
          { "src": "skills/backend/adr-author/", "dest": ".claude/skills/adr-author/" }              // architecture-aware skill only
        ],
        "shared": [],                                                                                // L3 ships no feature starters
        "governed": [
          "docs/backend/architecture/",                                                              // architecture contracts
          "ci/github/l3-quality-gate.yml"                                                            // installs to .github/workflows/quality-gate.yml
        ],

        // Spec-Driven Add-On (additive merge over L3 base)
        "level_4": {
          "mode": "merge",
          "files": [
            { "src": "claude-md/l4-backend-api.md", "dest": "CLAUDE.md" },                           // collides with L3 dest; merge-mode → L4 wins
            { "src": "skills/backend/spec-planning/", "dest": ".claude/skills/spec-planning/" },
            { "src": "skills/backend/architecture-preflight/", "dest": ".claude/skills/architecture-preflight/" },
            { "src": "skills/backend/implementation-plan/", "dest": ".claude/skills/implementation-plan/" },
            { "src": "rules/generic/test-first.md", "dest": ".claude/rules/test-first.md" },
            { "src": "rules/generic/spec-compliance.md", "dest": ".claude/rules/spec-compliance.md" }
          ],
          "shared": ["features/starter_backend/", "features/schema_contract_example/"],
          "governed": [
            "docs/backend/evaluation/",
            "docs/backend/contracts/",
            "governance/backend/",
            "governance/schemas/evaluation_prediction.schema.json",
            "ci/github/quality-gate.yml"                                                             // SAME dest as L3 gate; merge-mode → L4 wins
          ]
        },

        // L5 unchanged — replace semantics preserved
        "level_5": {
          "mode": "replace",
          "files": [ /* L5-specific entries (full self-contained set, as today) */ ],
          "shared": ["features/starter_backend_l5/", "features/schema_contract_example/"],
          "governed": [ /* L5 docs and schemas */ ]
        }
      }
    }
  }
}
```

### Key observations

1. **`level_3` block is gone.** L3 is the default (top-level entries).
2. **`level_4` block is new.** Its `mode: "merge"` makes its arrays additive over L3's.
3. **`CLAUDE.md` `dest` collision is intentional.** Both L3 and L4 ship a file with `dest: "CLAUDE.md"` — merge-mode collision resolution (L4 later wins, §4.3) is what swaps the agent's operating-mode directives when the user upgrades.
4. **`quality-gate.yml` `dest` collision is intentional.** L3's lean gate and L4's full gate both install to `.github/workflows/quality-gate.yml`. Same merge-mode resolution (§3.4).
5. **L5 entries are unchanged.** No content edits; the `mode: "replace"` field is added explicitly for clarity but defaults to replace anyway when present on a `level_5` block.
6. **`shared` and `governed` arrays grow at L4** by appending the new L4-only paths to whatever L3 already lists. No removals.

The same diff pattern applies to:
- `agents/copilot/manifest.json` × all variant cells (with `.instructions.md` extensions and `.github/instructions/` paths).
- `agents/codex/manifest.json` × all variant cells (with `AGENTS.md` files at nested directory paths).
- `type: cli` and the three `ui` cells per agent.

---

## Appendix B — Draft CHANGELOG.md v0.7.0 entry

This is the user-facing migration document. To be appended to `CHANGELOG.md` in Increment 10.

```markdown
## [0.7.0] — 2026-MM-DD

### Breaking changes — maturity model reframed

The meaning of Level 3 and Level 4 has changed. **If your project's `.govkit` marker says
`level: "3"` or `level: "4"`, please read this section before upgrading.**

| Level | v0.6.x | v0.7.0 |
|---|---|---|
| **L3** | Spec-Driven Development (3 artifacts per feature) | **Governed AI Delivery (Foundations)** — agent rules + architecture docs only; no `features/` directory |
| **L4** | Governed AI Delivery (5 artifacts per feature) | **Spec-Driven Add-On** — adds `features/` and the 5-artifact contract on top of L3 |
| **L5** | GenAI Operations | GenAI Operations *(unchanged)* |

The new model is additive (L4 ⊃ L3) and splits at a clearer boundary: whether your project
adopts a `features/` directory model.

### What this means for adopters

After upgrading, govkit prints a one-time migration warning per invocation until you run
`govkit upgrade --migrate-levels`. Suppress with `GOVKIT_NO_MIGRATION_WARNING=1` if needed.

**If your marker says `level: "3"`** (3-artifact features under v0.6.x):

Your project's shape (a `features/` directory with 3-artifact dirs) maps most closely to the
new **L4**, but L4 requires 5 artifacts per feature. Run `govkit upgrade --migrate-levels`
for an interactive prompt with four options:

1. Migrate to L4 with stub generation — govkit creates `eval_criteria.yaml` and
   `architecture_preflight.md` stubs in each feature dir; you fill them in over time.
2. Migrate to L4 without stubs — you author the two new artifacts manually.
3. Adopt new-L3 (Foundations) — you confirm we should delete your `features/` directory
   and switch to architecture-only governance (no per-feature artifacts).
4. Abort — pin `govkit==0.6.*` in your project until you're ready.

**If your marker says `level: "4"`** (5-artifact features under v0.6.x):

No data migration needed. Your project shape is correct under v0.7.0; only the level label
flips. Run `govkit upgrade --migrate-levels` to clear the migration warning.

**If your marker says `level: "5"`:**

Nothing changes for you. Run `govkit upgrade --migrate-levels` to clear the migration warning.

### Other changes

- **CLI:** `govkit upgrade --migrate-levels` (new flag) — interactive marker migration.
- **CLI:** `govkit init` errors at L3 with a message pointing to `govkit apply --level 4`.
- **CLI:** `govkit validate` is a no-op at L3 (returns 0 with informational message).
- **CLI:** `govkit apply --level 3` no longer creates an empty `features/` directory in the target.
- **Manifest schema:** `level_3` key removed; `level_4` key added with optional `mode: "merge" | "replace"`. The `governed` key is now formally allowed (previously the schema rejected it despite all live manifests using it — a long-standing schema bug, fixed here).
- **CI:** `l3-quality-gate.yml` rewritten as a lean codebase-wide gate (no per-feature artifact checks). The full governance gate continues to ship at L4.
- **Test-first and spec-compliance rules** (`test-first.md`, `spec-compliance.md`) move from L3 to L4. They are still part of the kit; they are now part of the spec-driven add-on.

### Support and pinning

- v0.6.x will receive bug-fix-only backports through the v0.8.0 release.
- During the v0.7.0-rc1 window, pin with `pip install govkit==0.6.*` if you want to defer the migration.

### Migration commands

\`\`\`bash
pip install --upgrade govkit
govkit upgrade --migrate-levels --target /path/to/your/project
\`\`\`
```


