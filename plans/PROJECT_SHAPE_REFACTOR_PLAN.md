# Project Shape Refactor: One Install = One Project Shape

**Status:** Plan only — no implementation yet.
**Author:** govkit refactor working group
**Created:** 2026-05-17
**Target version:** govkit v0.8.0 (current v0.7.0 per pyproject.toml)
**Predecessor:** [MATURITY_MODEL_L3_L4_SWAP_PLAN.md](MATURITY_MODEL_L3_L4_SWAP_PLAN.md) (v0.7.0)

---

## 1. Summary

Replace the orthogonal `--type {api,cli}` + `--ui {none,react,angular}` cross-product with a flat `--type {api,cli,ui-react,ui-angular}` enumeration. One `govkit apply` configures one project shape. The `--ui` dimension is removed entirely; the dead `CLAUDE-UI.md` / `copilot-instructions-ui.md` sidecar files are deleted along with it.

Concurrently, bring all skills into compliance with the **Open Skills** standard (canonical `SKILL.md` frontmatter: `name`, `description`; no `$ARGUMENTS` substitution; body operates on natural-language args derived from context) so every skill works identically across all three agents.

Adopt **progressive loading** as the default placement strategy for shape-scoped guidance — each agent's native mechanism:
- **Codex** — nested `AGENTS.md` (already correct)
- **Copilot** — `.github/instructions/*.instructions.md` with `applyTo:` globs (already correct)
- **Claude Code** — nested `CLAUDE.md` (e.g. `src/CLAUDE.md` for UI shapes); the existing `.claude/rules/*.md` pattern is reused only for shapes that don't have a clean subtree split.

| Shape | `--type` | Root agent file | Auto-loaded by? |
|---|---|---|---|
| Backend HTTP API | `api` | `CLAUDE.md` / `AGENTS.md` / `.github/copilot-instructions.md` | All three |
| Backend CLI | `cli` | same as above | All three |
| **React SPA** | `ui-react` | same as above (canonical path, not `-UI` sidecar) | All three |
| **Angular SPA** | `ui-angular` | same as above | All three |

Fullstack-in-one-repo is **not a top-level shape**. Teams that want it run `govkit apply` per subdirectory of a monorepo (e.g. `apps/api/`, `apps/web/`). Codex's hierarchical loader, Claude's recursive `CLAUDE.md` discovery, and Copilot's `applyTo` globs all support subpath governance natively — no install-time support required.

### Why this design

The current 0.7.0 cross-product makes three project shapes look like four configurations:

- `--type api --ui none` (backend API)
- `--type cli --ui none` (backend CLI)
- `--type api --ui react` (claims to be fullstack, but the UI guidance lands in `CLAUDE-UI.md` / `copilot-instructions-ui.md` files that neither agent auto-loads — UI guidance is functionally dead for two of the three agents)
- `--type api --ui none` for a UI-only project (no escape — backend rules are forced)

Enterprise reality is that UI and backend ship in separate repos. The current schema doesn't support that case at all (no UI-only install path), and it half-supports fullstack (Codex works; Claude and Copilot have dead sidecars). Collapsing to a flat enumeration solves both problems and removes the dead-code class entirely.

---

## 2. Current state references

### 2.1 CLI code

