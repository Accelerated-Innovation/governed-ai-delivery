# Multi-Service Skill Context Plan

**Status:** In progress — 2026-08-03. Covers #86. Increments 1–2 done
(derived `source_root`, `services`); increments 3–4 not started.

**Increment 3 is blocked** on a decision recorded under Follow-ups: codex's
own path-scoped rules make a multi-service repo look single-service, so the
`services` list survives `apply` but not a later `upgrade`. Teaching the
skills to read a field that erases itself would be worse than not shipping
it.

Give `.govkit/skill_context.yaml` an honest source root and a way to say
"this repo holds several services", so a skill can scope its work to one of
them.

Everything asserted below about what govkit writes was produced by running
`govkit apply` against three real layouts and reading the emitted file — see
the table in Motivation §1.

## Motivation (evidence)

### 1. `source_root` is wrong for two of the three layouts govkit supports

`cli/skill_context.py:296` hardcodes it:

```python
derived = {
    "style": style,
    "source_root": "src/",          # never derived from the repo
    "layers": deepcopy(...),
}
```

Meanwhile `cli/detect.py::detect_source_root` computes the real one. The two
never meet. Applied to three skeletons:

| Layout | `skill_context.source_root` | `detect_source_root()` | Verdict |
| --- | --- | --- | --- |
| `src/{api,ports,…}` (flat) | `src/` | `src` | right, modulo the trailing slash |
| `src/mypkg/{api,ports,…}` | `src/` | `src/mypkg` | **wrong** |
| `src/{orders,billing}/{…}` | `src/` | `""` | **wrong** |

The middle row is the layout `docs/backend/architecture/REPO_STRUCTURE_README.md`
prescribes as canonical, and the one the shipped import-linter contract is
written for (`containers = ["src.myservice"]`). So the field is wrong for the
documented single-service case, not only for the multi-service case #86
reports.

### 2. Nothing reads it

Searched `cli/`, `agents/`, `docs/`, `governance/`, `extensions/`, `features/`
and `tests/`:

| Consumer | Reads `source_root`? |
| --- | --- |
| `cli/rule_templating.py` | no — expands `architecture.layers` only |
| `cli/install_common.py` | no — calls `detect_source_root()` directly |
| the two planning skills | no — read `architecture.style` and `.layers` |
| any doc, rule, extension or feature | no |
| `SkillContext.source_root` | populated by the loader, read by nobody |

So today the wrong value is inert. That is *why* it went unnoticed, and it is
the reason to fix the representation before a consumer arrives rather than
after.

### 3. `layers` survives multi-service by accident

`rule_templating` turns each hint into `**/<hint>/**`, which matches at any
depth. `src/orders/services/` and `src/billing/services/` both match
`**/services/**`, so rule scoping is correct in a multi-service repo today —
correct, but for a reason nothing states and nothing tests. It also means
rule scoping cannot distinguish the two services, which is fine for rules
(the same rules apply to both) and not fine for a skill asked to build a
feature in one of them.

### 4. Two notions of "source root" already exist

`detect_source_root()` returns `""` for the multi-service layout on purpose,
documented as: callers "fall back to root-relative destinations rather than
guessing which service a rule belongs to". That is the right answer for codex
rule placement and it is the same question #86 asks, answered once already,
in a function `skill_context` does not call.

Virtues: **Honest** (the file describes the repo it is in), **Unique** (one
notion of where the source lives).

## Decision

**Derive `source_root`, and add `services` only for the case the flat fields
cannot express.**

```yaml
architecture:
  style: hexagonal
  source_root: src/orders        # "" when several services — see below
  layers:
    domain: [services/, models/]
  services:                      # absent when there is one service
    - name: orders
      root: src/orders
    - name: billing
      root: src/billing
```

Three properties, each chosen against an alternative:

- **`source_root` is derived from `detect_source_root()`**, not hardcoded.
  `""` becomes meaningful: *no single root*, which is the honest answer for a
  multi-service repo and already the convention that function uses. The
  alternative — deleting the field, since nothing reads it — was rejected
  because the two planning skills are the consumers this plan then teaches to
  use it, and because a published context file that omits where the code
  lives is a strange thing to hand a skill.

