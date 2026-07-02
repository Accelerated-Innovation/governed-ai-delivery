# Marker Warning Consolidation Plan

Collapse the three structurally identical copies of "print a suppressible
warning once per process" in `cli/marker.py` into one small `_OneTimeWarning`
value object plus three declarations.

## Motivation (evidence)

`cli/marker.py` lines 36–156 hold three instances of the same concept, each
repeating four elements:

| Warning | Global flag | Env-var suppression | Reset helper |
|---|---|---|---|
| Version migration (pre-0.7 L3/L4 swap) | `_MIGRATION_WARNING_PRINTED` | `GOVKIT_NO_MIGRATION_WARNING` | `_reset_migration_warning` |
| Shape migration (dropped `ui` option) | `_SHAPE_MIGRATION_WARNING_PRINTED` | `GOVKIT_NO_SHAPE_MIGRATION_WARNING` | `_reset_shape_migration_warning` |
| Directory migration (legacy single-file marker) | `_DIRECTORY_MIGRATION_WARNING_PRINTED` | `GOVKIT_NO_DIRECTORY_MIGRATION_WARNING` | `_reset_directory_migration_warning` |

~120 lines for one concept instanced three times. The repo has shipped a
marker migration in 0.7, 0.8, and 0.10 — the next one currently means a
fourth copy-paste of the whole block.

Virtues: Unique (the once-per-process + env-suppression algorithm exists
once), Brief (~120 → ~55 lines), Easy (the next migration warning is one
declaration), Developed (the implicit "one-time warning" concept becomes a
named thing).

## Constraints discovered in the tests

1. **The reset helper names are a de-facto public contract.** ~30 call
   sites across `tests/test_govkit.py` import
   `_reset_migration_warning` / `_reset_shape_migration_warning` /
   `_reset_directory_migration_warning` by name. Churning 30 test sites for
   zero behavioral value is out of scope — the three names survive as
   one-line delegations to the new representation.
2. **Messages are pinned byte-for-byte in spirit.** Tests assert env-var
   names appear in stderr (`assert "GOVKIT_NO_DIRECTORY_MIGRATION_WARNING"
   in err`) and count occurrences across multi-read scenarios. All three
   message strings stay identical.
3. **Trigger conditions differ per warning** (version comparison; `ui` in
   options; unconditional on legacy read). The conditions are NOT the
   duplication — they stay in the three `_maybe_warn_*` functions. Only the
   fire-once/suppress/print machinery consolidates.

## Target design

```python
@dataclass
class _OneTimeWarning:
    """A stderr warning that fires at most once per process, suppressible
    via an env var. Migration warnings declare one instance each; tests
    re-arm via reset()."""
    env_var: str
    printed: bool = False

    def warn(self, message: str) -> None:
        if self.printed or os.environ.get(self.env_var) == "1":
            return
        print(message, file=sys.stderr)
        self.printed = True

    def reset(self) -> None:
        self.printed = False


_VERSION_MIGRATION_WARNING = _OneTimeWarning("GOVKIT_NO_MIGRATION_WARNING")
_SHAPE_MIGRATION_WARNING = _OneTimeWarning("GOVKIT_NO_SHAPE_MIGRATION_WARNING")
_DIRECTORY_MIGRATION_WARNING = _OneTimeWarning("GOVKIT_NO_DIRECTORY_MIGRATION_WARNING")
```

Each `_maybe_warn_*` keeps its trigger condition and ends in
`_X_WARNING.warn(<same message>)`. Each `_reset_*` helper becomes
`_X_WARNING.reset()`. The three module-level `*_PRINTED` globals and the
`global` statements disappear.

Message passed at `warn()` time rather than stored on the instance: the
version warning interpolates `stored_version`, so a stored template would
need format-args plumbing for one caller — not worth it at three instances.

## Increments

### 1. `_OneTimeWarning` + port (test-first)

1. Failing tests first, in `tests/test_headers.py`-style class grouping
   (new class in `tests/test_govkit.py` next to the existing warning tests,
   or a small `tests/test_marker.py` if none fits — decide by proximity to
   the existing marker-warning test classes):
   - `warn()` prints to stderr once; second call is silent
   - `warn()` is silent when the env var is "1"
   - `reset()` re-arms
   - env var checked at warn time, not construction time (monkeypatch after
     instantiation must still suppress — module-level instances outlive
     test env changes)
2. Implement the class; port the three warnings to instances; reduce
   `_maybe_warn_*` to condition + `warn(message)`; reduce `_reset_*` to
   `reset()` delegations. Delete the three `*_PRINTED` globals.
3. The ~30 existing test sites and message assertions must stay green
   untouched — they are the behavioral spec for the port.

Diff: marker.py + one test file.

### 2. Ride-along + sweep

1. `validate.check_gherkin_nfr_coverage`: replace the `category_to_tag`
   identity dict (every key maps to itself) with a `frozenset` of known
   categories; `expected_tag = category`. Behavior identical; existing
   NFR-coverage tests pin it.
2. Grep for the deleted globals (`_MIGRATION_WARNING_PRINTED` etc.) — zero
   code hits.
3. CHANGELOG note under Unreleased. Full suite.

Diff: validate.py + CHANGELOG.

## Risks / non-goals

- **No behavior change.** Same messages, same env vars, same once-per-
  process semantics, same reset entry points for tests.
- **Non-goal:** promoting `_OneTimeWarning` to a shared module. marker.py is
  its only consumer; a second consumer elsewhere can motivate the move
  later (rule of three applies to homes as well as helpers).
- **Non-goal:** the section-body parser duplication in validate.py
  (`check_nfrs_sections._populated` / `check_llm_nfrs`) — at the evidence
  threshold, not over it; wait for a third caller.