- [cli/govkit.py:802-809](cli/govkit.py#L802-L809) — argparse `--type` choices `["api", "cli"]`, `--ui` choices `["none", "react", "angular"]`, `--ci` choices `["github", "azure"]`
- [cli/govkit.py:191-212](cli/govkit.py#L191-L212) — `resolve_options` iterates manifest's `options` spec; works generically across dimensions
- [cli/govkit.py:215-238](cli/govkit.py#L215-L238) — `_select_variant` reads `variants[dimension][value]`; level-aware override lookup (`level_4`/`level_5`)
- [cli/govkit.py:285-317](cli/govkit.py#L285-L317) — `_collect_entries` dedups files by `(src, dest)` tuple — preserves cross-dimension dest collisions (Copilot pattern)
- [cli/govkit.py:469-484](cli/govkit.py#L469-L484) — `_resolve_starter_dir` keys on `starter_type ∈ {backend, cli, ui}` and `level`
- [cli/govkit.py:456-466](cli/govkit.py#L456-L466) — `_prompt_starter_type` choices `["backend", "cli", "ui"]`
- [cli/govkit.py:818-820](cli/govkit.py#L818-L820) — init subparser `--starter` choices `["backend", "cli", "ui"]`

### 2.2 Manifests (3 agents)

All three manifests follow the same shape:

- [agents/claude-code/manifest.json](agents/claude-code/manifest.json)
- [agents/codex/manifest.json](agents/codex/manifest.json)
- [agents/copilot/manifest.json](agents/copilot/manifest.json)

Each has four top-level option dimensions: `level`, `type` (`api|cli`), `ui` (`none|react|angular`), `ci` (`github|azure`). The `variants.type.*` blocks own the root agent file. The `variants.ui.*` blocks contribute a sidecar root file (`CLAUDE-UI.md`, `.github/copilot-instructions-ui.md`, `src/AGENTS.md`) plus UI-scoped rules/skills.

**Dead sidecar destinations to be removed:**
- [agents/claude-code/manifest.json:178](agents/claude-code/manifest.json#L178), [212](agents/claude-code/manifest.json#L212), [238](agents/claude-code/manifest.json#L238), [255](agents/claude-code/manifest.json#L255), [272](agents/claude-code/manifest.json#L272) — `dest: "CLAUDE-UI.md"`
- [agents/copilot/manifest.json:164](agents/copilot/manifest.json#L164), [181](agents/copilot/manifest.json#L181), [198](agents/copilot/manifest.json#L198), [221](agents/copilot/manifest.json#L221), [238](agents/copilot/manifest.json#L238), [255](agents/copilot/manifest.json#L255) — `dest: ".github/copilot-instructions-ui.md"`
- Codex's `src/AGENTS.md` ([agents/codex/manifest.json:178](agents/codex/manifest.json#L178)) is **not** dead — Codex's hierarchical loader picks it up — but the manifest will still need updating to put UI content at the *root* `AGENTS.md` when `type=ui-react`/`ui-angular` is selected (UI-only shape).

### 2.3 L5 UI silent fallback bug

Every `variants.ui.{react,angular}.level_5.files[0]` currently references `l4-ui-*.md` rather than `l5-ui-*.md`. No `l5-ui-react.md` / `l5-ui-angular.md` files exist. L5 UI installs silently fall back to L4 content:

- [agents/claude-code/manifest.json:212](agents/claude-code/manifest.json#L212), [272](agents/claude-code/manifest.json#L272)
- [agents/codex/manifest.json:212](agents/codex/manifest.json#L212), [272](agents/codex/manifest.json#L272)
- [agents/copilot/manifest.json:198](agents/copilot/manifest.json#L198), [255](agents/copilot/manifest.json#L255)

This refactor fixes it as part of authoring the new UI shape content (§5.2).

### 2.4 Skills — Open Skills compliance gaps

Per-agent SKILL.md frontmatter audit:

| Agent | `name:` | `description:` | Extras | `$ARGUMENTS` in body |
|---|---|---|---|---|
| claude-code | **missing** | yes | `argument-hint:` | yes |
| codex | yes | yes | (none) | no — "determine from user's request" |
| copilot | yes | yes | `argument-hint:`, `user-invocable: true` | yes |

Sample evidence:
- [agents/claude-code/skills/backend/spec-planning/SKILL.md:1-4](agents/claude-code/skills/backend/spec-planning/SKILL.md#L1-L4) — missing `name:`, uses `$ARGUMENTS`
- [agents/codex/skills/backend/spec-planning/SKILL.md:1-4](agents/codex/skills/backend/spec-planning/SKILL.md#L1-L4) — compliant
- [agents/copilot/skills/backend/spec-planning/SKILL.md:1-6](agents/copilot/skills/backend/spec-planning/SKILL.md#L1-L6) — uses `$ARGUMENTS` and `user-invocable:` extension

All 27 SKILL.md files (3 agents × 9 skills) get normalized in Phase 1.

### 2.5 Generic rules — repo-scope.md leakage

[agents/claude-code/rules/generic/repo-scope.md:50](agents/claude-code/rules/generic/repo-scope.md#L50) explicitly lists `services/`, `adapters/`, `ports/` in its forbidden-patterns section. The file is labeled "generic" but contains backend-specific paths. Same content lives in:

- [agents/codex/rules/generic/repo-scope.md](agents/codex/rules/generic/repo-scope.md)
- [agents/copilot/instructions/generic/repo-scope.instructions.md](agents/copilot/instructions/generic/repo-scope.instructions.md)

Phase 2 splits this into backend and UI variants (or rewrites it to be truly path-agnostic — see §5.3).

### 2.6 CI workflows

Backend gates: `ci/{github,azure}/{l3-quality-gate,quality-gate,eval-gate,repo-scope-check}.yml`
UI gates: `ci/{github,azure}/{ui-quality-gate,ui-eval-gate}.yml`

Today's manifest `ci.{github,azure}` blocks ship the L3 backend `l3-quality-gate.yml` regardless of project type. UI-only installs get backend gates that don't apply.

### 2.7 Tests

- [tests/test_govkit.py](tests/test_govkit.py) — `TestVariantResolution`, `TestResolveOptions`, `TestSmokeApply`, `TestSmokeInit`. Several tests use the `--type api --ui react` cross-product directly or via `resolve_variant_files({"type": "api", "ui": "react", "ci": "github"})`.
- [tests/test_validate.py](tests/test_validate.py) — reads `type` from `.govkit` marker; no UI-aware paths today.

### 2.8 Smoke scripts (external sandbox)

Currently live in `c:\users\marty\source\sandbox\govkit-test\`:

- `smoke.ps1` — backend matrix (3 agents × 3 levels). Calls `govkit apply --type api --ui none`.
- `smoke-ui.ps1` — UI matrix (3 agents × 2 frameworks × 3 levels). Calls `govkit apply --type api --ui $framework`.
- `smoke-dotnet.ps1` — backend matrix with .NET-realistic feature content. Calls `govkit apply --type api --ui none`.

Brought into the repo at `scripts/` in Phase 0 (§5.6).

### 2.9 Documentation

- [README.md](README.md) — references `--type` and `--ui` flags in usage examples; documents the cross-product.
- [CONTRIBUTING.md](CONTRIBUTING.md) — agent parity invariant.
- [PARITY_TEST.md](PARITY_TEST.md) — parity matrix.

---

## 3. Target shape

### 3.1 New `--type` enumeration

```text
--type api          # Backend HTTP API (hexagonal: api/, services/, ports/, adapters/, security/)
--type cli          # Backend CLI       (hexagonal minus api/)
--type ui-react     # React SPA         (src/features/, src/shared/)
--type ui-angular   # Angular SPA       (src/features/, src/shared/)
```

`--ui` is removed entirely. Existing 0.7.0 installs that used `--ui react` were materially broken on Claude and Copilot anyway (dead sidecar); per §7, no migration is provided — re-run `govkit apply` with the new flag.

### 3.2 Manifest dimensions after refactor

```jsonc
{
  "agent": "claude-code",
  "options": {
    "level": { "choices": ["3", "4", "5"], "default": "3" },
    "type":  { "choices": ["api", "cli", "ui-react", "ui-angular"], "default": "api" },
    "ci":    { "choices": ["github", "azure"], "default": "github" }
  },
  "variants": {
    "type": {
      "api":         { /* unchanged from 0.7.0 */ },
      "cli":         { /* unchanged from 0.7.0 */ },
      "ui-react":    { /* NEW — owns root file at canonical path */ },
      "ui-angular":  { /* NEW — owns root file at canonical path */ }
    },
    "ci": {
      "github": { /* split into backend gates + ui gates by type-aware logic — see §4.4 */ },
      "azure":  { /* same */ }
    }
  }
}
```

No `ui` block. No `--ui` flag. No sidecar files.

### 3.3 Progressive loading by agent

Within a single project shape, each agent's native progressive-loading mechanism is used:

**Claude Code**
- Backend shapes: root `CLAUDE.md` references `.claude/rules/*.md` (unchanged from 0.7.0)
- UI shapes: root `CLAUDE.md` + **nested `src/CLAUDE.md`** containing the UI-scoped rules inline. The `.claude/rules/` directory is not used for UI rules.
- Rationale: Claude Code's recursive `CLAUDE.md` loader picks up `src/CLAUDE.md` only when the agent is working under `src/` — genuinely progressive.

**Codex**
- All shapes: nested `AGENTS.md` placed at the path each rule scopes to (e.g. `api/AGENTS.md`, `src/features/components/AGENTS.md`). Already correct in 0.7.0; only the *root* `AGENTS.md` placement changes for UI shapes (was `src/AGENTS.md` sidecar, becomes root + nested).

**Copilot**
- All shapes: `.github/instructions/*.instructions.md` with `applyTo:` frontmatter globs. Already correct in 0.7.0. UI shape files retain UI-scoped globs; backend shape files retain backend globs. No co-mingling because no fullstack shape exists.

### 3.4 Open Skills standard compliance

Every `SKILL.md` across all three agents converges on:

```yaml
---
name: <skill-name>
description: <one-sentence what-it-does AND when-to-use-it. The harness uses this to decide whether to invoke.>
---

<body — describes the operation; derives arguments from natural-language context;
asks the user if a required argument cannot be inferred. Body is loaded only when
the skill is invoked — progressive loading is automatic via the standard.>
```

Removed: `argument-hint:`, `user-invocable:`, `$ARGUMENTS` substitution patterns.

### 3.5 Fullstack workflow (documented, not enforced)

For monorepos that want both shapes:

```bash
govkit apply --agent claude-code --type api      --target apps/api
govkit apply --agent claude-code --type ui-react --target apps/web
```

Each subdir is a complete, self-contained govkit install. The three agents discover the relevant rules based on which subtree they're working in:

- **Codex** — walks up from current file to nearest `AGENTS.md`; finds `apps/api/AGENTS.md` or `apps/web/AGENTS.md` automatically.
- **Claude Code** — recursive `CLAUDE.md` discovery; finds `apps/api/CLAUDE.md` or `apps/web/CLAUDE.md` automatically.
- **Copilot** — `applyTo:` globs in each subdir's `.github/instructions/*.instructions.md` use subpath patterns (`apps/api/**/*`, `apps/web/src/**/*.tsx`).

This is documented in README.md and a new `docs/MONOREPO_PATTERN.md` (Phase 5).

---

## 4. Manifest semantics change

### 4.1 New rules

- The `ui` dimension is **deleted** from all three manifests. No deprecation, no compat shim — 0.7.0 `.govkit` markers that include `ui` are read tolerantly (the `ui` key is ignored on `govkit upgrade`).
- The `type` dimension's `choices` array gains `"ui-react"` and `"ui-angular"`.
- The new `type.ui-react` and `type.ui-angular` blocks have the same shape as `type.api` and `type.cli` (base + `level_4` merge + `level_5` replace), and own the canonical root agent file (`CLAUDE.md` / `AGENTS.md` / `.github/copilot-instructions.md`).

### 4.2 CLI implementation

`cli/govkit.py`:

- `apply_parser.add_argument("--type", choices=["api", "cli", "ui-react", "ui-angular"], ...)` — add the two UI choices.
- `apply_parser.add_argument("--ui", ...)` — **deleted**.
- `resolve_options` — unchanged; works generically across whatever options the manifest declares.
- `_select_variant` — unchanged.
- `_collect_entries` — unchanged.
- `_resolve_starter_dir` and `_prompt_starter_type` — `starter_type` enumeration changes from `["backend", "cli", "ui"]` to `["backend", "cli", "ui-react", "ui-angular"]`. (Note: `"backend"` stays as the starter slug for `--type api` since the starter is shape-flavored, not type-flavored. The mapping is documented in `_resolve_starter_dir`.)
- `cmd_init` — `--starter` choices update to match.

`cli/validate.py`:

- Wherever `type` is read from the marker or CLI, accept the new values.
- No new artifact requirements at this layer — UI shapes use the same 5-artifact spec as backend shapes (L4) or no artifacts (L3).

### 4.3 Starter template mapping

| `--type` | Starter slug used by `_resolve_starter_dir` |
|---|---|
| `api` | `starter_backend` (or `starter_backend_l5` at L5) |
| `cli` | `starter_cli` (or `starter_cli_l5` at L5) |
| `ui-react` | `starter_ui` (or `starter_ui_l5` if it exists at L5) |
| `ui-angular` | `starter_ui` (or `starter_ui_l5` if it exists at L5) |

`ui-react` and `ui-angular` share the same starter today (`starter_ui/` is framework-agnostic Gherkin/NFRs/plan content). If they diverge later, two separate starters (`starter_ui_react/`, `starter_ui_angular/`) can be added without manifest churn.

### 4.4 CI variants become shape-aware

Today's `ci.github.governed` ships `l3-quality-gate.yml` (backend) regardless of type. After refactor, each `ci.{github,azure}` block contains a per-`type` sub-block:

```jsonc
"ci": {
  "github": {
    "files": [],
    "shared": [],
    "governed": [],
    "by_type": {
      "api":         { "governed": ["ci/github/l3-quality-gate.yml", "ci/github/repo-scope-check.yml"] },
      "cli":         { "governed": ["ci/github/l3-quality-gate.yml", "ci/github/repo-scope-check.yml"] },
      "ui-react":    { "governed": ["ci/github/l3-ui-quality-gate.yml"] },
      "ui-angular":  { "governed": ["ci/github/l3-ui-quality-gate.yml"] }
    },
    "level_4": { /* same shape with by_type */ },
    "level_5": { /* same shape with by_type */ }
  }
}
```

Resolver change: `resolve_variant_files` reads the current `type` value when expanding the `ci.*` dimension and merges `by_type[type]` into the entries returned for that dimension. This is a small, contained extension to `_dimension_entries`.

**Alternative considered** (rejected): make `ci` an implicit consequence of `type` (no separate dimension, no `--ci` flag). Rejected because `--ci github` vs `--ci azure` is genuinely orthogonal — a backend API can ship on either CI; same for UI. Keeping `ci` as its own dimension preserves that.

A new CI file `ci/{github,azure}/l3-ui-quality-gate.yml` is authored as part of §5.5.

---

## 5. Authoring tasks (new content needed)

### 5.1 Promote existing UI variants to primary root files (12 files)

The 0.7.0 manifest had UI variants targeting sidecar paths. Their *content* already describes a UI project well — what changes is the manifest `dest` and stripping any cross-references to the sidecar:

| Source | 0.7.0 dest (sidecar) | v0.8.0 dest (canonical) |
|---|---|---|
| `agents/claude-code/claude-md/ui-react.md` | `CLAUDE-UI.md` | `CLAUDE.md` |
| `agents/claude-code/claude-md/ui-angular.md` | `CLAUDE-UI.md` | `CLAUDE.md` |
| `agents/claude-code/claude-md/l4-ui-react.md` | `CLAUDE-UI.md` | `CLAUDE.md` |
| `agents/claude-code/claude-md/l4-ui-angular.md` | `CLAUDE-UI.md` | `CLAUDE.md` |
| `agents/codex/agents-md/ui-react.md` | `src/AGENTS.md` | `AGENTS.md` |
| `agents/codex/agents-md/ui-angular.md` | `src/AGENTS.md` | `AGENTS.md` |
| `agents/codex/agents-md/l4-ui-react.md` | `src/AGENTS.md` | `AGENTS.md` |
| `agents/codex/agents-md/l4-ui-angular.md` | `src/AGENTS.md` | `AGENTS.md` |
| `agents/copilot/copilot-instructions/ui-react.md` | `.github/copilot-instructions-ui.md` | `.github/copilot-instructions.md` |
| `agents/copilot/copilot-instructions/ui-angular.md` | `.github/copilot-instructions-ui.md` | `.github/copilot-instructions.md` |
| `agents/copilot/copilot-instructions/l4-ui-react.md` | `.github/copilot-instructions-ui.md` | `.github/copilot-instructions.md` |
| `agents/copilot/copilot-instructions/l4-ui-angular.md` | `.github/copilot-instructions-ui.md` | `.github/copilot-instructions.md` |

Content edits per file:

- Remove any reference to `CLAUDE-UI.md` / `copilot-instructions-ui.md` / `src/AGENTS.md` sidecar paths.
- Update the "see also" sections to point at sibling rule files at their new locations.
- Add the explicit "this is a UI-only project; if your team also ships a backend in this repo, see the monorepo pattern in `docs/MONOREPO_PATTERN.md`" note.

### 5.2 Author missing L5 UI variants (6 new files)

Today the L5 UI manifest blocks reference `l4-ui-*.md`. Author the true L5 versions:

- `agents/claude-code/claude-md/l5-ui-react.md`
- `agents/claude-code/claude-md/l5-ui-angular.md`
- `agents/codex/agents-md/l5-ui-react.md`
- `agents/codex/agents-md/l5-ui-angular.md`
- `agents/copilot/copilot-instructions/l5-ui-react.md`
- `agents/copilot/copilot-instructions/l5-ui-angular.md`

Content sketch (per file):
- Same operating-mode preamble as L5 backend variants.
- Reference L5 UI-specific rules (LLM-driven UX patterns, prompt-driven component generation governance, evaluation of UI-side LLM features).
- Cross-reference `docs/ui/evaluation/` and `governance/ui/` (already L4-installed; L5 adds depth).
- Note: deep L5-UI rule authoring (e.g. dedicated `rules/ui-react/llm-*.md` files) is **out of scope** for this refactor. The L5 root files reference the L4 UI rules plus the existing L5 *backend* LLM rules where applicable (since LLM-gateway/guardrails/observability/multi-agent rules apply to UI projects too — UI calls LLMs through the same governed path).

### 5.3 Split or genericize `repo-scope.md`

Two options:

**Option A** (recommended): split into two variants per agent.
- `rules/generic/repo-scope-backend.md` — references `services/`, `adapters/`, `ports/`
- `rules/generic/repo-scope-ui.md` — references `src/features/`, `src/shared/`
- Each `type.*` block in the manifest pulls the appropriate one.

**Option B**: rewrite to be path-agnostic.
- Drop all concrete path references; talk only about "modules owned by another repo" / "implementation code intended for another repo" generically.
- Slightly weaker (loses the helpful concrete examples) but ships one file.

Authoring impact: Option A = 6 new files (3 agents × 2 variants); Option B = 3 file rewrites. **Option A is recommended** — the concrete paths are pedagogically useful and the per-agent file count is small.

### 5.4 New nested `src/CLAUDE.md` for UI shapes (Claude Code only)

For `type=ui-react` and `type=ui-angular` on Claude Code, plant a `src/CLAUDE.md` containing the UI-scoped rules inline. The 0.7.0 pattern of separate `.claude/rules/components.md`, `viewmodel.md`, `ui-api.md`, `accessibility.md` files is replaced by a single `src/CLAUDE.md` that consolidates them.

Two new files per framework:
- `agents/claude-code/claude-md/src-ui-react.md` → `src/CLAUDE.md`
- `agents/claude-code/claude-md/src-ui-angular.md` → `src/CLAUDE.md`

(L4 and L5 variants share the same `src/CLAUDE.md` content unless the UI rules genuinely differ by level — they don't today.)

The root `CLAUDE.md` (UI-shape variant) cross-references `src/CLAUDE.md` so a user reading the root file knows where to look. Claude Code's loader picks up `src/CLAUDE.md` automatically when the agent works under `src/`.

For Codex and Copilot, no equivalent change — Codex already nests `AGENTS.md` per directory, Copilot already uses `applyTo` globs.

### 5.5 New `l3-ui-quality-gate.yml` CI file (2 files)

- `ci/github/l3-ui-quality-gate.yml`
- `ci/azure/l3-ui-quality-gate.yml`

Content: UI-appropriate lint (eslint/biome), unit tests (vitest/jest), build smoke (`npm run build`), accessibility check stub. Mirrors the structure of `l3-quality-gate.yml` but targets the UI toolchain.

L4 and L5 UI CI gates (`ui-quality-gate.yml`, `ui-eval-gate.yml`) already exist and stay.

### 5.6 Smoke scripts (move into repo)

Phase 0 of execution. See §10 for details.

### 5.7 Open Skills body rewrites (27 files)

For every `SKILL.md` across 3 agents × 9 skills:

- Normalize frontmatter to `name:` + `description:` only.
- Remove `argument-hint:`, `user-invocable:`.
- In description, ensure both "what it does" and "when to use it" are present in one sentence.
- Body: replace `$ARGUMENTS` substitution with natural-language argument extraction:
  ```markdown
  Plan the implementation of the named feature. When invoked, determine the
  feature name from the user's request; if it is not provided, ask before
  proceeding.
  ```
- Body content (paths to read, instructions) stays — only the argument-handling preamble changes.

Reference implementation: [agents/codex/skills/backend/spec-planning/SKILL.md](agents/codex/skills/backend/spec-planning/SKILL.md) is already compliant.

---

## 6. Impacted files

### 6.1 CLI (`cli/`)

- [cli/govkit.py](cli/govkit.py):
  - argparse `--type` choices: add `ui-react`, `ui-angular`.
  - argparse `--ui` argument: **delete**.
  - `_resolve_starter_dir`: handle `ui-react`/`ui-angular` (map both to `starter_ui`).
  - `_prompt_starter_type`: choices `["backend", "cli", "ui-react", "ui-angular"]`.
  - `cmd_init` `--starter` choices: same update.
  - `_dimension_entries` (or `_select_variant`): extend to honor `by_type` sub-blocks for `ci` dimension. See §4.4.
  - Help text on `--type`: update to enumerate all four shapes.

- [cli/validate.py](cli/validate.py):
  - Audit for any hardcoded `type ∈ {api, cli}` checks; accept UI types.
  - No new validation logic — UI shapes share L4 5-artifact requirements with backend shapes.

### 6.2 Manifests (3 files)

- [agents/claude-code/manifest.json](agents/claude-code/manifest.json)
- [agents/codex/manifest.json](agents/codex/manifest.json)
- [agents/copilot/manifest.json](agents/copilot/manifest.json)

Each manifest:
- `options.type.choices` += `["ui-react", "ui-angular"]`.
- `options.ui` block: **delete**.
- `variants.ui` block: **delete**.
- `variants.type.ui-react`: **new** — owns canonical root file dest, references UI rules at progressive-loading paths.
- `variants.type.ui-angular`: **new** — same shape.
- `variants.ci.{github,azure}`: restructure with `by_type` sub-blocks per §4.4.
- L5 UI variants (now inside `variants.type.ui-{react,angular}.level_5`): reference `l5-ui-*.md` (not `l4-ui-*.md`).

### 6.3 Content files

**New (8):**
- `agents/{claude-code,codex,copilot}/{claude-md,agents-md,copilot-instructions}/l5-ui-{react,angular}.md` — 6 files (§5.2)
- `agents/claude-code/claude-md/src-ui-{react,angular}.md` — 2 files (§5.4)

**New from split (6):**
- `agents/{claude-code,codex}/rules/generic/repo-scope-{backend,ui}.md` — 4 files
- `agents/copilot/instructions/generic/repo-scope-{backend,ui}.instructions.md` — 2 files

**Edited (12):**
- `agents/{claude-code,codex,copilot}/{claude-md,agents-md,copilot-instructions}/{ui-react,ui-angular,l4-ui-react,l4-ui-angular}.md` — strip sidecar cross-references (§5.1)

**Edited (27):**
- All `agents/*/skills/**/SKILL.md` files — Open Skills compliance (§5.7)

**Deleted (0):**
- The original `repo-scope.md` / `repo-scope.instructions.md` files are renamed-then-edited via §5.3; no files truly deleted.

### 6.4 CI files

- `ci/github/l3-ui-quality-gate.yml` — **new**
- `ci/azure/l3-ui-quality-gate.yml` — **new**
- Existing `ci/{github,azure}/{l3-quality-gate,ui-quality-gate,ui-eval-gate}.yml` — unchanged.

### 6.5 Schemas

- [governance/schemas/agent-manifest.schema.json](governance/schemas/agent-manifest.schema.json):
  - Remove the `ui` dimension from the schema.
  - Add `ui-react` and `ui-angular` to the `type.choices` enum (or whatever the schema's expression for that is).
  - Add `by_type` sub-block support for `ci` dimension if the schema is strict on the shape.

### 6.6 Tests

- [tests/test_govkit.py](tests/test_govkit.py):
  - Any test calling `resolve_variant_files(..., {"type": "api", "ui": "react"})` → `({"type": "ui-react"})` or equivalent.
  - Add new tests for `type.ui-react` and `type.ui-angular` variant expansion.
  - Add test for `by_type` CI resolution.
  - Remove `--ui` argparse test cases.

- [tests/test_validate.py](tests/test_validate.py):
  - Add UI-type fixtures (`.govkit` markers with `type: ui-react`, `type: ui-angular`).
  - Confirm validate handles UI types the same as backend types at L3 (short-circuit), L4 (5-artifact), L5 (LLM-checks).

### 6.7 Smoke scripts

Moved from sandbox to repo at Phase 0; updated at Phase 4. See §10.

### 6.8 Documentation

- [README.md](README.md):
  - Replace `--type {api,cli}` + `--ui {none,react,angular}` examples with flat `--type {api,cli,ui-react,ui-angular}`.
  - Add monorepo pattern section (link to new `docs/MONOREPO_PATTERN.md`).
  - Update install matrix table.

- [CONTRIBUTING.md](CONTRIBUTING.md):
  - Agent parity invariant — note that all 3 agents ship identical Open-Skills-compliant SKILL.md files.

- [PARITY_TEST.md](PARITY_TEST.md):
  - Update parity matrix to reflect 4 shapes × 3 levels × 3 agents = 36 combinations.

- `docs/MONOREPO_PATTERN.md` — **new**. Documents the "apply per subdir" pattern with examples for all three agents.

---

## 7. Migration / no-migration story

Per the v0.8.0 product decision: **no automated migration**.

`.govkit` markers written by 0.7.0 may include `"ui": "react"` or `"ui": "angular"` in their `options` block. On `govkit upgrade`:

- The `ui` key is read tolerantly (no schema-strict failure).
- A one-time warning is printed to stderr: *"Project shape model changed in v0.8.0. The `ui` option is no longer supported. Re-run `govkit apply --type ui-react` (or `ui-angular`) to switch to a UI shape, or run `govkit apply --type api` to keep the current backend shape."*
- The warning is suppressible via `GOVKIT_NO_SHAPE_MIGRATION_WARNING=1`.
- `govkit upgrade` itself proceeds — it refreshes whatever shape the marker resolves to, treating `ui` as ignored.

No interactive migration prompt (no equivalent of v0.7.0's `--migrate-levels`). Per the user, "not many are using the govkit yet" so the cost of manual re-apply is acceptable.

---

## 8. Test plan

### 8.1 Unit tests (test_govkit.py)

Add to `TestVariantResolution`:
- `test_type_ui_react_at_l3` — `resolve_variant_files({"type": "ui-react", "ci": "github"}, level="3")` returns expected UI files at root paths, no backend leakage.
- `test_type_ui_angular_at_l3` — same for angular.
- `test_type_ui_react_at_l4` — adds spec-driven artifacts; root file is `l4-ui-react.md`.
- `test_type_ui_react_at_l5` — root file is `l5-ui-react.md` (regression: 0.7.0 silently fell back to L4).
- `test_ci_by_type_dispatch_backend` — `ci.github` with `type=api` yields backend gates.
- `test_ci_by_type_dispatch_ui` — `ci.github` with `type=ui-react` yields `l3-ui-quality-gate.yml`.
- `test_no_ui_dimension` — manifest lacks `options.ui` and `variants.ui`.
- `test_ui_option_in_marker_tolerated_on_upgrade` — `.govkit` with `"ui": "react"` in `options` doesn't crash `read_govkit_marker`.

Add to `TestSmokeApply`:
- `test_apply_ui_react_at_l3` — end-to-end apply to a temp dir; assert canonical root file exists and contains UI content; assert no backend rule files leak.
- `test_apply_ui_angular_at_l4` — same plus 5-artifact feature scaffolding.
- `test_apply_no_ui_flag_in_argparse` — argparse rejects `--ui react`.

### 8.2 Validate tests (test_validate.py)

- `test_validate_ui_react_l3_no_op` — UI L3 install validates clean with no features.
- `test_validate_ui_react_l4_5_artifact` — UI L4 install with a UI feature dir validates clean.
- `test_validate_ui_marker_tolerated` — `.govkit` with `type: ui-react` reads cleanly.

### 8.3 Schema tests

- `test_manifest_schema_no_ui` — schema rejects manifests with `options.ui`.
- `test_manifest_schema_ui_types_allowed` — schema accepts `type.choices` containing `ui-react`, `ui-angular`.

### 8.4 Smoke matrix

After Phase 4, run all three smoke scripts. Expected baseline (all green):

```
smoke.ps1         — 9 configs (3 agents × {api,cli, ui-react,ui-angular?} × ...
                   Actually no — smoke.ps1 covers backend; ui shapes go to smoke-ui.ps1.
                   See §10 for the post-refactor smoke matrix definition.)
smoke-ui.ps1      — 12 configs (3 agents × 2 UI shapes × 3 levels)
smoke-dotnet.ps1  — 9 configs (3 agents × 3 levels; type=api)
```

(L5 UI is expected to apply successfully but fail validate, same as L5 backend with non-LLM feature content — consistent with the established smoke-script expectation.)

---

## 9. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Hidden `.claude/rules/` references in UI shape break Claude Code agents that don't pick up `src/CLAUDE.md` | Medium | Confirm Claude Code's nested-CLAUDE.md loader behavior with a smoke test before Increment 8; if it doesn't work, fall back to flat `.claude/rules/` for UI. |
| Open Skills body rewrites break agent-specific harness expectations (e.g. Copilot's `user-invocable: true` may be load-bearing) | Medium | Pilot the rewrite on a single skill per agent first (Increment 1); verify it still invokes correctly in each agent before doing all 27. |
| `by_type` CI dispatch is a new resolver shape; risk of breaking the existing single-type CI case | Low | The new code path is additive — base `governed` array still works; `by_type` is opt-in per-dimension. Unit test both paths. |
| L5 UI authoring (§5.2) requires content that doesn't exist yet (deep LLM-UI rules) | Low | Scope the L5 UI files to reference existing L4 UI + L5 backend LLM rules. Deep new content deferred to a follow-up release. |
| Smoke scripts in repo break for contributors with different machine layouts | Medium | Default `$RepoPath` relative to `$PSScriptRoot`; document override in `scripts/README.md`. Test on a fresh checkout. |
| 0.7.0 → 0.8.0 marker migration warning fires constantly for downstream automation | Low | `GOVKIT_NO_SHAPE_MIGRATION_WARNING=1` env var documented. |
| Splitting `repo-scope.md` doubles per-agent maintenance | Low | Acceptable — both variants share most content; only the concrete-paths section differs. |

---

## 10. Smoke scripts in detail

### 10.1 Move into repo (Phase 0, Increment 0a)

The three sandbox scripts move to `scripts/` and become repo-canonical. The external sandbox at `c:\users\marty\source\sandbox\govkit-test\` continues to work — users pass `-SandboxRoot` to redirect output there.

```
scripts/
├── README.md              # how to run, parameter reference, troubleshooting
├── smoke.ps1              # backend matrix
├── smoke-ui.ps1           # UI shapes matrix
├── smoke-dotnet.ps1       # backend matrix, .NET-realistic feature content
├── smoke-inspect.ps1      # NEW: visual inspection helper
└── projects/              # default output dir (gitignored)
```

`.gitignore` additions:
```
scripts/projects/
scripts/projects-ui/
scripts/projects-dotnet/
scripts/.venv/
```

`$RepoPath` default changes from hardcoded `C:\Users\marty\source\repos\governed-ai-delivery` to:
```powershell
$RepoPath = Resolve-Path (Join-Path $PSScriptRoot "..")
```

So a fresh checkout's `scripts/smoke.ps1` automatically finds the parent repo.

### 10.2 New `smoke-inspect.ps1` (Phase 0, Increment 0b)

```powershell
<#
.SYNOPSIS
  Opens previously-applied smoke-test sandboxes for visual inspection.

.DESCRIPTION
  Picks one or more sandbox dirs from scripts/projects*/ and opens each in
  Explorer (default), VS Code, or as a console tree dump.

.PARAMETER Config
  Specific sandbox name to open (e.g. "claude-code-l3", "codex-ui-react-l4").

.PARAMETER Pattern
  Wildcard pattern across all sandbox dirs (e.g. "*ui*-l4", "claude-code-*").

.PARAMETER All
  Open every sandbox under scripts/projects*/.

.PARAMETER Editor
  "explorer" (default) | "code" (VS Code) | "tree" (console dump).

.PARAMETER SandboxRoot
  Where the sandbox dirs live. Default: this script's directory.

.EXAMPLE
  .\smoke-inspect.ps1 -Config claude-code-l3
  .\smoke-inspect.ps1 -Pattern "*ui*-l4" -Editor code
  .\smoke-inspect.ps1 -All -Editor tree
#>
```

Behavior:
- `-Config` selects exactly one; `-Pattern` filters; `-All` opens every leaf dir under `projects/`, `projects-ui/`, `projects-dotnet/`.
- `-Editor explorer` (default): `Invoke-Item` each dir → Windows opens an Explorer window per dir.
- `-Editor code`: `& code $dir` — opens in VS Code.
- `-Editor tree`: prints a `Get-ChildItem -Recurse -Force` tree to stdout per dir, with file sizes and a header.

### 10.3 Post-refactor smoke matrix definitions (Phase 4, Increment 11)

After the `--ui` flag is removed:

**`scripts/smoke.ps1`** (backend matrix, unchanged dimensions):
```powershell
[CmdletBinding()]
param(
    [string[]]$Agents = @("claude-code", "codex", "copilot"),
    [string[]]$Types  = @("api", "cli"),
    [string[]]$Levels = @("3", "4", "5"),
    ...
)
# Inside the loop:
& $venvGovkit apply --agent $agent --type $type --level $level --ci github --target $projectPath
# (No --ui none)
```

Output dir: `scripts/projects/`. 18 configs (3 × 2 × 3).

**`scripts/smoke-ui.ps1`** (UI matrix, rewritten):
```powershell
[CmdletBinding()]
param(
    [string[]]$Agents = @("claude-code", "codex", "copilot"),
    [string[]]$Types  = @("ui-react", "ui-angular"),
    [string[]]$Levels = @("3", "4", "5"),
    ...
)
# Inside the loop:
& $venvGovkit apply --agent $agent --type $type --level $level --ci github --target $projectPath
```

Output dir: `scripts/projects-ui/`. 18 configs (3 × 2 × 3).

**`scripts/smoke-dotnet.ps1`** (unchanged dimensions, `--ui none` removed):
Output dir: `scripts/projects-dotnet/`. 9 configs (3 × 1 × 3).

Total post-refactor matrix: 45 configs across the three scripts.

---

## 11. Increments

Each increment is a single atomic commit (`refactor: increment N project-shape`). Commits are independently reversible; the matrix-breaking commit is Increment 11 (Phase 4) — explicitly the breaking point.

### Phase 0 — Tooling (no behavior change)

**Increment 0a: Move smoke scripts into repo.**
- Copy `smoke.ps1`, `smoke-ui.ps1`, `smoke-dotnet.ps1` from sandbox into `scripts/`.
- Change `$RepoPath` default to `Resolve-Path (Join-Path $PSScriptRoot "..")`.
- Add `.gitignore` entries for `scripts/projects*/`, `scripts/.venv/`.
- Write `scripts/README.md` (parameter reference, examples, sandbox-redirect via `-SandboxRoot`).
- Run scripts once with default `-SandboxRoot` to verify in-repo execution works.

**Increment 0b: Author `scripts/smoke-inspect.ps1`.**
- Implement the four `-Editor` modes (explorer, code, tree, default).
- Implement `-Config`, `-Pattern`, `-All` selection.
- Document in `scripts/README.md`.

**Increment 0c: Capture pre-refactor baseline.**
- Run all three smoke scripts with `-Force` from a clean state.
- `smoke-inspect.ps1 -All -Editor tree > tmp/baseline.txt` — textual snapshot of every sandbox's file tree.
- Commit the baseline to a gitignored `tmp/` location with a note in the commit message describing where the snapshot lives.

### Phase 1 — Open Skills compliance (skills only)

**Increment 1: Pilot Open Skills rewrite on one skill per agent.**
- Pick `spec-planning` as the pilot (already compliant on Codex; needs rewrite on Claude and Copilot).
- Rewrite Claude's `agents/claude-code/skills/backend/spec-planning/SKILL.md`:
  - Add `name: spec-planning` to frontmatter.
  - Remove `argument-hint:`.
  - Replace `$ARGUMENTS` substitution with Codex-style natural-language argument extraction.
- Rewrite Copilot's `agents/copilot/skills/backend/spec-planning/SKILL.md`:
  - Remove `argument-hint:` and `user-invocable:`.
  - Replace `$ARGUMENTS` substitution.
- Smoke-test invocation in each agent (manual; Claude Code IDE / Copilot Chat / Codex CLI).
- If a load-bearing extension is found (e.g. Copilot's `user-invocable:`), document and revisit Phase 1 scope before Increment 2.

**Increment 2: Roll Open Skills compliance across all 27 SKILL.md files.**
- Apply the same frontmatter + body changes to all remaining skills (backend: `architecture-preflight`, `implementation-plan`, `adr-author`, `genai-preflight`, `eval-suite-planning`, `multi-agent-design`; ui: `spec-planning`, `architecture-preflight`, `implementation-plan`, `adr-author`).
- 26 file edits (one pilot already done).
- Verify parity: `diff` Claude vs Codex vs Copilot SKILL.md bodies should differ only in path notation conventions (e.g. `**` vs no glob) — frontmatter must be identical.

**Increment 3: Audit `description:` fields for "when to use" cues.**
- Pass over all 27 SKILL.md descriptions.
- Ensure each describes both *what it does* and *when to invoke*.
- Example: `"Generate a feature plan (plan.md) and eval_criteria.yaml from NFRs and acceptance scenarios. Use when the user asks to plan a feature or run /spec-planning."`
- Run smoke scripts; confirm no regression in apply output.

### Phase 2 — Manifest schema refactor (additive)

**Increment 4: Add `ui-react` and `ui-angular` to `type` choices in all 3 manifests.**
- Add the new options to `options.type.choices` in claude-code, codex, copilot manifests.
- Add empty `variants.type.ui-react` and `variants.type.ui-angular` blocks (placeholders — populated in Increment 5).
- Update argparse `--type` choices in `cli/govkit.py`.
- Tests pass (no functional change yet; new types just don't install anything).
- Smoke scripts unchanged.

**Increment 5: Populate `variants.type.ui-react` and `variants.type.ui-angular` blocks.**
- For each agent, author the base + `level_4` + `level_5` blocks pointing at the existing UI rule sources (`rules/ui-react/*.md`, `rules/ui-angular/*.md`).
- The root file (`CLAUDE.md` / `AGENTS.md` / `.github/copilot-instructions.md`) points at the existing `ui-{react,angular}.md` content (which targets the canonical dest, not the sidecar).
- L5 entries reference `l5-ui-{react,angular}.md` (placeholder files authored in Increment 6).
- Smoke-test by running `govkit apply --type ui-react` (the new path) to a temp dir; verify canonical root file exists.
- Note: at this point both `--type api --ui react` (old path, dead sidecar) and `--type ui-react` (new path, canonical root) work. The `--ui` flag is still present; cleanup is Phase 4.

**Increment 6: Author the 6 missing L5 UI variant root files.**
- `agents/{claude-code,codex,copilot}/{claude-md,agents-md,copilot-instructions}/l5-ui-{react,angular}.md`
- Content per §5.2.
- Wire into the `level_5` blocks added in Increment 5.
- Test: `govkit apply --type ui-react --level 5` produces the L5 root file (not the L4 fallback).

**Increment 7: Split `repo-scope.md` into backend/ui variants per Option A.**
- Author `repo-scope-backend.md` and `repo-scope-ui.md` (or `.instructions.md` for Copilot).
- Update each `variants.type.*` block to reference the appropriate variant.
- Delete the original `repo-scope.md` / `repo-scope.instructions.md` (or keep as a copy of `repo-scope-backend.md` for compat — TBD during execution).
- Test: backend shape installs `repo-scope-backend.md`; UI shape installs `repo-scope-ui.md`.

### Phase 3 — Progressive loading hardening

**Increment 8: Plant nested `src/CLAUDE.md` for Claude UI shapes.**
- Author `agents/claude-code/claude-md/src-ui-{react,angular}.md`.
- Update `variants.type.ui-{react,angular}` for claude-code to install these at `src/CLAUDE.md`.
- Remove the `.claude/rules/{components,viewmodel,ui-api,accessibility}.md` entries from the UI-shape variants for Claude only (they're now consolidated inside `src/CLAUDE.md`).
- Verify Claude Code picks up `src/CLAUDE.md` when working under `src/` (manual smoke test in Claude Code IDE).
- If the loader doesn't work as expected, revert to flat `.claude/rules/` for UI on Claude and document the limitation.

**Increment 9: Audit Copilot UI `applyTo:` globs.**
- Read every `agents/copilot/instructions/ui-{react,angular}/*.instructions.md` frontmatter.
- Confirm `applyTo:` is present and scoped to `src/**/*.tsx` (react) or `src/**/*.ts` (angular) — not a globless catch-all.
- Fix any missing or over-broad globs.
- Smoke-test by applying `--type ui-react` and inspecting `.github/instructions/`.

**Increment 10: Audit Codex UI nested `AGENTS.md` placements.**
- Verify `variants.type.ui-{react,angular}` in codex manifest plants `AGENTS.md` at:
  - Project root (for the UI-shape overview)
  - `src/AGENTS.md` (for the src tree)
  - `src/features/components/AGENTS.md` (for React/Angular components specifically)
  - `src/features/hooks/AGENTS.md` (or `src/features/services/` for Angular)
  - `src/features/api/AGENTS.md`
  - `src/shared/accessibility/AGENTS.md`
- Adjust dests if any are missing or misplaced.

### Phase 4 — Schema cleanup (breaking)

**Increment 11: Remove the `ui` dimension entirely.**
- Delete `options.ui` and `variants.ui` blocks from all 3 manifests.
- Delete `--ui` argument from `cli/govkit.py` argparse.
- Delete the sidecar files from the agent content dirs:
  - `agents/claude-code/claude-md/{ui-react,ui-angular,l4-ui-react,l4-ui-angular}.md` are kept (they're now used by `variants.type.ui-*`) — verify.
  - Actually no deletions of source files; only manifest dests change.
- Update smoke scripts:
  - `scripts/smoke.ps1`: drop `--ui none` from the apply call.
  - `scripts/smoke-dotnet.ps1`: drop `--ui none`.
  - `scripts/smoke-ui.ps1`: rewrite `$Frameworks` → `$Types` per §10.3; drop `--ui` from the apply call.
- Update `read_govkit_marker` to log the one-time warning when `ui` is present in the marker's `options`.
- This is the breaking commit. Tests that referenced `--type api --ui react` must be updated in lockstep.

**Increment 12: Update CLI starter resolution.**
- `_resolve_starter_dir`: handle `ui-react`, `ui-angular` (map both to `starter_ui` or `starter_ui_l5`).
- `_prompt_starter_type` and `cmd_init` `--starter` choices: `["backend", "cli", "ui-react", "ui-angular"]`.
- Test `govkit init my_feature --target <ui-shape-project>` creates a feature from `starter_ui/`.

**Increment 13: Update `cli/validate.py` and `governance/schemas/agent-manifest.schema.json`.**
- Audit validate.py for hardcoded `type` value checks; accept UI types.
- Schema: remove `ui` dimension; add UI types to `type` enum.
- Run full test suite; fix any remaining `--ui` references.

### Phase 4.5 — CI dispatch (small standalone increment)

**Increment 14: Implement `by_type` CI dispatch.**
- Extend `_dimension_entries` or `_select_variant` to honor a `by_type` sub-block on the `ci` dimension only.
- Update `variants.ci.{github,azure}` blocks in all 3 manifests to use `by_type`.
- Author `ci/github/l3-ui-quality-gate.yml` and `ci/azure/l3-ui-quality-gate.yml`.
- Test: `--type api --ci github` produces backend CI files; `--type ui-react --ci github` produces UI CI files.

### Phase 5 — Validation and docs

**Increment 15: Update tests.**
- Rewrite affected `tests/test_govkit.py` tests per §8.1.
- Rewrite affected `tests/test_validate.py` tests per §8.2.
- Add schema test per §8.3.
- Run full test suite; expect green.

**Increment 16: Full smoke matrix run.**
- Run `scripts/smoke.ps1 -Force`, `scripts/smoke-ui.ps1 -Force`, `scripts/smoke-dotnet.ps1 -Force`.
- For each leaf sandbox, run `scripts/smoke-inspect.ps1 -Config <name> -Editor tree` and visually scan.
- Expected: 45 configs apply; L3/L4 validate clean; L5 validate fails on missing LLM artifacts (consistent with existing convention).
- Diff against Increment 0c baseline (textual `tree.txt` output) — spot-check that UI shapes have no backend leakage and backend shapes have no UI leakage.

**Increment 17: Update README, CONTRIBUTING, PARITY_TEST, write MONOREPO_PATTERN.md.**
- README: new install matrix, new examples, monorepo section.
- CONTRIBUTING: Open Skills note.
- PARITY_TEST.md: refresh parity matrix (36 → 36 combinations; same dimensions but different composition).
- New `docs/MONOREPO_PATTERN.md`: subpath-install pattern with per-agent code samples.

**Increment 18: Bump version to 0.8.0 and CHANGELOG.**
- `pyproject.toml`: `version = "0.8.0"`.
- `CHANGELOG.md`: 0.8.0 entry summarizing project shape refactor + Open Skills compliance + progressive loading hardening.
- Note breaking change: `--ui` removed; users must re-apply.

---

## 12. Rollback strategy

Each increment is a single git commit; `git revert <sha>` undoes that increment alone.

- Phase 0 (Increments 0a–0c): pure additive — `git revert` removes scripts cleanly.
- Phase 1 (Increments 1–3): SKILL.md frontmatter changes — `git revert` restores the original frontmatter and body.
- Phase 2 (Increments 4–7): additive manifest changes — `git revert` removes the new `type` entries. Existing installs continue to work.
- Phase 3 (Increments 8–10): structural placement changes — `git revert` restores the previous placement.
- Phase 4 (Increment 11): the breaking commit. `git revert` restores `--ui` flag and `ui` dimension. **All Phase 5 increments depend on this**, so reverting Increment 11 requires also reverting Increments 12, 13, 14.
- Phase 4.5 (Increment 14): isolated to CI dispatch — independently revertable.
- Phase 5 (Increments 15–18): docs/tests/version — independently revertable.

If a fundamental problem is found at Phase 4 (e.g. Claude Code's nested `CLAUDE.md` doesn't work as expected for UI shapes), the rollback path is:

1. Revert Increments 12, 13, 14, 15, 16, 17, 18 (in that order, or as a single revert range).
2. Revert Increment 11 (restores `--ui`).
3. Increments 4–10 stay in place — they're additive and don't break anything.
4. Re-plan Phase 3 with the limitation documented.

---

## 13. Open questions

1. **Does Claude Code's recursive `CLAUDE.md` loader work as expected for nested `src/CLAUDE.md`?** Need empirical confirmation in Increment 8 (smoke test inside Claude Code IDE). If not, fall back to flat `.claude/rules/` for UI shapes on Claude.

2. **`repo-scope.md` split vs genericize.** Plan recommends split (Option A in §5.3). User confirmation requested before Increment 7 starts.

3. **Should `--starter` accept `ui` as a shorthand for "let me pick later"?** Currently the plan has `--starter ui-react`/`ui-angular`. A `--starter ui` shorthand that picks based on the project's `.govkit` marker (which records the `type`) could be cleaner UX but adds resolver complexity. Deferred — keep explicit shorthands for now.

4. **L5 UI authoring depth.** Plan §5.2 keeps L5 UI light (references existing L4 UI + L5 backend LLM rules). If we want true L5 UI content (e.g. dedicated `rules/ui-react/llm-component-generation.md`), that's a follow-up release.

5. **Should `scripts/projects/` go to `tmp/projects/` instead?** `tmp/` is conventionally ephemeral; `scripts/projects/` is what `$PSScriptRoot`-relative defaults produce. Plan goes with `scripts/projects/` for simplicity; revisit if the directory pollution becomes annoying.

6. **Tech-stack-specific smoke scripts.** `smoke-dotnet.ps1` exists for backend; should we author parallel `smoke-react.ps1` / `smoke-angular.ps1` with framework-realistic feature content? Deferred — start with `smoke-ui.ps1` covering both frameworks generically.

---

## 14. Out of scope (explicitly)

- Migrating existing 0.7.0 `.govkit` markers automatically. Per §7, only a warning is printed.
- Adding new project shapes beyond `api`, `cli`, `ui-react`, `ui-angular` (e.g. `mobile`, `data-pipeline`). Out of scope; the new flat-enumeration model makes future additions straightforward but they're not in this release.
- Restructuring backend shapes to use nested `CLAUDE.md` (the way UI shapes will). Backend stays with flat `.claude/rules/*.md` for this release.
- Deep L5 UI content authoring. Per §5.2, L5 UI roots reference existing files; new LLM-UI-specific rules are deferred.
- Updating import-linter rules in `pyproject.toml` for UI projects. The `[tool.importlinter]` block is a backend-hexagonal reference template; UI projects don't use it.
- Renaming `starter_backend` to `starter_api` (the slug mismatch is mildly confusing but isn't worth a breaking change).

---

## 15. Done definition

This refactor is done when:

1. All 18 increments are committed.
2. `pytest tests/` passes.
3. All three smoke scripts pass end-to-end on a fresh checkout: 18 + 18 + 9 = 45 configs apply cleanly; L3/L4 validate green; L5 validate fails on LLM-checks (expected, consistent with v0.7.0).
4. `scripts/smoke-inspect.ps1 -All -Editor tree` produces output where:
   - Every backend-shape sandbox has no UI rule files anywhere.
   - Every UI-shape sandbox has no backend rule files anywhere.
   - Every Claude UI sandbox has `src/CLAUDE.md` containing the UI rules.
   - Every Codex sandbox has the expected nested `AGENTS.md` placements.
   - Every Copilot sandbox has `applyTo:` globs on every instruction file.
5. `pyproject.toml` shows `version = "0.8.0"`.
6. `CHANGELOG.md` has a 0.8.0 entry.
7. README, CONTRIBUTING, PARITY_TEST, and the new MONOREPO_PATTERN.md are coherent with the new shape model.
