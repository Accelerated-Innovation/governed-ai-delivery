# Loop-ready gates plan

Status: in progress. L01 is delivered. L02 onward were replanned on 2026-11-22 and none is implemented.
Plan version: 0.2. Version 0.1 is summarized in Section 10.
Prepared: 2026-11-20. Replanned: 2026-11-22.
Baseline inspected: govkit 0.23.0, commit af71fa9.
Epic: not yet opened. Open it once this version is agreed.

## 1. Purpose and how to use this plan

This plan makes a feature's own definition of done checkable by a tool, so that it can be the stop condition of an agent loop. GovKit does not run the loop. A coding agent or maintainer should be able to continue the work from this file and the repository alone.

- Follow current maintainer instructions and CLAUDE.md first. Use this plan for scope, order and completion evidence.
- Each increment is delivered test first, through its own issue and PR, under CLAUDE.md *Delivery review*.
- Each increment is tried in the pilot repository (Section 7) before the next one is designed in detail.
- Update the ledger in Section 11 after each increment. An unchecked criterion stays unchecked until the behaviour is demonstrated.
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

A project that follows GovKit's feature workflow already writes down what done means:

- `acceptance.feature` holds the behaviour as Gherkin scenarios, including scenarios tagged `@nfr-*` that carry the non-functional values to test.
- Tests are written first and fail before the implementation exists.
- `eval_criteria.yaml` states the acceptable values for probabilistic evaluation.

What is missing is a tool that reports whether that definition was met. GovKit checks that the definition is written and well-formed. It does not check that a scenario ran and passed, or that an evaluation scored above its threshold.

## 3. Evidence

### 3.1 The first pilot repository

A level 5 Python and FastAPI consumer repository on govkit 0.23.0, with 30 feature packages, was reviewed read-only on 2026-11-20 to write a `/goal` prompt for one implementation increment. Each item below had to be discovered by hand.

1. **`validate` could not be the stop condition.** `govkit validate --target .` exited 1 because 10 older packages failed later-added checks. L01 addressed this.
2. **The real checks are prose.** Lint, type check, boundary check and the three test tiers are named in CI YAML and in the project's CLAUDE.md.
3. **A skip reads as a pass.** Integration scenarios skip when a service is unreachable, unless CI-only environment variables turn the skip into a failure.
4. **Legitimate skip markers are an escape route.** The project marks unbound scenarios `@pending`. A loop could reach green by adding more.
5. **The verifier is editable.** Acceptance files, thresholds, datasets, rubrics, CI workflows and test settings all sit in the tree the loop edits.
6. **Some evaluations are paid or need a person.** LLM-judge runs cost money under an owner-set cap, and some criteria need human labels.
7. **The unit of work is prose.** The project wrote its own test to prove every acceptance scenario is bound to a runnable copy.
8. **Preconditions are implicit.** Services had to be started before any check could give a meaningful answer.

### 3.2 Findings on 2026-11-22

Found by running commands against a fresh installation and by reading the evidence modules.

1. **New installations have no level.** `govkit profile apply` followed by `govkit pack apply` writes a profile, a resolution, a pack lock, pinned packs and agent skills. It writes no `.govkit/marker.json`, the schemas have no level field, and `--level` is rejected.
2. **`govkit validate` checks nothing there.** Without a marker it falls back to level 3, prints the level 3 notice and exits 0. The L01 options run and check nothing.
3. **`govkit conform` runs no feature checks there.** It passed on the profile and the pack lock. The feature checks were reported as not applicable because they require legacy configuration. The `gherkin-delivery` pack ships skills and no checks.
4. **Issue #220 does not list `validate`.** It tracks the features that work only through a marker or a level and need a profile equivalent before legacy removal.
5. **The evidence contract already states the principle.** `docs/<area>/evaluation/EVIDENCE_CONTRACT.md` says a forecast is not evidence, a producer self-check is advisory, and `INCONCLUSIVE` is not a pass.
6. **`govkit evidence` already runs locally and without a level.** It reads JUnit XML and axe JSON from the working tree. The evidence gate template runs the project's tests and then the same command.
7. **`govkit evidence` counts a skipped test as passed.** A report with one passing and three skipped tests printed `Working PASS 4 tests passed` and exited 0.
8. **`govkit evidence` is not connected to the definition of done.**
   - It never reads `acceptance.feature` or `eval_criteria.yaml`.
   - It reports on the whole repository, with no feature selection.
   - It accepts any matching result file in the tree, whatever commit produced it.

The first pilot is a legacy level 5 installation. Sections 3.2 and 6 rest on one level-free installation made from a bundled example until the new pilot reports.

