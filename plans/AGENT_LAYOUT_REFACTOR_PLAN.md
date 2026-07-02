# Agent Layout Refactor Plan

Give "an agent's on-disk layout" a single owner: a new kernel-leaf module
`cli/agent_layout.py` holding one frozen dataclass and one table, replacing the
four private copies of the same facts in `calibrate.py`, `setup_review.py`,
`doctor.py`, and `rule_templating.py`.

## Motivation (evidence)

Four modules independently translate the marker's `agent` string into
filesystem facts, each with its own `if/elif` chain or private table:

| Fact | calibrate.py `_agent_paths` | setup_review.py `_agent_doc_paths` | doctor.py `_rules_spec_for_agent` | rule_templating.py `_RULES_DIRS_BY_AGENT` / `_TEMPLATE_SCHEMAS` |
|---|---|---|---|---|
| Instruction file | copy | copy | — | — |
| Rules directory | copy | copy | copy | copy |
| Rules glob | — | copy | — | — |
| Frontmatter glob key | — | — | copy | copy |
| Glob value shape | — | — | implicit | copy |
| Codex "no rules dir" | `"AGENTS.md"` | `"(nested AGENTS.md per layer)"` | `None` | `[]` |

Adding a fourth agent today means editing four modules with four idioms —
including four different spellings of "this agent has no glob-scoped rules".
Agent parity is a maintained invariant of this repo; this table makes it
structural instead of remembered.

## Target design

```python
# cli/agent_layout.py — kernel leaf, imports nothing internal (like paths.py)

@dataclass(frozen=True)
class AgentLayout:
    instruction_file: str               # "CLAUDE.md"
    rules_dir: str | None               # None = no glob-scoped rules (codex)
    rules_glob: str | None
    frontmatter_glob_key: str | None    # "paths" | "applyTo"
    glob_value_shape: str | None        # "list" | "comma-string"

AGENT_LAYOUTS: dict[str, AgentLayout] = {
    "claude-code": AgentLayout("CLAUDE.md", ".claude/rules",
                               ".claude/rules/*.md", "paths", "list"),
    "copilot": AgentLayout(".github/copilot-instructions.md",
                           ".github/instructions",
                           ".github/instructions/*.instructions.md",
                           "applyTo", "comma-string"),
    "codex": AgentLayout("AGENTS.md", None, None, None, None),
}
```

Boundary: `agents/<agent>/manifest.json` continues to own *what installs*.
`agent_layout.py` owns the derived facts commands need *after* install (where
rules live, how their frontmatter is scoped, what to tell the user to review).

## Increments

Each increment is independently committable, keeps the full suite green, and
runs `ruff check` scoped to the files it touched. Increment 1 is test-first
(new code). Increments 2–5 are behavior-preserving refactors where the
existing per-agent tests are the specification — if a gap is found mid-
increment, add the failing test before changing the module.

### 1. Create `cli/agent_layout.py` (test-first)

1. Write `tests/test_agent_layout.py` — failing (module doesn't exist):
   - the three production agents are present with exactly the field values above
   - `AgentLayout` is frozen (assignment raises `FrozenInstanceError`)
   - codex has `rules_dir is None` and all glob fields `None`
   - parity guard: `set(AGENT_LAYOUTS) == {bundled agent dirs with a
     manifest.json under paths.AGENTS_DIR}` — a fourth agent cannot be added
     to the bundle without a layout row, or vice versa
2. Create the module to make them pass. No consumer changes.

Diff: 2 new files.

### 2. Migrate `doctor.py`

Pinned behavior: `test_d001_handles_copilot_applyto_format`,
`test_d001_codex_agent_skips_glob_check` (tests/test_doctor.py:207, 224).

1. In `_check_rule_globs_resolve` (D001), replace `_rules_spec_for_agent`
   with `AGENT_LAYOUTS.get(agent)`; skip when the layout is missing or
   `frontmatter_glob_key is None`. Convert `rules_dir` with `Path(...)` at
   the use site (the helper returned a `Path`).
2. Delete `_rules_spec_for_agent`.

Diff: doctor.py only.

### 3. Migrate `rule_templating.py`

Pinned behavior: `test_copilot_applyto_template_expands_to_comma_string`,
`test_copilot_applyto_fallback_preserved_when_layer_empty`
(tests/test_rule_templating.py:132, 153).

1. Derive the schema list from the table instead of hardcoding it:
   `[(f"{l.frontmatter_glob_key}_template", l.frontmatter_glob_key,
   l.glob_value_shape) for l in AGENT_LAYOUTS.values() if
   l.frontmatter_glob_key]`. `expand_rule_template(text, layers)` keeps its
   signature and its agent-agnostic try-both-schemas behavior — narrowing it
   to per-agent expansion would be a behavior change with no payoff; out of
   scope here.
2. In `template_installed_rules`, replace `_RULES_DIRS_BY_AGENT.get(agent, [])`
   with the layout lookup (`layout.rules_dir` or skip when `None`).
3. Delete `_RULES_DIRS_BY_AGENT` and the hardcoded `_TEMPLATE_SCHEMAS` literal.

Diff: rule_templating.py only.

### 4. Migrate `calibrate.py` and `setup_review.py`

Pinned behavior: per-agent path assertions in tests/test_calibrate.py:130–148
and tests/test_setup_review.py:65–80 — including the codex display strings.

1. `setup_review.py`: delete `_agent_doc_paths`; read `layout.instruction_file`,
   and render codex's absence at the two format sites:
   `layout.rules_dir or "(nested AGENTS.md per layer)"` /
   `layout.rules_glob or "AGENTS.md"`. Display fallbacks are presentation,
   not layout facts — they stay at the print site.
2. `calibrate.py`: delete `_agent_paths`; same lookup, fallback
   `layout.rules_dir or "AGENTS.md"` for the step's `file_path`.

Diff: calibrate.py + setup_review.py (both display-only consumers).

### 5. Sweep and close

1. `grep` the repo for `_agent_paths`, `_agent_doc_paths`,
   `_rules_spec_for_agent`, `_RULES_DIRS_BY_AGENT` — zero hits expected.
2. Full suite + ruff on all files touched by the branch.
3. Note in CHANGELOG.md under Unreleased (internal refactor, no user-facing
   behavior change).

## Risks / non-goals

- **No behavior change intended anywhere.** Every consumer's per-agent output
  is already pinned by tests; any red test in increments 2–4 means the
  refactor drifted, not that the test needs updating.
- **Non-goal:** moving layout facts into `agents/<agent>/manifest.json`.
  Defensible future home, but it costs a schema change across three manifests
  plus load-failure handling for zero present benefit. The table gives the
  facts one owner; consumers won't care if the storage moves later.
- **Non-goal:** per-agent narrowing of `expand_rule_template` (see
  increment 3).
