# Data Enforcement Hardening Plan

Close the gap between what govkit's `--type data` install *promises* (spec-first
delivery, modifiable architecture contracts, CI-checked evaluation criteria) and
what the code *delivers*. Source: the 2026-07-23 data-teams code review
(`govkit-data-teams-review.md`), "What I'd do, in priority order." Every finding
below was verified against the working tree; file/line anchors are from that
review.

Ordering principle: trust foundation first (edit-protection), then cheap
validation fixes, then the spec machinery, then net-new enforcement. Each
increment is independently committable, full suite green, ruff scoped to
changed files. Parity: any change to claude-code agent assets must land
identically for codex and copilot in the same increment (see `PARITY_TEST.md`).

## Motivation (evidence)

| Promise | Reality today | Anchor |
|---|---|---|
| "govkit never overwrites files you authored" | Edit-protection survives exactly one upgrade: `is_user_edited` compares mtime vs marker `applied_at`, and `cmd_upgrade` re-stamps `applied_at` after refusing — the *next* upgrade clobbers silently. Fresh git clones invert the failure (all mtimes newer than `applied_at` → mass false refusals → `--force` nukes real edits). | `cli/fs.py:25-51`, `cli/cmd_upgrade.py:147` |
| "The eval gate checks that every NFR category has at least one tagged scenario" (`l4-data.md`) | `known_categories` omits freshness/quality/pii/lineage/cost; the populated-section heuristic requires `- ` bullets while data NFRs use tables. Data NFR coverage is unvalidated. | `cli/validate.py:271-274, 261` |
| "Governed by evaluation criteria validated against a JSON Schema" | Data installs ship no schema (`variants.type.data.governed` = `docs/data/architecture/` only); the starter doesn't conform to the backend schema; `check_eval_criteria` invokes `check-jsonschema --check-metaschema` on the *instance* (wrong invocation). Nothing executes the criteria. | `agents/*/manifest.json`, `cli/validate.py:197-205` |
| Skills "do NOT assume hexagonal … whatever your layer mapping is" (`l4-data.md`) | L4 data installs get the backend skills, which hardcode `docs/backend/architecture/` and cite API/security docs a data install doesn't have. | `agents/*/manifest.json` data.level_4, `skills/backend/spec-planning/SKILL.md:17-20` |
| Databricks stack support | Overlay swaps 6 docs, but the layer rules stay dbt-worded (`{{ source() }}`, materializations, staging/marts globs) and are govkit-owned (overwritten on upgrade). | `cli/stacks/databricks-lakehouse/`, `agents/*/rules/data/` |
| — | Latent: `validate.STARTERS` omits `starter_data`; `cmd_init` ignores the marker's `options.type` and defaults the prompt to `backend` in data repos; the data starter's virtue vocabulary forked from the documented 7 Virtues. | `cli/validate.py:71-74`, `cli/cmd_init.py`, `features/starter_data/plan.md` |

---

## Phase A — Trust foundation

### Increment 1: Content-hash edit-protection (replaces mtime)

The one defect that can destroy a team's calibrated contracts. Fix before
anything else ships on top.

Target design: the `govkit:editable` header gains a `hash:` field — SHA-256 of
the doc **body** (content below the header), computed at install time. A doc is
user-edited iff its current body hash differs from the recorded hash.
Timestamps stop being an ownership signal entirely.

1. Failing tests first (`tests/test_fs.py`):
   - install → edit body → `is_user_edited` True; **stays True after a
     simulated second upgrade re-stamps `applied_at`** (the amnesia repro)
   - install → `touch` the file / copy to a new mtime without content change
     (the fresh-clone repro) → False
   - legacy file with header but no `hash:` field → fall back to today's
     mtime comparison (no behavior break for existing installs)
   - `--force` overwrite refreshes the recorded hash
2. `cli/headers.py`: `format_editable_header` accepts `body_hash`;
   `parse_editable_header` already returns arbitrary fields — no change.
   `prepend_header_to_file` computes the hash of the body it writes.