## 4. Decisions

Decisions 1 to 9 were agreed on 2026-11-19 and 2026-11-20. Decisions 10 to 15 were agreed on 2026-11-22.

1. **GovKit does not run loops.** It does not spawn, schedule or re-prompt an agent. The agent's own primitives own the trigger and the iteration. GovKit owns the stop condition, the limits and the record.
2. **Core and pack are separate.** Improvements that are useful with no loop at all go in the core installer. Everything that is specifically about driving a loop goes in an opt-in declarative pack in this repository.
3. **No "loop" in core names.** Options, schemas and commands in core are named for what they do. Only the pack carries the loop-engineering label.
4. **Claude Code only at first.** Pack skills are written agent-neutrally. The guidance on how to drive them (`/goal`, `/loop`, `/schedule`) ships for Claude Code only until the other agents have equivalent primitives.
5. **Backend, CLI and data first.** UI types follow later.
6. **A loop finishing is not approval.** Reaching the stop condition does not replace review, merge authorization or a release decision.
7. **Unknown is never done.** Required evidence that is skipped, degraded, unverified or owed cannot produce a passing result.
8. **"Baseline" is not reused.** `govkit validate-baseline` already means an approved behavioural baseline. The record of accepted existing failures is called "known failures".
9. **Plan plus issues.** This plan holds shared decisions and order. An epic tracks the whole; each increment has its own issue. Issues are opened a few at a time.
10. **The definition of done is the feature's existing artifacts.** These are the scenarios in `acceptance.feature` including their NFR values, the tests that implement them, and the thresholds in `eval_criteria.yaml`. GovKit adds no parallel declaration of what done means. It may add the minimum needed to bind a criterion to a result.
11. **Build on the level-free path.** New work extends `govkit evidence` and `govkit conform`, which do not depend on a level. No later increment extends `govkit validate`. L01 stays as shipped, and its identifiers and known-failures record are reused where they fit.
12. **Local first, then CI, with one command.** Each check must work in a working tree while code is being written and tested. CI runs the same command. Nothing is built for CI only.
13. **A local result is a stop condition, not a gate.** The evidence contract says the task owner never commits its own final gate. A local run tells the agent to continue, stop or escalate. The independent run in CI is the one that counts for merge.
14. **One vocabulary.** Results use the evidence contract's outcomes: `PASS`, `FAIL`, `INCONCLUSIVE` and `ERROR`. The three states in Section 5 are derived from them.
15. **Test-first ordering is deferred.** Whether a test failed before the code existed is not verified for feature work in this plan. The evidence contract's "Timely" dimension stays unmeasured.

## 5. Target behaviour

For a selected feature, the later increments compose into one answer with three states:

| State | Meaning | Derived from |
|---|---|---|
| **done** | All required evidence for the feature is satisfied, with nothing unknown, skipped or owed, and nothing that was passing now fails. | Every required item is `PASS`. |
| **continue** | There are findings the agent can act on, each naming the scenario or criterion and the next action. | At least one `FAIL` the agent may fix. |
| **escalate** | What remains needs a person. | A required item is `INCONCLUSIVE` or `ERROR` and the agent cannot resolve it: a paid or human evaluation, a missing precondition, a stale result, or a protected file that would have to change. |

Required paid or human evidence that is still owed is **escalate**, never done.

The third state is the reason for the design. A two-state stop condition leaves an agent working on something it cannot legitimately fix, or tempts it to weaken the check.

## 6. Increments

Each increment is independently demonstrable and is tried in the pilot repository before the next is detailed.

| Id | Increment | Command | Depends on | Issue |
|---|---|---|---|---|
| L01 | Feature-scoped `validate` with a known-failures record | `validate` | — | #248, delivered in #254 |
| L02 | A skipped test is not a pass | `evidence` | — | not opened |
| L03 | Feature selection and scenario binding | `evidence` | L02 | not opened |
| L04 | Thresholds from `eval_criteria.yaml`, with cost and authority classes | `evidence` | L03 | not opened |
| L05 | Results must belong to the current commit | `evidence` | L02 | not opened |
| L06 | The definition cannot be weakened by the change it judges | `conform` | L03 | not opened |
| L07 | Preconditions, the three-state verdict and `conform` integration | `conform` | L02–L06 | not opened |
| L08 | CI templates use the feature-scoped checks | payload | L07 | not opened |
| L09 | Opt-in pack: skills, Claude Code guidance, prompt writer, run records | pack | L07 | not opened |

The order after L03 is provisional. The pilot decides it.

### L01 — Feature-scoped `validate` with a known-failures record (delivered)