- **`services` is absent for the single-service case**, so every existing
  file stays valid and the common case stays a two-line read. The
  alternative — always emit `services` with one entry and drop the flat
  `source_root` — is cleaner on paper and breaks every reader for a case that
  is the overwhelming majority.

- **`layers` stays relative and shared.** All services in one install share a
  type, a stack and therefore a layout; per-service layer maps would express
  a difference that cannot exist. This is settled by #82's rule: services
  differing in `type`, `stack` or `level` need **separate installs**, so one
  install's services differ only by package name.

**Skills ask when it is ambiguous.** #86's third question — what a skill does
when several services exist and the request names none — needs no schema
support. With `services` present and more than one entry, the planning skills
name them and ask which. That is a payload change, not a CLI one.

## Target design

### Derivation

`build_skill_context` calls `detect_source_root(target)` for `source_root`,
and a new `detect_services(target)` for the list. Both walk the same
candidate roots `detect_source_root` already walks, so multi-service
detection costs no extra traversal — the function already builds the
candidate list and discards it when `len(candidates) != 1`.

| Layout | `source_root` | `services` |
| --- | --- | --- |
| `src/{api,…}` | `src` | absent |
| `src/mypkg/{api,…}` | `src/mypkg` | absent |
| `src/{orders,billing}/{…}` | `""` | two entries |
| unrecognisable | `""` | absent |

The last two rows both carry `source_root: ""`, distinguished by whether
`services` is present. A skill reading `""` with no `services` knows govkit
could not tell, which is different from knowing there are three services.

### Team edits

`source_root` is already in `_TEAM_TUNABLE_ARCHITECTURE`, so the provenance
mechanism preserves a corrected value and refreshes an untouched one with no
change. `services` joins it on the same terms: a team that lists services
govkit did not detect keeps that list.

This is also the first tunable field whose *derived* value changes for
existing installs. An install written before this change records
`source_root: src/` in `_govkit_generated`; after it, the derived value may
be `src/mypkg`. Because the live value also reads `src/`, provenance sees no
edit and refreshes it. That is the desired outcome and it must be tested,
because the same mechanism would silently discard a team's edit if the
comparison were the other way around.

### What `SkillContext` gains

```python
@dataclass
class ServiceRef:
    name: str
    root: str

@dataclass
class SkillContext:
    ...
    services: list[ServiceRef] = field(default_factory=list)
```

Empty list for single-service, so `if ctx.services:` reads as "is this a
multi-service repo".

## Increments

Each is independently demonstrable and starts with failing tests. Payload
edits land for **all three agents in lockstep**; run `pytest -k parity`.

### 1. Honest `source_root` — done

1. Failing test in `tests/test_skill_context.py`: an applied install's
   `architecture.source_root` equals `detect_source_root(target)` for the
   flat, nested and multi-service layouts.
2. Replace the hardcoded `"src/"` with the derived value.
3. Assert the provenance interaction explicitly: an install whose live and
   recorded values both read `src/` picks up the newly-derived root; one
   whose live value was hand-edited keeps it.

No new representation — this alone makes the file stop lying, and is
revertible on its own.

Two things the increment settled beyond the plan as written:

- **The loader's default moved too.** `load_skill_context` defaulted a
  missing or malformed `source_root` to `"src/"`, which is the same
  fabrication on the read side: a file that never says where the code lives
  does not license the loader to name a directory. It now returns `""` —
  the "govkit cannot tell" the derivation uses.
- **Three of the five test layouts derive `""`**, so a table asserting only
  `emitted == detect_source_root(target)` would pass against a derivation
  that returned `""` unconditionally. The layouts carry written-out expected
  values, and a completeness test asserts the table still distinguishes
  three distinct answers rather than collapsing or emptying.

