# Loop-ready gates plan

Status: in progress. L01 ([#248](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/248)) is implemented and in review; no later increment is implemented. The order after L02 is provisional until the trial (L00) has been run.
Plan version: 0.1.
Prepared: 2026-11-20.
Baseline inspected: govkit 0.23.0, commit 606024a.
Epic: not yet opened. Draft text exists; open it once this plan is agreed.

## 1. Purpose and how to use this plan

This plan makes GovKit's checks usable as the stop condition of an agent loop, without GovKit running any loop itself. A coding agent or maintainer should be able to continue the work from this file and the repository alone.

- Follow current maintainer instructions and CLAUDE.md first. Use this plan for scope, order and completion evidence.
- Each increment is delivered test first, through its own issue and PR, under CLAUDE.md *Delivery review*.
- Update the ledger in Section 8 after each increment. An unchecked criterion stays unchecked until the behaviour is demonstrated.
- Writing this document implements nothing.

## 2. Background

Anthropic's Claude Code team defines a loop as an agent repeating cycles of work until a stop condition is met ([Getting started with loops](https://claude.com/resources/articles/getting-started-with-loops), 2026-06-30). The article describes four kinds, by what the person hands off:

| Loop | Hand-off | Claude Code primitive |
|---|---|---|
| Turn-based | The check | Verification skills |
| Goal-based | The stop condition | `/goal` |
| Time-based | The trigger | `/loop`, `/schedule` |
| Proactive | The prompt | The above, composed |

Its recurring advice is to give the agent a way to verify its own work, to define deterministic success and stop criteria, and to have code-writing loops checked by an independent reviewer.

A project that installs GovKit already has much of this: skills and rules, feature artifacts with acceptance criteria, `validate`, `doctor`, `conform`, and quality-gate templates. What it lacks is a stop condition an agent can be handed. GovKit's commands are one-shot checks with no trigger, iteration or turn limit, and that is intended to stay true.

## 3. Evidence from the pilot repository

A level 5 Python and FastAPI consumer repository on govkit 0.23.0, with 30 feature packages, was reviewed read-only on 2026-11-20 to write a `/goal` prompt for one implementation increment. Each item below had to be discovered by hand, and each one shaped the prompt.

1. **`validate` cannot be the stop condition.** `govkit validate --target .` exits 1 because 10 older packages fail later-added checks. There is no per-feature selector.
2. **The real checks are prose.** Lint, type check, boundary check and the three test tiers are named in CI YAML and in the project's CLAUDE.md. Three of them (`ruff`, `mypy`, `lint-imports`) run only locally.
3. **A skip reads as a pass.** Integration scenarios skip when a service is unreachable, unless CI-only environment variables turn the skip into a failure. `validate` itself reports a warning and continues when `check-jsonschema` is absent.
4. **Legitimate skip markers are an escape route.** The project marks unbound scenarios `@pending`. A loop could reach green by adding more.
5. **The verifier is editable.** Acceptance files, thresholds, datasets, rubrics, CI workflows and test settings all sit in the tree the loop edits.
6. **Some evaluations are paid or need a person.** LLM-judge runs cost money under an owner-set cap, and some criteria need human labels. A loop must never start them and cannot satisfy them.
7. **The unit of work is prose.** "Increment N" and the scenarios it covers exist only in a plan document. The project wrote its own test to prove every acceptance scenario is bound to a runnable copy.
8. **Preconditions are implicit.** Services had to be started before any check could give a meaningful answer.

This is one repository and one stack. The trial in L00 is the first evidence from a loop actually running.

## 4. Decisions

Agreed on 2026-11-19 and 2026-11-20.

1. **GovKit does not run loops.** It does not spawn, schedule or re-prompt an agent. The agent's own primitives own the trigger and the iteration. GovKit owns the stop condition, the limits and the record.
2. **Core and pack are separate.** Improvements that are useful with no loop at all go in the core installer. Everything that is specifically about driving a loop goes in an opt-in declarative pack in this repository, so no project is forced to take it.
3. **No "loop" in core names.** Options, schemas and commands in core are named for what they do. Only the pack carries the loop-engineering label.
4. **Claude Code only at first.** Pack skills are written agent-neutrally. The guidance on how to drive them (`/goal`, `/loop`, `/schedule`) ships for Claude Code only until the other agents have equivalent primitives.
5. **Backend, CLI and data first.** UI types follow later, as with architecture experiments.
6. **A loop finishing is not approval.** Reaching the stop condition does not replace review, merge authorization or a release decision.
7. **Unknown is never done.** Required evidence that is skipped, degraded, unverified or owed cannot produce a passing result.
8. **"Baseline" is not reused.** `govkit validate-baseline` already means an approved behavioural baseline. The record of accepted existing failures is called "known failures".
9. **Plan plus issues.** This plan holds shared decisions and order. An epic tracks the whole; each increment has its own issue. Issues are opened a few at a time, because later increments depend on what earlier ones teach.

## 5. Target behaviour

The later increments compose into one answer with three states:

- **done**: all required evidence for the selected scope is satisfied, with nothing unknown, skipped or owed, and nothing that was passing now fails. Required paid or human evidence that is still owed is **escalate**, never done.
- **continue**: there are findings the agent can act on, each naming the file and the next action.
- **escalate**: what remains needs a person. Examples are a protected file that would have to change, an evaluation that is paid or human-labelled, a missing precondition, or evidence that is unknown.

The third state is the reason for the design. A two-state stop condition leaves an agent working on something it cannot legitimately fix, or tempts it to weaken the check.

## 6. Increments

Each increment is independently demonstrable. L01 to L05 are gate improvements that stand without L06 and L07.

| Id | Increment | Where | Depends on | Issue |
|---|---|---|---|---|
| L00 | Hand-run trial in the pilot repository | No code | — | — |
| L01 | Feature-scoped `validate` with a known-failures record | Core | — | #248 |
| L02 | Declared verification checks with cost and authority classes | Core | — | drafted |
| L03 | Skipped and degraded results as unknown; escape-marker ratchet | Core | L02 | drafted |
| L04 | Protected paths checked against the actual diff | Core | L02 | not written |
| L05 | Machine-readable increments and scenario binding | Core | — | not written |
| L06 | Preconditions and the three-state verdict | Core | L01–L05 | not written |
| L07 | Opt-in pack: skills, Claude Code guidance, prompt writer, run records | Pack | L06 | not written |

### L00 — Trial

The maintainer drives one or two implementation increments in the pilot repository with `/goal`, using the existing commands as the stop condition, and records: why the loop stopped, whether it touched any verifier file, whether "done" survived an independent rerun, what it could not fix, how it read GovKit's output, and the cost. The findings revise the order and content of L03 onward.

### L01 — Feature-scoped `validate` with a known-failures record

Add `--feature` and `--known-failures` to `govkit validate`, give each per-feature check a stable identifier, and report failures as new, known or resolved. GovKit never writes or accepts the record. Full contract in #248. The contract as built is ADR 0021 and `docs/KNOWN_FAILURES.md`. `govkit conform` keeps its positional feature codes; aligning them is #253.

### L02 — Declared verification checks

A project declares its verification checks in one validated file: an identifier, the command, required environment and services, what the check proves, and a class of `free`, `paid` or `human`. The per-criterion class is also added to `eval_criteria.yaml`. GovKit reports where the declaration and the installed CI workflow disagree. Before designing the schema, read `gate_catalog.py` and ADR 0011; this should extend the existing GateSpec declarations if they fit, not add a parallel registry.

### L03 — Skipped and degraded results; escape-marker ratchet

A required check whose result is skipped, deselected or degraded is reported as unknown. Where a check produces a standard results file, GovKit reads skip counts from it. A project can declare escape markers (skip, xfail, a pending tag), and their count for a scope may fall but not rise against the comparison base.

### L04 — Protected paths

A change must not weaken its own verifier. Protected paths are derived from what GovKit already knows (feature specification artifacts, governed contracts, CI workflows, the known-failures record) plus paths the project declares (datasets, rubrics, thresholds, test settings). `change_conformance.py` already captures the actual Git diff; this adds a check on it. Adding tests is allowed; deleting or loosening existing ones is a finding.

### L05 — Machine-readable increments and scenario binding

An implementation plan names its increments and the acceptance scenarios each one covers in a form GovKit can read. A general check proves every acceptance scenario has a runnable bound copy, replacing per-project tests of the same idea.

### L06 — Preconditions and the verdict

A read-only command composes L01 to L05 into the three states of Section 5, with stable exit codes and structured output. Preconditions (services reachable, clean tree, record present) are checked first, so a missing one is reported before work starts.

### L07 — Opt-in pack

A declarative pack under `extensions/` with agent-neutral skills for a feature loop and a pull request loop, Claude Code guidance for driving them, a skill that writes the goal prompt from the declarations, and a schema for self-reported run records. Proactive maintenance entry points are generated but never activated by GovKit.

## 7. Non-goals and risks

Non-goals:

- Invoking, scheduling or supervising an agent.
- Telemetry. Run records stay local unless explicitly published.
- Changing what existing checks test.
- Parity of loop-driving guidance across all three agents in the first release.

Risks:

- **The term may not last.** Decision 3 limits the exposure to the pack.
- **Skip detection varies by stack.** L03 is promised only where a standard results file exists.
- **Declarations can drift from CI.** L02 must detect disagreement, not just store a second copy.
- **A record can hide failures.** L01 prints the record's digest; L04 protects the file.
- **Thin evidence.** Sections 3 and 6 rest on one repository until L00 reports.

## 8. Execution ledger

| Date | Increment | Result | Next |
|---|---|---|---|
| 2026-11-20 | Plan | Written; #248 opened for L01 | Run L00; agree plan; open epic and L02, L03 |
| 2026-11-22 | Plan | Merged as #252 | Start L01 |
| 2026-11-22 | L01 | Implemented test first on `feat/validate-feature-scope-known-failures`: four `validate` options, `known-failures` v1 schema and example, ADR 0021, guide, runtime-only wheel smoke for three agents. Six open points decided and recorded on #248; #253 filed for conform's codes | Review and merge the L01 PR; run L00 |