3. `cli/fs.py`: `is_user_edited` prefers hash comparison; mtime path survives
   only for headers lacking `hash:`.
4. Ride-along: `doctor` D006 gains nothing here, but confirm its baseline
   parsing tolerates the new field (it parses key:value generically).

Diff: headers.py, fs.py, test_fs.py, test_headers.py. CHANGELOG under
Unreleased ("edit-protection is now content-based; team edits survive
consecutive upgrades and fresh clones").

Non-goal: recording refused files in the marker. Hash comparison makes the
refusal state derivable from the file itself; no second bookkeeping surface.

---

## Phase B — Validation quick wins (all `cli/validate.py` + `cli/cmd_init.py`)

### Increment 2: Data NFR categories are validated

1. Failing tests: a data-shaped `nfrs.md` (table-style sections for
   `@nfr-freshness`, `@nfr-pii`, …) + an `acceptance.feature` missing
   `@nfr-freshness` → FAIL; with all tags present → PASS.
2. Add `freshness`, `quality`, `pii`, `lineage`, `cost` to
   `known_categories`. Normalize headings so `## @nfr-freshness` and
   `## Freshness` both map to `freshness`.
3. Make the populated-section heuristic recognize table rows (`| … |`) and
   checkbox lines, not just `- ` bullets.

Diff: validate.py, tests/test_validate.py.

### Increment 3: Starter + init hygiene

1. Add `starter_data` (and a guard test asserting `STARTERS` ⊇ every bundled
   `features/starter_*` dir name, so the *next* starter can't repeat this) to
   `cli/validate.py`.
2. `cmd_init`: read `options.type` from the marker and derive the starter
   default (`data` → `data`, `ui-*` → matching UI, else `backend`). Prompt
   text shows the detected default. Explicit `--starter` still wins.
3. Failing tests first for both: `govkit init` in a marker-typed data repo
   with no `--starter` and piped empty input → data starter scaffolded.

Diff: validate.py, cmd_init.py, tests. One increment — both are small and
share no risk.

### Increment 4: Honest schema validation plumbing

`check_eval_criteria` currently runs `check-jsonschema --check-metaschema`
against the instance file — it validates the YAML *as a schema*, which is
meaningless here for every project type, not just data.

1. Resolve the schema path from the install
   (`governance/*/schemas/eval_criteria.schema.json`); when present, run
   `check-jsonschema --schemafile <schema> <instance>`; when absent, WARN
   "no schema installed for this project type" (true for data until
   Increment 7).
2. Pin behavior with tests using a stub `check-jsonschema` on PATH (pass,
   fail, missing binary → WARN).

Diff: validate.py, tests/test_validate.py. This increment intentionally makes
the data gap *visible* (WARN) rather than silently green.

---

## Phase C — Spec machinery becomes type-aware

### Increment 5: Skills resolve the docs area from the install

The backend skills hardcode `docs/backend/…`. Rather than fork per-type
skills, template the area the same way rule globs are already templated at
install time (`rule_templating.py` precedent: agents can't resolve
skill_context at runtime, so resolve at install).

1. Add a `docs_area` fact to `skill_context.yaml` (`backend` | `ui` | `data`,
   derived from marker `options.type`).
2. SKILL.md sources gain `{{docs_area}}` tokens (`docs/{{docs_area}}/architecture/`);
   `post_install_finalize` expands tokens when copying skills — same pass,
   same degradation rule (unknown token → leave source text, doctor flags).
3. Guard test: after `apply --type data`, no installed skill file contains
   the literal string `docs/backend/`.
4. Parity: identical change in codex (`.agents/skills/`) and copilot
   (`.github/skills/`) sources.

Diff: skill_context.py, install_common.py (or a small skill_templating
helper), 3 agents × 4 skill sources, tests.

### Increment 6: Data-native preflight sections

Section vocabulary is still backend ("API Impact", "Security Impact") even
with correct paths. Give the preflight skill a per-area section block:

1. Data variant sections: Pipeline Impact (schedule/SLA/backfill), Contract
   Impact (mart schema changes vs the breaking-change table in `marts.md`),
   PII Impact, Lineage Impact. Backend/UI keep today's sections.
2. Source of truth for the sections is the skill source per area — accept the
   duplication across 3 agents (parity test pins it) rather than inventing a
   template engine.
3. Update `features/starter_data/architecture_preflight.md` so the worked
   example is exactly what the shipped skill now produces (it was
   hand-adapted; make that true by construction).

Diff: 3 agents × architecture-preflight + spec-planning SKILL.md, starter_data
preflight, PARITY_TEST.md additions.

---

## Phase D — Data evaluation criteria become enforceable

### Increment 7: A data eval-criteria schema that the starter passes

1. New `governance/data/schemas/eval_criteria.schema.json`: `version`
   (integer), `mode` (`deterministic` | `none` for data; no `llm`),
   `criteria[]` with `id`/`description`/`measurement`/`threshold`
   (string — data thresholds are query predicates, not 0–1 floats)/
   `severity` (`error`|`warn`). Deliberately *not* the backend criterion
   shape; data criteria are checked by queries and CI outcomes, not
   evaluator tools.
2. Fix `features/starter_data/eval_criteria.yaml` to conform (`version: 1`
   integer).
3. Manifests: data variant `governed` gains `governance/data/schemas/` (all
   3 agents). Increment 4's schema resolution then picks it up automatically
   — local validate goes from WARN to real instance validation.
4. Tests: starter validates against the new schema; backend starter still
   validates against the backend schema.

Diff: new schema, starter yaml, 3 manifests, tests/test_schemas.py.

### Increment 8: dbt-gate enforces the mart contract

The highest-leverage move in the whole plan: convert the docs teams edit into
checks the build runs.

1. `ci/github/dbt-gate.yml` (+ azure twin) static checks gain, blocking:
   - every model under `models/marts/` declares `contract: {enforced: true}`
     in its YAML (dbt-native column contract — the machine form of "marts
     are the public API")
   - every mart appears in at least one `exposures:` entry (operationalizes
     `marts.md`'s "no exposure = dead code or undocumented")
2. Opt-in (documented in the gate's trailer, same pattern as warehouse
   checks): `dbt-project-evaluator` for layer-boundary enforcement —
   machine-checks `BOUNDARIES.md` §1's allowed-reads table.
3. Update `cli/stacks/python-dbt/MODEL_LAYERING.md` + `TESTING.md` to
   document model contracts and versions as the mart change-control
   mechanism (deprecation via `deprecation_date`, breaking change via new
   model version + ADR). These are `editable: true` docs — bump overlay
   version (this *is* doc content, unlike the stack-metadata precedent).
4. Gate-behavior tests: extend the CI fixture approach used for the existing
   static checker (pure-python check script is already embedded — factor it
   into `scripts/` if embedding grows past ~150 lines, else keep inline).

Diff: 2 CI gate files ×2 platforms, 2 overlay docs, overlay.yaml version,
CHANGELOG.

Risk: teams on dbt-core < 1.5 lack model contracts. The check keys off
`dbt_project.yml` requiring `require-dbt-version: ">=1.5"` or the presence of
any `contract:` key; otherwise it downgrades to a warning with an upgrade
pointer. Conservative-gate philosophy preserved.

---

## Phase E — Rules follow the stack and the team

### Increment 9: Stack-overlaid data rules

1. Overlays gain an optional `rules:` list (schema change to
   `stack-overlay.schema.json`, same two-layer enforcement as the
   `supported_types` precedent in `STACK_METADATA_UNIFICATION_PLAN.md`).
2. `databricks-lakehouse` ships medallion-worded rule bodies
   (bronze/silver/gold vocabulary, Delta/PySpark idioms, globs
   `**/bronze/**` etc. templated via `layers.*` as today); `python-dbt`
   ships the current dbt rules unchanged.
3. Install path: when the active stack declares rules, they replace the
   type-default rule set for the overlapping filenames; `stack apply` swaps
   them (agent files are govkit-owned — unconditional refresh is correct
   here *because* Increment 10 removes team-tunable values from rule
   bodies).
4. Parity across 3 agents; D001 fixtures for a `src/bronze` repo.

Diff: schema, 2 overlay.yaml, new rule sources under
`cli/stacks/databricks-lakehouse/rules/` (or agent-variant subdirs — decide
in-increment against how manifests resolve rule sources today), install
plumbing, tests.

### Increment 10: Team-tunable values move out of rule bodies

1. Inventory the constants duplicated in `rules/data/*`: PII keyword list
   (`staging.md`), materialization defaults, naming patterns.
2. PII keywords → `skill_context.yaml` (`pii.keyword_list`, seeded from
   today's default); rules templated at install time with the list (same
   expansion pass as Increment 5); `dbt-gate`'s PII regex documented as
   generated from the same list (single source).
3. Materialization/naming stay in the **docs** (already editable) — rules
   drop the literal values and cite the doc, per the Authority pattern the
   rules already use.

Diff: rules sources ×3 agents, skill_context.py, dbt-gate PII section, tests.

---

## Phase F — Scoring honesty at data L4

### Increment 11: Decide and reconcile the prediction gate (ADR first)

Not a code-first increment — an ADR under `docs/data/architecture/ADR/`
choosing between:

- **(a)** drop the `evaluation_prediction` requirement for `--type data`
  (validate skips `check_plan_eval_prediction` when marker type is data;
  artifact completeness + Increments 7–8 carry enforcement), or
- **(b)** replace FIRST/Virtues with a data-native rubric (contract
  completeness, test-tier coverage, lineage coverage) with its own rubric
  doc.

Recommendation: (a) now, (b) only if a team asks for a scored gate — a
self-predicted ≥4.0 is ceremony either way, and (b) invents a rubric nobody
has calibrated. Whichever lands: fix the starter's virtue vocabulary drift
(`correctness/clarity/…` vs the documented `Working/Unique/Simple/…`) — under
(a) by deleting the block from `starter_data/plan.md`, under (b) by the new
rubric. Update `l4-data.md` ×3 agents to match.

Diff: ADR, validate.py (one level/type guard), starter_data/plan.md,
l4-data.md ×3, CHANGELOG.

---

## Sequencing and release shape

| Release | Increments | Theme |
|---|---|---|
| N | 1–4 | Trust + honest validation (no new features; safe patch/minor) |
| N+1 | 5–7 | Spec machinery works for data (minor) |
| N+2 | 8 | Mart contracts enforced in CI (minor; the headline) |
| N+3 | 9–11 | Databricks rules parity + tunables + scoring ADR |

Phases B and A are independent — B can land first if release pressure
demands, but nothing in C–E should ship before 1 (every later increment
rewrites installed files; doing that on top of mtime-based protection risks
the exact clobber the review flagged).

## Risks / non-goals

- **No new hard gates on existing installs without an escape hatch.**
  Increment 8's contract check warns (not fails) when the repo predates dbt
  1.5; Increment 2 can only fail features whose nfrs.md populates a category
  with no tag — which is the contract `l4-data.md` already claims.
- **Non-goal: executing data eval criteria in CI** (freshness queries,
  masked-value assertions). That requires warehouse credentials and stays
  behind the documented opt-in line. This plan makes the criteria
  *structurally valid and visible*, and moves the enforceable subset
  (contracts, exposures, boundaries) into static checks.
- **Non-goal: per-type skill forks.** Templating (Increments 5–6) keeps one
  skill source per agent; a `skills/data/` tree is fallback only if the
  section-block divergence outgrows templating.
- **Non-goal: touching L5 for data.** Data remains L3/L4 per the v0.13
  ruling; nothing here changes that boundary.