Verified against real `govkit apply` runs over 5 layouts × 3 agents, diffed
against the same runs from `main`. **The only bytes that change anywhere in
an installed tree are the two `source_root` lines** — the live field and the
provenance record. Rule globs, skill templating, codex's `AGENTS.md`
placement and doctor's output are all identical, which is the
"`rule_templating` is unchanged" item under Verification, measured rather
than argued.

The migration was checked on real installs produced by pre-change code, via
both `apply` and `upgrade`: an untouched `src/` becomes `src/mypkg`, a
hand-edited `services/` survives. (`upgrade` no-ops when the marker's
version already matches the running govkit, so that check needs a marker
recording an older version — otherwise it silently proves nothing.)

Commit: `fix(cli): derive skill_context source_root from the repo (#86)`

### 2. `services` in the emitted context — done

1. Failing test: the multi-service layout emits two `services` entries with
   the right names and roots; single-service layouts emit none.
2. `detect_services()` in `cli/detect.py`, wired into `build_skill_context`,
   added to `_TEAM_TUNABLE_ARCHITECTURE`.
3. `ServiceRef` and `SkillContext.services` in the loader, with the same
   defensive coercion the other fields get — a hand-edited `services:` that
   is a scalar, or holds non-dict entries, must not crash
   `load_skill_context`.

Built on `_layer_root_candidates()`, per open question 1's answer: one walk,
two readings. `detect_services` filters that list to candidates whose parent
is `src/` or `Source/`, which is what stops `src/` itself — a source root
holding the layers directly — from being reported as a service named "src".

Three things the increment settled:

- **Provenance needed a third case.** It compared a live value against the
  record and preserved it when they differed, skipping any key the record
  did not hold. `services` is the first field govkit writes only
  *sometimes*, so a team listing services in a repo govkit reads as
  single-service had no record entry to differ from, and their list was
  dropped on the next write. A live key with no record entry now reads as
  "govkit did not write this", which is the general form of the rule the
  other three fields never needed.
- **`services` is absent, never `[]`.** An empty list would erase the
  distinction between "three services" and "govkit could not read this
  repo", which both otherwise carry `source_root: ""`.
- **Non-conforming siblings are omitted** — open question 3, answered by
  doing: `src/legacy/` beside two real services is not listed, and one
  conforming package beside a non-conforming one is the single-service case.
  The omission is still silent, which is the part left open.

**The end-to-end run found a defect the unit tests could not.** Codex places
a path-scoped `AGENTS.md` inside each layer folder, and for a multi-service
repo — where there is no single source root — those destinations stay
root-relative, so `apply` *creates* root-level `api/`, `ports/`, `services/`
and `adapters/`. `write_skill_context` runs after that, so re-deriving read
the repo as flat single-service and emitted no services at all. Codex, one
of three agents, silently got none of this feature.

The cause is that `source_root` and `services` were observed at a different
moment from `style` and `detected_signals`, which come from a `RepoProfile`
built during stack selection, before a byte is written. Both now live on
that profile, so all four facts describe the same repo — the team's, not the
one govkit just modified. Increment 1 had the same split and got away with
it: its value was `""` before and after.

Verified with real `govkit apply` over **7 layouts × 3 agents**, diffed
against the same runs from `main`: the only bytes that differ anywhere in
an installed tree are the `services` block, and codex now matches the other
two agents on every layout.

Commit: `feat(cli): describe multi-service repos in skill_context (#86)`

### 3. Skills ask which service

1. Failing test in `tests/test_agent_skills.py`: `spec-planning` and
   `implementation-plan` instruct the agent to check
   `architecture.services` and, when several are present and the request
   names none, to ask before planning.
2. Edit the three agents' copies in lockstep; frontmatter stays byte-identical.

Commit: `feat(skills): scope planning to one service in multi-service repos (#86)`

### 4. Documentation

1. `docs/backend/architecture/REPO_STRUCTURE_README.md`: the multi-service
   shape and what `skill_context` says about it.
2. Cross-reference the import-linter reference's `containers` guidance, which
   already documents the same layout from the enforcement side.

