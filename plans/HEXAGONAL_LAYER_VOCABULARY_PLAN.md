# Hexagonal Layer Vocabulary and Boundary Contract Plan

Settle the backend layer vocabulary across the whole payload — the domain
layer's name, where entities live, and which source layout the tooling
assumes — and replace `governance/backend/importlinter-reference.toml`
with a contract that actually enforces `BOUNDARIES.md`. Closes #77 (the
vocabulary) and #75 (the contract). These are one decision: the contract
names the packages, so its `layers` and `containers` lines cannot be
written until the layout is fixed.

Everything asserted here about import-linter behaviour and govkit's
detection and install paths was verified by running it, not by reading —
see the tables in Motivation and Target design.

Reported downstream from an L5 `api` install (`llm-application` +
`skill-oriented-agent-architecture`), but neither defect is L5-specific —
see scope per issue.

## Motivation (evidence)

### 1. Three incompatible layouts ship simultaneously (#77)

**Shape A — top-level `services/`, no `domain/`:**

| Source | Evidence |
| --- | --- |
| `docs/backend/architecture/REPO_STRUCTURE_README.md:23-49` | tree is `api/ ports/ services/ adapters/ common/` |
| `cli/stacks/*/TECH_STACK.md` (all 7 stacks) | same five folders |
| `cli/stacks/python-fastapi/overlay.yaml:47` | calibrate prompt names those five |
| `governance/backend/importlinter-reference.toml:22-28` | `layers = [api, ports, services, adapters, common]` |
| `cli/skill_context.py:50-52` | `domain: ["services/"]` |

**Shape B — top-level `domain/`:** `docs/backend/architecture/BOUNDARIES.md:11-14`.

**Shape C — `services/` nested under `domain/`:**
`cli/stacks/*/LAYER_IMPLEMENTATION.md:29` — "`src/domain/services/`, `src/domain/models/`".

The two files voting for `domain/` are each **self-contradictory**:

- `BOUNDARIES.md` §1 (`:11-14`) lists `domain/` and omits `api/` entirely,
  while §2's table (`:20`) governs `api/` and §5 (`:52-53`) assigns
  ownership of `services/user/` and `services/payment/`.
- `LAYER_IMPLEMENTATION.md:29` says `src/domain/services/`, while its own
  ASCII diagram twelve lines above (`:17`) shows the Domain layer as
  `services/, models/`.

Every file that is internally consistent already says `services/`.

**Root cause:** `ARCH_CONTRACT.md` — the authoritative contract — never
states the domain's on-disk path. It gives explicit paths for ports
(`ports/inbound/`, `ports/outbound/`), inbound adapters (`api/`) and
outbound adapters (`adapters/`), but for the domain it lists only
*contents* ("Contains: `services`, `models`, `use_cases`", `:19`). That
silence is the gap every other doc filled differently.

### 2. The reference contract is broken four ways (#75)

Verified empirically against import-linter 2.11 using a five-package
skeleton (`api`, `ports`, `services`, `adapters`, `common`):

1. **It is not valid import-linter TOML.** The file ships
   `[tool.importlinter.contracts.hexagonal]` (single-bracket table).
   import-linter 2.x requires `[[tool.importlinter.contracts]]` (array of
   tables). Copying it verbatim as the file's own header instructs
   produces `'str' object has no attribute 'items'` — a crash, not a gate.
2. **`services → ports` is forbidden.** The domain cannot import the port
   interfaces it depends on, which `ARCH_CONTRACT.md:12` requires it to.
3. **`adapters → ports` is forbidden.** Adapters cannot import the ports
   they implement — permitted by `BOUNDARIES.md:21` and
   `ARCH_CONTRACT.md:38`, and the defining move of the pattern.
4. **`services → adapters` is permitted.** The single most important
   forbidden edge — `ARCH_CONTRACT.md:37`, `BOUNDARIES.md:29` — passes
   silently. A false negative in a gate documented as blocking.

Defects 2 and 3 break a **conforming** repo; defect 4 lets a violating one
through. The file's own header comment ("Dependencies must flow inward:
api → ports → services → adapters → common") is incoherent — it places
`adapters` inside the domain.

Additionally, `api → services` (forbidden by `BOUNDARIES.md:28`) is not
expressible in a layers contract at all and is currently unenforced.

### 3. Domain entities have no agreed home, and `use_cases/` is a phantom

