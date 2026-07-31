# Hexagonal Layer Vocabulary and Boundary Contract Plan

Settle one canonical name for the backend domain layer across the whole
payload, and replace `governance/backend/importlinter-reference.toml`
with a contract that actually enforces `BOUNDARIES.md`. Closes #77 (the
name) and #75 (the contract). The two are one decision: the contract's
`layers` list cannot be written until the layer name is fixed.

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

### 3. A second, divergent copy exists

`pyproject.toml:109-127` carries the same broken contract in govkit's own
repo, labelled "a reference template for target projects". It is inert
here — govkit's source is `cli/`, not `src/`, and no workflow runs
`lint-imports` against this repo — which is precisely why it rotted
unnoticed. Two copies, no test, no consumer.

Nothing in `agents/`, `docs/`, `governance/`, `ci/`, or `cli/` references
`importlinter-reference.toml` by name.

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

### Deferred sub-decision (not in scope)

`ARCH_CONTRACT.md:19` says the domain contains `services`, `models`, and
`use_cases`; `REPO_STRUCTURE_README.md:46-50` has no `models/` or
`use_cases/` and files "data models" under `common/`, while
`BOUNDARIES.md:14` scopes `common/` to "logging, tracing, DTOs". Where
domain entities live is a real ambiguity, but it is separable from the
layer *name* and would widen this change considerably. File as a
follow-up issue; do not resolve here.

## Target design

### Contract (verified against import-linter 2.11)

```toml
[tool.importlinter]
root_package = "src"

[[tool.importlinter.contracts]]
name = "Hexagonal Architecture"
type = "layers"
layers = ["api | adapters", "services", "ports", "common"]
containers = ["src"]

[[tool.importlinter.contracts]]
name = "API talks only to inbound ports"
type = "forbidden"
source_modules = ["src.api"]
forbidden_modules = ["src.services"]
```

`api` and `adapters` are siblings — both are adapters in the pattern, and
neither may import the other. In import-linter's layer syntax `|`
separates **independent** siblings (mutual imports forbidden); `:`
separates siblings that *may* import each other. `|` is the one we want —
this was confirmed by experiment, not read from the docs.

`ports` sits **below** `services`, not above. `BOUNDARIES.md:22` currently
grants `ports/ → domain/`, which combined with `services → ports` is the
very cycle `BOUNDARIES.md:31` forbids. Ports hold interfaces and depend
only on `common/`; the domain imports them. `BOUNDARIES.md` §2 must be
corrected accordingly.

Verified behaviour of the config above:

| Edge | Expected | Result |
| --- | --- | --- |
| conforming skeleton | pass | KEPT |
| `services → adapters` | fail | BROKEN |
| `ports → services` | fail | BROKEN |
| `api → services` | fail | BROKEN (forbidden contract) |
| `api → adapters` | fail | BROKEN (independent siblings) |

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
   - assert all sources agree on the five names
   - assert no backend doc references a top-level `domain/` package
2. Confirm it fails, naming `BOUNDARIES.md` and `LAYER_IMPLEMENTATION.md`.

Commit: `test(docs): assert one hexagonal layer vocabulary across payload`

### 2. Correct the two outlier docs — #77

1. `BOUNDARIES.md`: §1 lists `api/ ports/ services/ adapters/ common/`;
   §2's table replaces `domain/` with `services/` and drops
   `ports/ → domain/` (see cycle note above); §3-§4 prose follows.
2. `LAYER_IMPLEMENTATION.md:29` (all 7 stacks): `src/services/`,
   agreeing with its own diagram.
3. `ARCH_CONTRACT.md` §2: state the domain path explicitly —
   "Domain Core: `services/`" — closing the root gap.
4. Increment 1's test passes.

Commit: `docs(backend): standardize domain layer on services/ (#77)`

### 3. Fixture-backed contract test (test-first) — #75

1. New `tests/test_importlinter_reference.py`, marked `e2e` (it shells out
   to `lint-imports`), failing on `main`:
   - build a conforming five-package skeleton in `tmp_path`, write the
     shipped reference contract into a `pyproject.toml`, run
     `lint-imports`, assert **exit 0**
   - for each of `services → adapters`, `ports → services`,
     `api → services`, `api → adapters`: add that import, assert
     **non-zero exit** and the offending edge in stdout
2. Confirm all five cases fail today (the conforming case crashes on the
   invalid table form; the violation cases pass when they must not).

Commit: `test(governance): run import-linter against the shipped reference`

### 4. Rewrite the reference contract — #75

1. Replace `governance/backend/importlinter-reference.toml` with the
   Target design block. Rewrite the header comment: correct the
   `[[...contracts]]` copy instruction, drop the "flow inward" line, and
   add the composition-root note.
2. Increment 3's test passes.

Commit: `fix(governance): correct import-linter layer contract (#75)`

### 5. Remove the duplicate copy

1. Test asserting `pyproject.toml` carries no `[tool.importlinter]`
   section (govkit's source is `cli/`; the contract is inert here and only
   invites drift).
2. Delete `pyproject.toml:109-127`, leaving a one-line comment pointing at
   `governance/backend/importlinter-reference.toml` as the single copy.

Commit: `chore: drop inert import-linter duplicate from pyproject (#75)`

## Verification

- `./run_tests` after each increment; `./full_test` before the PR (the
  increment 3 test is `e2e`-marked and excluded from the fast loop).
- `pytest -k parity` and `tests/test_agent_skills.py` after any payload edit.
- Regenerate smoke sandboxes — `.\scripts\smoke.ps1 -Agents claude-code
  -Levels 4 -Force` — and confirm the emitted
  `governance/backend/importlinter-reference.toml` matches. `scripts/projects/`
  is gitignored (`.gitignore:109`), so these are regenerated, never edited.
- No `cli/` behaviour changes in increments 1-4, so `wheel-smoke` is
  unaffected; increment 5 touches `pyproject.toml` but not `force-include`.

## Out of scope — file separately

- **L3 ships a boundary gate with no contract.**
  `ci/github/l3-quality-gate.yml` and `ci/azure/l3-quality-gate.yml` run a
  `boundary-check` job that pip-installs import-linter and runs
  `lint-imports`, but `governance/backend/` ships only at L4+ (manifest
  `level_4`/`level_5`, types `api`/`cli`). An L3 install therefore gets a
  CI job with nothing to enforce. Either ship the reference at L3 or drop
  the job from the L3 gate.
- Domain entity placement (`models/` / `use_cases/`) — see Deferred
  sub-decision.
- `cli/detect.py:54` `_HEXAGONAL_FOLDERS = {"ports", "adapters"}` never
  inspects the domain folder, so layer hints are never reconciled against
  disk — tracked in #76.