Commit: `docs(backend): document the multi-service skill context (#86)`

## Verification

- `./run_tests` after each increment; `./full_test` before the PR.
- `pytest -k parity` after any skill edit — three agents, in lockstep.
- Apply against all three layouts and read the emitted file, not just the
  unit tests. Increment 1's whole subject is a value that unit tests have
  been asserting as `src/` for as long as it has been wrong.
- Confirm an install created **before** this change picks up the corrected
  root on the next apply, and that a hand-edited root survives it.
- Confirm `rule_templating` output is unchanged for every layout: the layer
  globs are depth-agnostic and must stay that way, or multi-service rule
  scoping regresses while the context file gets better.

## Open questions

1. ~~**Does `detect_services` belong in `detect.py` or should
   `detect_source_root` return both?**~~ **Neither — extract the shared
   candidate walk, keep two thin public functions over it.** Answered
   2026-08-03, before increment 1.

   The question as posed prices the wrong thing. The "second traversal" is
   `Path.iterdir()` on `src/`, `Source/` and each direct child — no
   recursion, once per install. Increment 1 measured it at nothing
   noticeable against a `govkit apply` that copies a hundred files. Saving
   it is not a reason to widen a signature.

   The real argument for one pass is **Unique**: the invariant binding the
   two answers — `source_root` is `""` exactly when the candidate list does
   not hold one entry, and `services` is populated exactly when it holds
   more than one — has to live somewhere. Two independent walks can drift
   on a fingerprint, a skip-dir rule, or the `Source/` sibling, and nothing
   would notice.

   A `(root, services)` tuple buys that at a real cost: `install_common`
   wants one value, tuple returns invite positional-unpack mistakes, and
   the existing call site changes for no benefit to itself. A private
   `_layer_root_candidates(target) -> list[Path]` gets the same single
   source of truth with **no** caller changing. `detect_source_root` keeps
   its exact signature and behaviour; `detect_services` is a second thin
   reading of the same list.

   One wrinkle for increment 2 to settle: `detect_source_root` returns
   early when the layers sit at the target root, so a repo with both
   root-level layers *and* `src/{orders,billing}/` never builds a candidate
   list today. The helper has to decide whether that stays true — it
   probably should, since such a repo has no coherent answer — but it must
   be decided rather than inherited.
2. **Should `name` be the package name or a team-chosen label?** The package
   name is derivable and stable; a label is friendlier in skill output and
   needs somewhere to live. Recommend the package name, with the field
   tunable like everything else in the architecture block.
3. **Does anything need to stop a multi-service repo from having services
   with different shapes?** `src/orders/{api,…}` beside `src/legacy/` that is
   not hexagonal at all. **Half-answered by increment 2:** detection lists
   only the conforming packages, and that is right — `src/legacy/` is not a
   service govkit can say anything useful about, and one conforming package
   beside a non-conforming one is correctly the single-service case. Both are
   tested.

   What is still open is the part the original question worried about: the
   omission is silent. Nothing in the emitted file or in `doctor` says
   "there is a `src/legacy/` here that govkit did not list". A team reading
   `services: [orders, billing]` has no way to tell whether that is the whole
   repo. `doctor` is the natural place — it already reports what it examined
   — and this should be settled before increment 3 teaches skills to plan
   against the list.

## Follow-ups

### Codex's path-scoped rules break multi-service repos — blocks increment 3

Two defects with one cause, both found by running `govkit apply` rather than
by reading code. Neither is created by this plan; increment 2 is what made
them visible.

**1. The rules govern nothing.** In a `src/{orders,billing}/` repo,
`detect_source_root` returns `""`, so `resolve_path_scoped_dests` leaves
codex's destinations root-relative and `apply` writes `api/AGENTS.md`,
`ports/AGENTS.md`, `services/AGENTS.md`, `adapters/AGENTS.md` and
`security/AGENTS.md` at the repo root. Verified on a real install: there is
**no `AGENTS.md` anywhere under `src/orders` or `src/billing`**. Codex
resolves `AGENTS.md` upward from the file being edited, so a file at
`src/orders/api/handlers.py` finds the top-level `AGENTS.md` and never the
root `api/AGENTS.md`. Those five files govern no code at all.