`ARCH_CONTRACT.md:19` says the Domain Core "Contains: `services`,
`models`, `use_cases`". Neither of the latter two survives contact with
the rest of the payload:

**`models`** is claimed by two layers at once:

| Source | Claim |
| --- | --- |
| `ARCH_CONTRACT.md:19` | `models` belongs to the domain |
| `LAYER_IMPLEMENTATION.md:17` | diagram: "Domain (Core Logic) — `services/, models/`" (siblings) |
| `LAYER_IMPLEMENTATION.md:29` | `src/domain/models/` (nested) |
| `SECURITY_AUTH_PATTERNS.md:115` | `models/user.py` defines `UserContext` — **top-level** |
| `REPO_STRUCTURE_README.md:50` | `common/` = "shared utilities and **data models**" |
| `BOUNDARIES.md:14` | `common/` = "cross-cutting concerns (logging, tracing, DTOs)" |

`REPO_STRUCTURE_README.md`'s five-folder tree has no `models/` at all and
files data models under `common/` — which `BOUNDARIES.md` scopes to DTOs.
Domain entities and transport DTOs are different things, and `common/` is
required to be dependency-free, so it is the wrong home for business
state. The only concrete worked example in the payload
(`SECURITY_AUTH_PATTERNS.md:115`) already uses a top-level `models/`.

**`use_cases`** exists nowhere but that one line. No tree, no stack, no
test, no rule declares a `use_cases/` folder. Everywhere else in the
payload "use cases" is prose describing what *inbound ports* express —
`agents/{claude-code,codex,copilot}/rules/backend/ports.md` all say
"Inbound ports (`ports/inbound/`) define how the domain logic is called
(use cases, command handlers)", and `LAYER_IMPLEMENTATION.md:85` repeats
it under Ports. `ARCH_CONTRACT.md:19` invented a folder nothing else
knows about.

### 4. A second, divergent copy exists

`pyproject.toml:109-127` carries the same broken contract in govkit's own
repo, labelled "a reference template for target projects". It is inert
here — govkit's source is `cli/`, not `src/`, and no workflow runs
`lint-imports` against this repo — which is precisely why it rotted
unnoticed. Two copies, no test, no consumer.

Nothing in `agents/`, `docs/`, `governance/`, `ci/`, or `cli/` references
`importlinter-reference.toml` by name.

### 5. Tooling assumes a layout the docs do not prescribe

`REPO_STRUCTURE_README.md:23-40` documents the tree as
`src/<project_package_name>/api/…` — one package deep — and justifies the
nesting at `:55-63`, the third reason being *"allows multiple services to
reuse the governance kit."* Multi-service intent is already written down.
Three parts of the toolchain never caught up:

**Architecture detection only sees one level into `src/`.** Verified by
running `build_profile` against three layouts:

| Layout | `detected_architecture_signals` | resulting `skill_context` |
| --- | --- | --- |
| `src/{api,ports,services,…}` (flat) | `['hexagonal-shape']` | `style: hexagonal`, layers populated |
| `src/mypkg/{api,ports,services,…}` (**documented**) | `[]` | `style: unknown`, layers empty |
| `src/{orders,billing}/{…}` (multi-service) | `[]` | `style: unknown`, layers empty |

`_top_level_folder_names` (`cli/detect.py:370-382`) scans only `target`,
`target/src`, `target/Source`, `target/models`. For `src/mypkg/ports/` it
sees `src`'s children as `{mypkg}`, so `_HEXAGONAL_FOLDERS` never reaches
its two-match threshold. **A project following govkit's own documented
structure is not recognised as hexagonal.**

**This matters more than a wrong hint.** `layers` is not informational —
`cli/rule_templating.py` expands `paths_template: layers.domain` into the
concrete `paths:` globs that scope every backend rule at install time.
A wrong or empty `layers` value does not merely mislabel a folder; it
determines whether rules attach to the code at all. (The `**/services/**`
fallback in the source rules survives an empty expansion, so claude-code
and copilot degrade safely — but skill consumers get `style: unknown`
and empty hints.)

**The contract hardcodes `containers = ["src"]`**, which resolves to
`src.services` — matching the flat layout, not the documented one. The
fixture that verified the replacement contract used the flat form, so
this gap survived verification and must be closed here.

