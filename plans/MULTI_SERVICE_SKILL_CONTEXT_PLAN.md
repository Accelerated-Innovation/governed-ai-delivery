# Multi-Service Skill Context Plan

**Status:** Implemented — 2026-08-03, all increments. Derived `source_root`
(#117), `services` + per-service codex rules + doctor D018 (#118), planning
skills that ask which service, and the docs. Closes #86.

One increment was not in the plan. **2b** came out of increment 2's
end-to-end run, which found that codex's path-scoped rules governed no code
in a multi-service repo and that the folders they created made every later
reading of the repo see a flat single-service layout. That would have made
increment 3 unsafe — a skill taught to read a field that erases itself.

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

### 2b. Codex rules scope to each service — done

Not in the original plan. Increment 2's end-to-end run surfaced two defects
in codex's path-scoped rule placement, and the second of them would have
made increment 3 unsafe.

1. Failing tests in `tests/test_path_scoped_rules.py`: a multi-service
   install puts every path-scoped rule under each service and none at the
   repo root; single-source-root and unrecognisable layouts install exactly
   as before; the service list survives an `upgrade`.
2. `resolve_path_scoped_dests` gains one branch — no single root **and**
   services detected → one destination per service.
3. Doctor **D018** names rules left where govkit no longer writes them.
4. `_layer_root_candidates` stops counting govkit's own folders at the
   target root.

**What the rules were doing before.** In a `src/{orders,billing}/` repo
there is no single source root, so destinations stayed root-relative and
`apply` wrote `api/AGENTS.md`, `ports/AGENTS.md`, `services/AGENTS.md`,
`adapters/AGENTS.md` and `security/AGENTS.md` at the repo root. Codex
resolves `AGENTS.md` upward from the file being edited, so
`src/orders/api/handlers.py` reaches the top-level `AGENTS.md` and never the
root `api/AGENTS.md`. Verified on a real install: **no `AGENTS.md` anywhere
under either service.** Five files governing nothing — the same defect
`resolve_path_scoped_dests` was written to fix for `src/<package>/`, left
unfixed for the multi-service shape.

**Nothing is removed.** `write_managed_agent_block` already replaces a file
wholesale only when it can prove the file is govkit's own — byte-identical
to the body, or untouched since `applied_at` — and otherwise appends its
block below the team's content. Confirmed with a real apply against a
hand-written root `AGENTS.md` and a hand-written root `api/AGENTS.md`: both
kept their content, each with one govkit block. Fan-out changes only where
the *next* write goes, and adds no delete path.

D018 reports what is left behind, with different advice per case, because
govkit cannot know which it is until it looks:

| Left at the root | Advice |
| --- | --- |
| holds only govkit's block | safe to delete, and names the live locations |
| holds the team's content too | leave the file; the block inside it is stale |

This deliberately does **not** follow `reconcile_legacy_instruction_files`,
which deletes. That function deletes because leaving its file makes the
agent load governance *twice* — actively contradictory. A stale root
`api/AGENTS.md` here governs nothing, so it is inert clutter. Different
hazard, different remedy.

**The migration was the part that nearly shipped broken.** The first draft
fixed fresh installs and did nothing for existing ones: the root folders an
earlier govkit created made `_layer_root_candidates` match at the target
root, so `detect_services` returned `[]` for ever. The fan-out could never
fire on the installs that needed it, and **D018 could never fire at all** —
a check that cannot fail, which is the thing this repo has learned to look
for. Only the end-to-end replay of a pre-fan-out install caught it; every
unit test was green.

The fix is that a folder holding nothing but a govkit-authored `AGENTS.md`
is govkit's artifact, not a source layer — discounted **only at the target
root**. That scoping is load-bearing. govkit creates layer folders in
exactly one place: the root, when it could not detect a source root.
Everywhere else it writes into folders the team already had. Discounting at
`src/<pkg>/` would drop the source root of a greenfield install whose layer
folders hold only the rules govkit just wrote, sending the next run's rules
back to the repo root — pinned by
`test_a_greenfield_package_layout_does_not_relocate_itself`.

Verified: `apply` twice is idempotent on all four layouts; a pre-fan-out
install upgrades to per-service rules, keeps its team-authored root file
intact, keeps its service list, and gets one D018 per stale location with
the right advice for each.

Commit: `fix(cli): scope codex path-scoped rules to each service (#86)`

### 3. Skills ask which service — done

1. Failing test in `tests/test_agent_skills.py`: `spec-planning` and
   `implementation-plan` instruct the agent to check
   `architecture.services` and, when several are present and the request
   names none, to ask before planning.
2. Edit the three agents' copies in lockstep; frontmatter stays byte-identical.

Two things beyond the plan as written:

- **Naming the service is not enough.** The section also requires the
  chosen service's `root` to prefix every path in the output. Without it a
  plan says `services/pricing.py`, which is a folder that does not exist in
  a repo whose only services folders are `src/orders/services/` and
  `src/billing/services/`. Pinned by a test asserting the section shows a
  scoped path.
- **Placed before the inputs section, not appended.** The question has to be
  resolved before planning starts. That position also keeps the block
  extractable for the parity test — the next heading is `## `, so the
  comparison covers the section and nothing after it. Appending would have
  swallowed the trailing `### Data projects` note in the spec-planning
  files, and the parity test would have failed for a reason that had
  nothing to do with the section.

UI copies deliberately untouched, with a test asserting they stay that way.

Commit: `feat(skills): scope planning to one service in multi-service repos (#86)`

### 4. Documentation — done

1. `docs/backend/architecture/REPO_STRUCTURE_README.md`: the multi-service
   shape and what `skill_context` says about it.
2. Cross-reference the import-linter reference's `containers` guidance, which
   already documents the same layout from the enforcement side.

The cross-reference runs both ways: the reference file now points at
`architecture.services` as the place the container names are already
recorded, so an adopter copies them rather than working them out.

`REPO_STRUCTURE_README.md` is **stack-agnostic**, so it must not name a
boundary tool — `tests/test_layer_vocabulary.py` enforces that and the doc
is in its scanned set. The boundary bullet therefore describes what the
reference contract does and defers to `TECH_STACK.md` for which tool this
stack uses, per the convention #104 established. Worth recording because
the obvious draft named the tool and would have failed the check.

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

### ~~Codex's path-scoped rules break multi-service repos~~ — closed by 2b

Both defects are fixed: the rules fan out per service, and govkit no longer
reads its own root-level folders as architecture. Doctor D018 names what an
earlier install left behind. Kept as a pointer because the reasoning that
found them is worth keeping: unit tests were green across every layout while
codex, one of three agents, got none of the feature.

### Should doctor name skipped sibling packages? — tracked as #120

Open question 3's remaining half, deliberately left out of 2b. A team reading
`services: [orders, billing]` cannot tell whether that is the whole repo.

The obvious version is wrong: flagging every unlisted directory under `src/`
would fire on `src/utils/`, `src/config/` and every shared package, which is
noise, not honesty. A useful check needs a definition of "near miss" —
plausibly a package holding *at least one* architecture-layer folder but too
few to match a fingerprint, which is the case where govkit almost listed it
and a team would be surprised it did not.

That definition needs deciding before the check is written, which is why 2b
shipped without it. Lifted into **#120** rather than left here, since an open
question inside a plan marked Implemented is where things go to be forgotten.

### Codex and copilot planning skills assume hexagonal — #119

Found while adding increment 3's section and deliberately not fixed there.
claude-code's copies of `spec-planning` and `implementation-plan` read
`architecture.layers`; codex's and copilot's name `ports/inbound/`,
`services/` and `adapters/` outright. On a Clean or layered repo — where
govkit correctly records `Presentation/`, `Application/`, `Infrastructure/` —
two of three agents plan against folders that do not exist.

The parity suite cannot see it: it pins frontmatter plus a few named
sections, and skill bodies are otherwise free to differ.

### D018 covered only half of what it was shaped for — closed by #83

D018 shipped in 2b asking "are there services?" when the question it needed
was "does govkit still write to this location?". The single-source-root
relocation (#82, `api/AGENTS.md` -> `src/api/AGENTS.md`) is the same defect
and went unreported, which is how **#83** stayed open after the check landed.

It now asks `resolve_path_scoped_dests` — the same function that decides
placement — so the check covers every layout that relocates rules and stays
quiet for every layout that does not, with a completeness test over all five.

Worth recording as a shape: a check guarded by *one cause* of a condition
rather than by the condition itself will miss the other causes, and look
correct doing it.

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
