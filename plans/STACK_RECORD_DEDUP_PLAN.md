# Stack Record Dedup Plan

Give the two stack marker records — the `stack.id` assumption and the
`stack` metadata block — a single point of construction in
`cli/stack_select.py`, eliminating the verbatim copies in
`cli/cmd_stack.py`.

## Motivation (evidence)

Two record shapes are built independently in two modules:

1. **The 10-key `stack.id` assumption.**
   `stack_select._build_stack_assumption` derives it from
   (overlay, source, confidence, evidence);
   `cmd_stack.cmd_stack_apply` inlines the same dict with hardcoded
   values. Verified: the inline copy is exactly
   `_build_stack_assumption(overlay, source="flag", confidence="high",
   evidence=[])` — including the derived fields (`review_required:
   source == "default"` → False; `warning_message` → None).
2. **The 4-key `stack` metadata block** (`id`, `version`, `display_name`,
   `applied_at`) — built identically in `stack_select.apply_stack_overlay`
   and `cmd_stack.cmd_stack_apply`.

Failure mode: adding a field to either record (e.g. a future calibration
hint) requires two edits; miss one and `govkit apply --stack` and
`govkit stack apply` write silently divergent marker records — the same
silent-drift class the agent-layout and stack-metadata refactors closed.

The dependency already flows correctly: cmd_stack imports
`STACK_ID_ASSUMPTION` from stack_select. The owner exists; the record
construction just never moved there.

Virtues: Unique (one definition per record shape), Easy (next field = one
edit), Coherent (the module that owns the stack choice owns its records).

## Target design

In `cli/stack_select.py`:

- Promote `_build_stack_assumption` → `build_stack_assumption` (same body;
  public because cmd_stack consumes it across modules).
- Add `build_stack_meta(overlay) -> dict` returning the 4-key block with
  `applied_at` stamped at call time; `apply_stack_overlay` uses it.

In `cli/cmd_stack.py`:

- `cmd_stack_apply` calls `build_stack_assumption(overlay, source="flag",
  confidence="high", evidence=[])` and `build_stack_meta(overlay)`;
  the two inline dicts (~16 lines) are deleted.

Records must stay byte-identical — the integration tests in
tests/test_govkit.py (assumption source=flag / source=default) and
tests/test_skill_context.py (cmd_stack_apply end-to-end) are the spec.

## Increments

### 1. Promote the builders (test-first)

1. Failing tests first, in tests/test_stack_select.py:
   - `build_stack_assumption(overlay, "flag", "high", [])`:
     review_required False, warning_message None, value == overlay.id,
     files_affected == overlay doc dests, calibrated fields None
   - `build_stack_assumption(overlay, "default", "low", [])`:
     review_required True, warning_message names the overlay id
   - `build_stack_meta(overlay)`: exactly the 4 keys, values from the
     overlay, applied_at parseable by datetime.fromisoformat
2. Rename `_build_stack_assumption` → `build_stack_assumption`; add
   `build_stack_meta`; `apply_stack_overlay` uses it in place of its
   inline dict.

Diff: stack_select.py + test_stack_select.py.

### 2. cmd_stack consumes the builders

Replace the two inline dicts in `cmd_stack_apply` with the builder calls.
The "replace prior stack.id assumption, keep the rest" filter stays in
cmd_stack — it is re-apply-specific and has one site.

Diff: cmd_stack.py only.

### 3. Sweep

1. Grep: `_build_stack_assumption` gone from code; no inline
   `"calibrated_against_overlay_version"` construction outside
   stack_select (tests may build fixture assumptions inline — that is
   test data, not production knowledge, and stays).
2. CHANGELOG note under Unreleased. Full suite. End-to-end: `govkit stack
   apply <id>` on a scratch install; inspect the marker's stack block and
   assumption record.

## Risks / non-goals

- **No behavior change.** Both commands write byte-identical records.
- **Non-goal:** moving the prior-assumption replacement filter out of
  cmd_stack (single site).
- **Non-goal:** a Python dataclass for the assumption record. It is
  serialized straight to JSON and consumed as a dict everywhere (doctor,
  calibrate, setup_review); a class would add conversion at every boundary
  for no call-site gain — the builder function IS the single point of
  definition.