`--feature`, `--known-failures`, `--known-failures-digest` and `--print-known-failures` on `govkit validate`, with stable check identifiers. The contract is ADR 0021 and `docs/KNOWN_FAILURES.md`. It serves legacy installations and checks nothing on a level-free installation (Section 3.2). `govkit conform` keeps its positional feature codes; aligning them is #253.

### L02 — A skipped test is not a pass

`govkit evidence` reads the skipped count and skipped test cases from JUnit XML.

- "Working" is `PASS` only when at least one test ran and none failed, errored or was skipped.
- A report in which tests were skipped is `INCONCLUSIVE`, and the detail gives the counts and names the first few skipped tests.
- A report in which every test was skipped is `INCONCLUSIVE`, as an empty report is today.
- Failures and errors still take precedence and report `FAIL`.

This is a defect against the evidence contract. It changes an exit status from 0 to 1 for projects that have skipped tests, so the changelog must say so. Whether a project may declare accepted skips is decided in L06, not here.

### L03 — Feature selection and scenario binding

`govkit evidence --feature <name>` reports on one feature. It reads the scenarios from `features/<name>/acceptance.feature` and binds each one to a test result.

- Each scenario reports one of: passed, failed, skipped, or missing (no result found).
- The feature's "Working" outcome is `PASS` only when every scenario passed.
- Scenarios tagged `@nfr-*` are listed with their tags, so the report shows which NFR values were exercised.
- A name that matches no feature directory is an error, as in L01.

The binding rule is the open design question (Section 9). Test runners name Gherkin scenarios differently in JUnit output, so the rule must be settled against the pilot's real output before the schema is fixed. This increment replaces per-project tests that prove every scenario has a runnable copy.

### L04 — Thresholds from `eval_criteria.yaml`

`govkit evidence --feature <name>` reads the feature's criteria and compares each against a measured result.

- Each criterion is bound to a result a tool produced. The format of that result file is an open question.
- Each criterion has a class: `free`, `paid` or `human`.
  - A `free` criterion with a result reports `PASS` or `FAIL` against its threshold.
  - A `free` criterion without a result is `INCONCLUSIVE`.
  - A `paid` or `human` criterion without a result is reported as owed, which the verdict turns into escalate. GovKit never starts a paid or human evaluation.
- The FIRST and virtue forecasts in `plan.md` remain forecasts. They are not read as results.

Adding the class changes the three `eval_criteria` schemas (backend, UI, data), their starters and their worked examples together.

### L05 — Results must belong to the current commit

A result file from an earlier state of the tree is `INCONCLUSIVE`, not `PASS`. The evidence contract already requires evidence to be scoped to the exact commit; nothing enforces it. How a result is tied to a commit is an open question. Issue #152 proposes a per-feature evidence record and overlaps with this increment; decide here whether L05 delivers part of it.

### L06 — The definition cannot be weakened by the change it judges

A check on the actual Git diff, composed through `change_conformance.py`, which already captures it.

- Protected by default: `acceptance.feature`, `eval_criteria.yaml`, the known-failures record and the CI workflows.
- Protected when the project declares them: datasets, rubrics, thresholds and test settings.
- Adding scenarios or tests is allowed. Deleting a scenario, loosening a threshold or editing a protected file is a finding that needs a person.
- A project may declare escape markers (skip, xfail, a pending tag). Their count for a feature may fall but not rise against the comparison base.

### L07 — Preconditions, the verdict and `conform` integration

A read-only command composes L02 to L06 into the three states of Section 5, with stable exit codes and structured output.

- Preconditions are checked first: the feature exists, its artifacts are present, result files exist, and required services are reachable where the project declares them.
- The feature artifact checks that `validate` runs today become selectable by capability and reportable through `govkit conform`, so a level-free installation has them. This closes the gap in #220.
- L01's check identifiers and the known-failures record are reused.

### L08 — CI templates use the feature-scoped checks

The evidence gate templates for GitHub and Azure, and `ci/README.md`, are updated together to run the feature-scoped checks and to treat `INCONCLUSIVE` as the contract requires. No new CI-only behaviour is added.

### L09 — Opt-in pack

A declarative pack under `extensions/` with agent-neutral skills for a feature loop and a pull request loop, Claude Code guidance for driving them, a skill that writes the goal prompt from the feature's artifacts, and a schema for self-reported run records. Proactive maintenance entry points are generated but never activated by GovKit.

## 7. Pilot repository

The maintainer is creating a pilot repository to try each increment. It replaces the single hand-run trial (L00) of version 0.1. To exercise this plan it needs:

- a level-free installation: `govkit profile apply` then `govkit pack apply`, with `application-governance`, `gherkin-delivery` and `llm-evaluation`;
- a test runner that executes Gherkin scenarios and writes JUnit XML;
- at least three features:
  - one deterministic feature whose scenarios all pass;
  - one with `@nfr-*` scenarios that carry values to test;
  - one with `mode: llm` criteria, including a criterion that is paid or needs a person;
- at least one scenario that skips when a service is unavailable, to exercise L02;
- one older feature left failing, to exercise the known-failures record.

After each increment, record in the ledger: what the pilot run showed, whether "done" survived an independent rerun, what the agent could not fix, how it read GovKit's output, and the cost.

## 8. Non-goals and risks

Non-goals:

- Invoking, scheduling or supervising an agent.
- Telemetry. Run records stay local unless explicitly published.
- Further changes to `govkit validate`.
- Verifying that tests were written before the code.
- Scoring judgement-only dimensions such as "Clear" mechanically.
- Parity of loop-driving guidance across all three agents in the first release.
- UI project types in the first pass.

Risks:

- **The agent grades its own work locally.** Decision 13 keeps the local result advisory; L05 and L06 limit what a local run can claim.
- **Scenario binding varies by test runner.** L03 is promised only for runners whose JUnit output names the scenario.
- **Probabilistic results have no standard file format.** L04 may have to define one.
- **L02 turns some green runs red.** Projects with skipped tests will see `INCONCLUSIVE` where they saw `PASS`.
- **Two commands could drift.** `validate` and `evidence` both gain a `--feature` option. L07 brings them under `conform`.
- **The term may not last.** Decision 3 limits the exposure to the pack.
- **Thin evidence.** One legacy pilot and one synthetic level-free installation, until the new pilot reports.

## 9. Open questions

1. **Scenario binding (L03).** How is a scenario matched to a JUnit test case: by scenario name, by a stable tag, or by a mapping the project declares? Decide from the pilot's real output.
2. **Evaluation result format (L04).** What file carries a measured score for a criterion, and which tools write it today?
3. **Commit scoping (L05).** Is a result tied to a commit by a recorded revision, by comparing file times, or by an evidence record as in #152?
4. **Schemas on a level-free installation.** Does a pack install the `eval_criteria` schema, and which of the three applies when there is no project type from a marker?
5. **Accepted skips.** May a project declare a skip as accepted, and if so where, without recreating the escape route of Section 3.1 item 4?
6. **The legacy pilot.** Can it be converted with `govkit migrate`, so that it also exercises the level-free path?

## 10. What changed from version 0.1

Version 0.1 planned L02 to L06 as additions to `govkit validate`, with a new file in which a project declared its verification checks.

- **The definition of done moved.** It is the feature's own scenarios, tests and criteria (decision 10), so the separate declaration file is dropped.
- **The foundation moved.** New installations have no level and `validate` checks nothing there, so the work builds on `evidence` and `conform` (decision 11).
- **The order changed.** Skipped results come first, because the defect exists today. Scenario binding moved from fifth to third, because it connects the checks to the definition.
- **The trial changed.** A single hand-run trial became a pilot repository used after every increment.

| Version 0.1 | Version 0.2 |
|---|---|
| L00 Hand-run trial | Section 7, the pilot repository |
| L01 Feature-scoped `validate` | L01, delivered |
| L02 Declared verification checks with classes | Dropped as a separate file; the classes move to L04 |
| L03 Skipped and degraded results; escape-marker ratchet | L02 (skipped results) and L06 (ratchet) |
| L04 Protected paths | L06 |
| L05 Machine-readable increments and scenario binding | L03 (scenario binding); machine-readable increments dropped |
| L06 Preconditions and the verdict | L07 |
| L07 Opt-in pack | L09 |
| — | L04 thresholds, L05 commit scoping and L08 CI templates are new |

## 11. Execution ledger

| Date | Increment | Result | Next |
|---|---|---|---|
| 2026-11-20 | Plan | Version 0.1 written; #248 opened for L01 | Agree plan |
| 2026-11-22 | Plan | Version 0.1 merged as #252 | Start L01 |
| 2026-11-22 | L01 | Delivered in #254 (`af71fa9`): four `validate` options, `known-failures` v1 schema and example, ADR 0021, guide, runtime-only wheel smoke for three agents. Six open points recorded on #248; #253 filed for conform's codes | — |
| 2026-11-22 | Plan | Version 0.2: replanned after finding that new installations have no level and that `govkit evidence` is the level-free foundation (Section 3.2) | Agree version 0.2; create the pilot repository; open the epic and the L02 issue |