This is the same defect `resolve_path_scoped_dests` was written to fix for
the `src/<package>/` layout, left unfixed for the multi-service one.

**2. They then hide the services.** Those root-level folders make
`_layer_root_candidates` match at the target root, so every later reading of
the repo sees a flat single-service layout. Increment 2 fixed `apply` by
observing before writing, but the folders are on disk permanently, so a
later `upgrade` — which builds its profile after the install — derives no
services and the list is dropped. Measured:

| Agent | after `apply` | after `upgrade` |
| --- | --- | --- |
| claude-code | 2 services | 2 services |
| codex | 2 services | **0** |
| copilot | 2 services | 2 services |

Nothing reads `services` yet, so the practical impact today is zero. That
stops being true at increment 3, which is why it blocks it: a skill taught
to read a field that erases itself on the next `upgrade` is worse than a
skill that does not know about services.

**Recommended fix: fan the path-scoped rules out per service.**
`src/orders/api/AGENTS.md` and `src/billing/api/AGENTS.md` rather than one
root copy. It puts the rules where codex will actually resolve them, and it
creates no root-level layer folders, so the detection problem disappears
with the defect that caused it. `detect_services` — which increment 2 adds —
is exactly what makes it expressible; `resolve_path_scoped_dests` grows one
branch. claude-code and copilot need no change: their `**/<layer>/**` globs
already match at any depth, which is the accident recorded in Motivation §3.

Two alternatives, both weaker. *Drop the path-scoped rules entirely for a
multi-service repo* — smaller, and removes only files that demonstrably do
nothing, but it leaves those services with no codex layer guidance. *Leave
it* — increment 3 then has to treat `services` as unreliable on one agent.

Either way, an install that already has the stale root folders keeps them:
govkit does not delete files it did not write in the user's tree. Worth
deciding whether `doctor` should name them.

## Out of scope

- **Per-service `type` / `stack` / `level`.** Settled by #82: services that
  differ in any marker option need separate installs. This plan describes
  services that differ only by package.
- **`marker.json`.** It records install options, not repo shape. Nothing here
  changes it.
- **Multi-service enforcement.** `governance/backend/importlinter-reference.toml`
  already ships a commented `independence` contract, and the
  dependency-cruiser reference ships one enabled. Both are per-tool concerns
  closed with #93.
- **UI and data types.** `ui-*` installs have no service packages, and the
  data types use dbt/medallion layering where "service" has no meaning.

  A review of increment 1 flagged that a dbt repo now emits
  `source_root: ""`, because `detect_source_root`'s fingerprints omit
  `_DBT_FOLDERS` and its candidate roots omit `models/`. Checked, and left
  alone deliberately:

  - **Not a regression.** Those repos previously got `src/`, a directory most
    dbt projects do not have. `""` — "govkit cannot tell" — is strictly more
    honest than the value it replaces.
  - **Not a codex-placement bug either.** `path_scoped` entries exist only
    under `variants.type.api` and `variants.type.cli` in all three manifests,
    so `resolve_path_scoped_dests` is a no-op for data installs and the
    omission never reached the function's original consumer.
  - **`""` may in fact be the right answer for dbt.** The `dbt-layered` hints
    already carry the prefix (`models/staging/`, `models/marts/`). A
    `source_root: models` beside them would make a consumer that joins the
    two produce `models/models/staging/`. Whether dbt has a source root
    *distinct from* its layer hints is a representation question for whoever
    writes the first data consumer, not a gap to patch ahead of one.

  The fix the review proposed — special-casing dbt inside
  `build_skill_context` — is the wrong shape regardless: it would create a
  second notion of where the source lives that disagrees with
  `detect_source_root`, which is the exact defect increment 1 removes. If
  `models/` ever becomes a recognised root, it belongs in that one function.