**Codex hardcodes root-relative rule destinations.** `agents/codex/manifest.json`
maps `rules/backend/services.md → services/AGENTS.md`, `ports/AGENTS.md`,
`api/AGENTS.md`, `adapters/AGENTS.md`, `security/AGENTS.md` — literal paths,
and `install_common.py` has no `layers`-based destination templating.
claude-code and copilot are layout-agnostic (`**/services/**`). A codex
user on the documented layout gets an empty root-level `services/`
holding only an AGENTS.md, which codex will never apply to
`src/mypkg/services/` — it resolves AGENTS.md from the edited file upward.
Nothing is destroyed; the guidance simply lands where it cannot fire.

Virtues: **Unique** (one layer vocabulary, one contract definition),
**Coherent** (the contract enforces the doc that describes it),
**Honest** (a gate that passes means the boundary holds).

## Decision

**Standardize on top-level `services/`.** `BOUNDARIES.md` and
`LAYER_IMPLEMENTATION.md` are the files to change.

Rationale: every internally-consistent source already uses it, including
`REPO_STRUCTURE_README.md` — the document whose specific job is to state
the on-disk layout. Choosing `domain/` would mean editing seven stacks'
`TECH_STACK.md`, the calibrate prompt, `skill_context.py`, and every
installed `skill_context.yaml` downstream, to match two files that
disagree with themselves.

`ARCH_CONTRACT.md` gains an explicit domain path so the gap cannot reopen.

**Domain entities live in a top-level `models/`.** The domain layer is
therefore two packages — `services/` (behaviour) and `models/` (state) —
matching `ARCH_CONTRACT.md:19`, `LAYER_IMPLEMENTATION.md:17`'s diagram,
and the `models/user.py` worked example in `SECURITY_AUTH_PATTERNS.md:115`.
The canonical tree becomes six packages:

```
src/<package>/
├── api/        inbound adapters (HTTP)
├── ports/      inbound and outbound interfaces
├── services/   domain behaviour and orchestration
├── models/     domain entities and value objects
├── adapters/   outbound infrastructure implementations
└── common/     cross-cutting concerns (logging, tracing, DTOs)
```

`REPO_STRUCTURE_README.md:50` drops "data models" from `common/`'s
description, leaving "shared utilities". `BOUNDARIES.md:14` keeps DTOs in
`common/` — transport shapes that cross boundaries are distinct from
domain entities, and moving them too would widen this change without
resolving anything.

**Drop `use_cases` from `ARCH_CONTRACT.md:19`.** Use cases are expressed
as inbound ports and implemented by services, which is what all three
agents' `rules/backend/ports.md` already say in lockstep. This is a
deletion of phantom vocabulary, not a new folder.

**Keep `src/<package>/` as the canonical source layout**, as
`REPO_STRUCTURE_README.md` already documents. One service is simply the
N=1 case of the same shape, and `src/myservice/api/…` is ordinary Python
src-layout — nothing about it reads as ceremony. The flat `src/api/`
alternative is a dead end: adding a second service would mean rewriting
every import path. Tooling moves to the docs, not the reverse.

**One install per set of marker options; containers for everything else.**
This settles when to nest:

