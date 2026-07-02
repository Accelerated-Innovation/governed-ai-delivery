# Stack Metadata Unification Plan

Make `cli/stacks/<id>/overlay.yaml` the single owner of per-stack facts, as
`cli/overlay.py` already claims ("the single source of truth for resolving
stacks"). Two parallel code tables currently contradict that claim, and both
fail silently when a new stack is added without editing them.

## Motivation (evidence)

| Fact | Owner today | Duplicate | Failure mode when a new stack skips the table |
|---|---|---|---|
| Primary language | `skill_context.language` in all 7 overlay.yaml | `doctor._STACK_PRIMARY_LANGUAGE` (doctor.py:248) | D005 silently stops covering the stack |
| Supported `--type` shapes | — (code only) | `stack_select._STACK_SUPPORTED_TYPES` (stack_select.py:43) | type-gating silently permits everything (`None` → `True`) |

I verified all 7 `_STACK_PRIMARY_LANGUAGE` entries match their overlay's
`skill_context.language` value-for-value — pure duplication. The stacks
dimension is actively growing (0.13.0 added `databricks-lakehouse`), so the
"remember to edit two code tables" tax is recurring, and the silent failure
modes mean nobody notices when it isn't paid.

Virtues: Unique (each fact lives once, in the stack's own manifest), Easy
(adding a stack becomes purely additive — drop in a directory, no code
edits), Coherent (restores overlay.py's documented contract).

## Target design

1. `overlay.yaml` gains a **required** `supported_types` list; the `Overlay`
   dataclass exposes it. Values per stack (copied from today's code table):
   - `python-fastapi`, `dotnet-aspnet`, `java-spring-boot`, `nodejs-fastify`,
     `go-gin` → `[api, cli]`
   - `python-dbt`, `databricks-lakehouse` → `[data]`
2. `stack_select._stack_supports_type` consults the loaded overlay; the
   permissive fallback survives (unknown stack id or empty list → `True`,
   preserving "safety net, not gatekeeper").
3. Doctor D005 reads `load_overlay(stack_id).skill_context.get("language")`
   (same local-import pattern D006 already uses) and
   `_STACK_PRIMARY_LANGUAGE` is deleted.

Contract enforcement, two layers:

- **Schema**: `governance/schemas/stack-overlay.schema.json` has
  `additionalProperties: false` and is enforced by
  `test_bundled_overlay_validates_against_schema` — so `supported_types`
  must be added to the schema in the same increment as the YAML edits.
  Make it `required` with items enum'd to the five `--type` values
  (`api`, `cli`, `data`, `ui-react`, `ui-angular`).
- **Guard test**: every bundled overlay must declare a non-empty
  `supported_types` AND a `skill_context.language`. The language guard stays
  a test (not a schema `required`) because `skill_context` is deliberately
  free-form per the schema's own description; the guard pins the one key
  doctor depends on without freezing the rest.

Explicitly NOT bumping overlay `version` fields: `supported_types` is
metadata, not doc content. A version bump would trigger D006 stale-baseline
warnings on every existing install for zero user benefit.

## Increments

Each increment is independently committable, full suite green, ruff scoped
to changed files.

### 1. `supported_types` joins the overlay contract (test-first)

1. Failing tests first:
   - `tests/test_overlay.py`: `load_overlay("python-fastapi").supported_types
     == ["api", "cli"]`; `load_overlay("python-dbt").supported_types ==
     ["data"]`; malformed/missing key → `[]` (loader default, not a crash)
   - `tests/test_overlay.py` guard: every bundled overlay declares non-empty
     `supported_types` and a `skill_context.language`
   - `tests/test_schemas.py` picks up the schema change automatically via
     `test_bundled_overlay_validates_against_schema` (required key missing →
     red until the YAMLs are edited; unknown key → red until the schema is)
2. Then, in one change set: schema property (+ `required`), all 7
   overlay.yaml files, `Overlay` dataclass field + `_build_overlay` wiring.

Diff: schema, 7 overlay.yaml, overlay.py, test_overlay.py.

### 2. Doctor D005 reads the overlay

Pinned behavior: five D005 tests in tests/test_doctor.py:351-428 (fires on
mismatch incl. databricks-lakehouse→python; silent on match, no stack, no
detected language, unknown stack id).

1. Replace `_STACK_PRIMARY_LANGUAGE.get(stack_id)` with a `load_overlay`
   lookup; `expected_lang = (overlay.skill_context or {}).get("language")`
   when the overlay loads, else `None` (unknown stack stays silent —
   identical to today).
2. Delete `_STACK_PRIMARY_LANGUAGE`.

Diff: doctor.py only.

### 3. Type-gating reads the overlay

Pinned behavior: tests/test_stack_select.py (explicit flag wins; `--type
data` overrides fastapi inference; `--type api` overrides dbt inference;
compatible inference honored).

1. `_stack_supports_type` loads the overlay: `None` or empty
   `supported_types` → `True` (permissive fallback unchanged); else
   membership test.
2. Delete `_STACK_SUPPORTED_TYPES`.

Diff: stack_select.py only.

### 4. Ride-along + sweep

1. Delete `validate._read_govkit_level` (verbatim copy of
   `marker.read_govkit_level`); import and call the original at the one use
   site (run_validation).
2. Grep for `_STACK_PRIMARY_LANGUAGE`, `_STACK_SUPPORTED_TYPES`,
   `_read_govkit_level` — plan docs may reference them as history; code must
   not.
3. CHANGELOG note under Unreleased. Full suite + end-to-end smoke
   (`apply --type data` on a scratch dir → confirms python-dbt default and
   type-gating through the overlay; `doctor` on a mismatched-language
   fixture → confirms D005 through the overlay).

## Risks / non-goals

- **No behavior change intended.** All current stacks keep identical
  language mappings and type support; unknown stacks stay permissive in
  stack_select and silent in D005, exactly as today.
- **Perf**: `_stack_supports_type` and D005 now read a YAML file per call.
  Both are called at most once per command run; negligible.
- **Non-goal**: deriving `supported_types` from the overlay's docs `dest`
  paths (`docs/data/...` implies data) — too clever, breaks the moment a
  stack ships mixed docs. Declared metadata is the honest representation.
- **Non-goal**: folding `_DEFAULT_STACK_BY_TYPE` into overlays. "Which stack
  is the default for a type" is govkit policy about the *set* of stacks, not
  a fact about any single stack — one default per type cannot live in seven
  files without inventing a precedence rule. It stays in code.