- Services that differ in `type`, `stack`, or `level` — e.g. `apps/api`
  (`type=api`) beside `apps/web` (`type=ui-nextjs`) — need **separate
  installs**. `marker.json` holds one `type`, and UI types reject
  `--stack` outright, so a backend+frontend monorepo cannot be expressed
  by one marker. Nested installs were verified working: agent config
  lands correctly namespaced per subtree for all three agents
  (`apps/web/.claude/skills/govkit-ui-*` beside the root's `govkit-*`),
  and Claude Code discovers directory-scoped skills.
- Services that share marker options and differ only by package — e.g.
  `src/orders/` and `src/billing/`, both `type=api` — stay in **one
  install** and are expressed as multiple import-linter `containers`.

Nesting for multiple same-type services is the wrong tool: it duplicates
governance docs and CI templates per service to express nothing but a
package name.

### Verified as already correct — do not change

`AGENTS.md` is merged, not overwritten. A pre-existing root or
path-scoped `AGENTS.md` keeps its content; govkit appends a delimited
`<!-- BEGIN GOVKIT GOVERNANCE -->` … `<!-- END GOVKIT GOVERNANCE -->`
block (manifest `"mode": "merge"`). Confirmed idempotent across
`apply --force` and `upgrade` — one marker pair, user content intact.
A filename prefix is impossible here because `AGENTS.md` is a fixed name
the agent looks for; the delimited block is the codex-side equivalent of
`.claude/rules/govkit/` and `.github/instructions/govkit/`. Recorded so a
later change does not "fix" working behaviour.

## Target design

### Contract (verified against import-linter 2.11)

```toml
[tool.importlinter]
root_package = "src"

# containers must name your service package(s), not bare "src".
# One service:      containers = ["src.myservice"]
# Several services: containers = ["src.orders", "src.billing"]
[[tool.importlinter.contracts]]
name = "Hexagonal Architecture"
type = "layers"
layers = ["api | adapters", "services", "ports", "models", "common"]
containers = ["src.myservice"]

[[tool.importlinter.contracts]]
name = "API talks only to inbound ports"
type = "forbidden"
source_modules = ["src.myservice.api"]
forbidden_modules = ["src.myservice.services"]

# Multi-service only — layers apply *within* each container and do not
# stop one service importing another. Uncomment and list your services.
# [[tool.importlinter.contracts]]
# name = "Services are independent"
# type = "independence"
# modules = ["src.orders", "src.billing"]
```

`containers` is the one line that varies per project. The layers list is
identical whether there is one service or ten — only the container list
grows. This replaces the current broken `no_cross_feature` stub, which
was a `forbidden` contract with identical `source_modules` and
`forbidden_modules`; `independence` is the correct contract type for
mutual isolation.

`api` and `adapters` are siblings — both are adapters in the pattern, and
neither may import the other. In import-linter's layer syntax `|`
separates **independent** siblings (mutual imports forbidden); `:`
separates siblings that *may* import each other. `|` is the one we want —
this was confirmed by experiment, not read from the docs.

`ports` sits **below** `services`, not above. `BOUNDARIES.md:22` currently
grants `ports/ → domain/`, which combined with `services → ports` is the
very cycle `BOUNDARIES.md:31` forbids. Ports hold interfaces and depend
only on `models/` and `common/`; the domain imports them. `BOUNDARIES.md`
§2 must be corrected accordingly.

`models` sits at the bottom above `common` so that `services`, `ports`,
and `adapters` may all reference entities, while entities themselves stay
ignorant of behaviour and interfaces — `models → services` and
`models → ports` are both violations. `api → models` is permitted: inbound
port signatures carry entities, and forbidding it would mandate a DTO
mapping layer `BOUNDARIES.md` does not currently require.

Verified behaviour, single service (`containers = ["src.svc"]`):

| Edge | Expected | Result |
| --- | --- | --- |
| conforming skeleton (6 packages) | pass | KEPT |
| `services → adapters` | fail | BROKEN |
| `ports → services` | fail | BROKEN |
| `models → services` | fail | BROKEN |
| `models → ports` | fail | BROKEN |
| `api → services` | fail | BROKEN (forbidden contract) |
| `api → adapters` | fail | BROKEN (independent siblings) |

Verified multi-service (`containers = ["src.orders", "src.billing"]`,
both services fully populated):

| Edge | Expected | Result |
| --- | --- | --- |
| conforming, two services | pass | all 3 contracts KEPT |
| `orders.services → billing.services` | fail | independence BROKEN |
| `orders.services → orders.adapters` | fail | layers BROKEN |

Note the second row: the layers contract stayed KEPT on the cross-service
import. Layers apply *within* each container and say nothing about
service-to-service edges — the `independence` contract is what catches
those, and omitting it leaves cross-service coupling unenforced.

Note for adopters: the composition root that wires adapters into services
must live outside all five packages (e.g. `src/main.py`), or it will trip
the sibling rule. Say so in the file's header comment.

## Increments

Each increment is independently demonstrable and starts with failing
tests. Payload edits land for **all three agents in lockstep**; run
`pytest -k parity` plus `tests/test_agent_skills.py` before each commit.
Scope `ruff` to changed files only (`fix = true` is on).

### 1. Anti-drift test for layer vocabulary (test-first) — #77

1. New `tests/test_layer_vocabulary.py`, failing on `main`:
   - collect the layer names asserted by `BOUNDARIES.md` §1 and §2,
     `REPO_STRUCTURE_README.md`'s tree, each stack's `TECH_STACK.md` and
     `LAYER_IMPLEMENTATION.md`, `importlinter-reference.toml`'s `layers`,
     and `cli/skill_context.py::_STYLE_LAYERS["hexagonal"]`
   - assert all sources agree on the six names
   - assert no backend doc references a top-level `domain/` package
   - assert no source declares a `use_cases/` folder
   - assert `common/` is not described as holding data models
2. Confirm it fails, naming `BOUNDARIES.md`, `LAYER_IMPLEMENTATION.md`,
   `ARCH_CONTRACT.md`, and `REPO_STRUCTURE_README.md`.

Commit: `test(docs): assert one hexagonal layer vocabulary across payload`

### 2. Correct the outlier docs — #77

1. `BOUNDARIES.md`: §1 lists all six packages; §2's table replaces
   `domain/` with `services/`, adds `models/`, and drops `ports/ → domain/`
   (see cycle note above); §3-§4 prose follows.
2. `LAYER_IMPLEMENTATION.md:29` (baseline + all 7 stacks): `src/services/`,
   `src/models/`, agreeing with its own `:17` diagram.
3. `ARCH_CONTRACT.md` §2: state the domain path explicitly — "Domain Core:
   `services/` (behaviour), `models/` (entities)" — and drop `use_cases`.
4. `REPO_STRUCTURE_README.md`: add `models/` to the tree and folder table;
   `common/` becomes "shared utilities".
5. `TECH_STACK.md` (all 7 stacks): add `models/` to the layer block.
6. Increment 1's test passes.

Commit: `docs(backend): standardize domain on services/ + models/ (#77)`

### 3. Point skill context at both domain packages

1. Failing test in `tests/test_skill_context.py`: the `hexagonal` style's
   `domain` hint is `["services/", "models/"]`.
2. Update `cli/skill_context.py::_STYLE_LAYERS["hexagonal"]`; adjust the
   existing expectations at `tests/test_skill_context.py:413` and
   `tests/test_rule_templating.py:35,52`.

Leaving this at `["services/"]` would recreate the same
docs-disagree-with-code split this plan exists to close. Scope `ruff` to
`cli/skill_context.py` only.

Commit: `fix(cli): include models/ in hexagonal domain layer hint (#77)`

### 4. Detect the documented `src/<package>/` layout

1. Failing tests in `tests/test_detect.py`, asserting
   `build_profile(...).detected_architecture_signals == ["hexagonal-shape"]`
   for:
   - `src/mypkg/{api,ports,services,models,adapters,common}` (documented, N=1)
   - `src/{orders,billing}/{…}` (multi-service)
   and that the existing flat `src/{…}` case still passes.
2. Extend `_top_level_folder_names` (`cli/detect.py:370-382`) to scan one
   level below `src/` — collect the union of each child package's folder
   names. Keep the existing roots so flat layouts are unaffected.
3. Assert the downstream effect: `build_skill_context` on the documented
   layout yields `style: hexagonal` with populated layers, not
   `style: unknown` with empty ones.

Bound the walk: only direct children of `src/`, skipping dot-dirs and the
existing skip set, so this cannot become a full-tree scan on a large repo.
Scope `ruff` to `cli/detect.py` only.

Commit: `fix(cli): detect hexagonal shape under src/<package>/ (#77)`

### 5. Template codex rule destinations on the source root

1. Failing test: applying `codex` to a target whose code is at
   `src/mypkg/services/` must not create a root-level `services/`
   directory.
2. Give the codex manifest's path-scoped rule entries a destination
   templated on the resolved source root, the way
   `cli/rule_templating.py` already templates claude-code and copilot
   globs from `skill_context.layers`. Fall back to today's root-relative
   destination when the layout is unknown, so no install regresses.
3. Parity check: claude-code and copilot must stay glob-based
   (`**/services/**`) — this increment brings codex *toward* them, it does
   not change their shape.

This is placement only. `AGENTS.md` merge behaviour is already correct
(see Decision) and must not change — the test should assert user content
outside the govkit block still survives.

Commit: `fix(codex): place path-scoped rules at the real source root (#77)`

### 6. Fixture-backed contract test (test-first) — #75

1. New `tests/test_importlinter_reference.py`, marked `e2e` (it shells out
   to `lint-imports`), failing on `main`:
   - build a conforming `src/<pkg>/` six-package skeleton in `tmp_path`,
     write the shipped reference contract into a `pyproject.toml` with
     `containers` pointed at that package, run `lint-imports`, assert
     **exit 0**
   - for each of `services → adapters`, `ports → services`,
     `models → services`, `models → ports`, `api → services`,
     `api → adapters`: add that import, assert **non-zero exit** and the
     offending edge in stdout
   - multi-service case: two populated service packages, assert the
     conforming pair passes and that a cross-service import breaks the
     `independence` contract
2. Confirm every case fails today (the conforming case crashes on the
   invalid table form; the violation cases pass when they must not).

Add `import-linter` to the `[test]` extra in `pyproject.toml` so CI has it.

Commit: `test(governance): run import-linter against the shipped reference`

### 7. Rewrite the reference contract — #75

1. Replace `governance/backend/importlinter-reference.toml` with the
   Target design block. Rewrite the header comment: correct the
   `[[...contracts]]` copy instruction, drop the "flow inward" line, spell
   out that `containers` must name the service package(s), and add the
   composition-root note.
2. Replace the broken `no_cross_feature` stub with the commented
   `independence` block.
3. Increment 6's test passes.

Commit: `fix(governance): correct import-linter layer contract (#75)`

### 8. Remove the duplicate copy

1. Test asserting `pyproject.toml` carries no `[tool.importlinter]`
   section (govkit's source is `cli/`; the contract is inert here and only
   invites drift).
2. Delete `pyproject.toml:109-127`, leaving a one-line comment pointing at
   `governance/backend/importlinter-reference.toml` as the single copy.

Commit: `chore: drop inert import-linter duplicate from pyproject (#75)`

## Verification

- `./run_tests` after each increment; `./full_test` before the PR (the
  increment 6 test is `e2e`-marked and excluded from the fast loop).
- `pytest -k parity` and `tests/test_agent_skills.py` after any payload edit.
- Regenerate smoke sandboxes — `.\scripts\smoke.ps1 -Agents claude-code
  -Levels 4 -Force`, plus one `codex` run for increment 5 — and confirm the
  emitted `governance/backend/importlinter-reference.toml` matches and no
  stray root-level `services/` appears. `scripts/projects/` is gitignored
  (`.gitignore:109`), so these are regenerated, never edited.
- Increments 3, 4 and 5 change `cli/` behaviour but add no bundled asset,
  so `wheel-smoke` is unaffected; increments 6 and 8 touch `pyproject.toml`
  but not `force-include`.
- Increment 5 is the highest-risk change (install destinations). Verify a
  legacy flat-layout target still installs exactly as it does today before
  and after.

## Out of scope — file separately

- **L3 ships a boundary gate with no contract.**
  `ci/github/l3-quality-gate.yml` and `ci/azure/l3-quality-gate.yml` run a
  `boundary-check` job that pip-installs import-linter and runs
  `lint-imports`, but `governance/backend/` ships only at L4+ (manifest
  `level_4`/`level_5`, types `api`/`cli`). An L3 install therefore gets a
  CI job with nothing to enforce. Either ship the reference at L3 or drop
  the job from the L3 gate.
- **`doctor` skips nested installs** (#78). Directly relevant now that
  backend+frontend monorepos are the sanctioned way to run two project
  types: a governed root plus `apps/web` means the nested install is never
  validated unless `--target` names it.
- **`skill_context.yaml` has no multi-service shape.** `source_root` is a
  single string and `layers` a single hint set. For
  `src/{orders,billing}/` there is no way to say "two trees". Increment 4
  makes detection *fire* for that layout, but the emitted context still
  describes one service. Needs a schema decision.
- **No `--force` warning for edits inside the `AGENTS.md` govkit block.**
  Tested, and there is **no data-loss defect** — an earlier suspicion that
  the block was replaced without protection was wrong:

  | Edit location | plain `upgrade` | `upgrade --force` |
  | --- | --- | --- |
  | inside the `AGENTS.md` govkit block | survived | replaced, no warning |
  | governed doc (`BOUNDARIES.md`) | survived | replaced, with warning |

  (Plain `upgrade` no-ops when the marker version already matches, which is
  what hid this — the row above needs the marker aged to an older version
  to exercise a real upgrade.)

  The only gap is the missing warning: governed docs print
  `warning: overwriting user edits … (--force set)`, the block prints
  nothing. Defensible, since the block tells the reader in-file to put
  their own instructions outside it — unlike governed docs, which teams are
  expected to customise. A one-line warning, not a design change; filed
  separately as an enhancement.
