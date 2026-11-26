# Loop-ready gates plan

Status: in progress. L01 to L05 are delivered. L06 onward were replanned on 2026-11-22 and none is implemented. The epic is #257.
Plan version: 0.2. Version 0.1 is summarized in Section 12.
Prepared: 2026-11-20. Replanned: 2026-11-22.
Baseline inspected: govkit 0.23.0, commit af71fa9; `discovery-engine` commit ebdfc41, read-only.
Epic: not yet opened. Open it once this version is agreed.

## 1. Purpose and how to use this plan

This plan makes a feature's own definition of done checkable by a tool, so that it can be the stop condition of an agent loop. GovKit does not run the loop. A coding agent or maintainer should be able to continue the work from this file and the repository alone.

- Follow current maintainer instructions and CLAUDE.md first. Use this plan for scope, order and completion evidence.
- Each increment is delivered test first, through its own issue and PR, under CLAUDE.md *Delivery review*.
- Each increment is tried in the pilot repository (Section 8) before the next one is designed in detail.
- Update the ledger in Section 13 after each increment. An unchecked criterion stays unchecked until the behaviour is demonstrated.
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

### 3.2 Findings in GovKit on 2026-11-22

Found by running commands against a fresh installation and by reading the evidence modules.

1. **New installations have no level.** `govkit profile apply` followed by `govkit pack apply` writes a profile, a resolution, a pack lock, pinned packs and agent skills. It writes no `.govkit/marker.json`, the schemas have no level field, and `--level` is rejected.
2. **`govkit validate` runs no feature checks there.** Without a marker it falls back to level 3. That path skips every per-feature check, the fix-record checks and the approval check, and prints the level 3 notice. It still runs the extension manifest checks, which fail the run only with `--strict`. The L01 options run and select no feature.
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

### 3.3 Findings in the Product Definition Graph on 2026-11-22

Read from `discovery-engine` (feature 24, the requirements index). Nothing there was changed.

1. **The graph indexes feature packages from git at tagged baselines.** Each scenario and each `eval_criteria` criterion is a requirement with a stable identifier.
   - A scenario is `<package>#scenario:<slug>`. The slug is an authored `@scenario:` tag, or is derived from the title.
   - A criterion is `<package>#evaluation:<name>`.
   - A scenario has a revision digest: SHA-256 of its text without comment lines. A criterion uses the content digest of its file.
2. **The graph accepts verification runs.** `POST /v1/verification-runs` records a run reference, the repository, the baseline tag, the build commit, the execution time, an `https://` artifact link, and one result per requirement. A result names the requirement, the revision that ran, a kind of `test` or `evaluation`, and an outcome of `passed`, `failed`, `skipped` or `error`.
3. **The graph computes status.** A read route reports each requirement as passed, failed, skipped, error, `unverified` (no run names the current revision) or `stale` (runs name only an earlier revision).
4. **Runs are strict and immutable.** The caller needs a service identity. The whole run is refused unless every revision matches the indexed baseline. An identical re-send is accepted; a different payload under the same reference is a conflict.
5. **A result carries no score.** The graph compares a criterion with measurements through a separate path, study findings that carry a metric, a value and a unit. A criterion may declare a `target` (metric, comparator, value, unit) for that comparison.
6. **Nothing pushes runs yet.** The route is documented as called by the build repository's CI. GovKit's graph client only reads commitment status.
7. **The identity rules have two owners.** `aipos-plugins` owns the identifier format and the slug rule; the slug rule exists only as code in one skill's script, and the engine mirrors it with a fixture pinned by hand to a commit. The engine owns the revision digest, which its ADR-AIG-035 defines and no other repository computes. GovKit would be a further copy of both.
8. **Issue #152 names shapes the engine does not have.** It proposes emitting `Specification` and `EvaluationResult`. The implemented contract is the verification run.

## 4. Decisions

Decisions 1 to 9 were agreed on 2026-11-19 and 2026-11-20. Decisions 10 to 21 were agreed on 2026-11-22.

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
12. **Local first, then CI, with one command.** Each check must work in a working tree while code is being written and tested. CI runs the same command. Nothing is built for CI only, except pushing results to another system (decision 19).
13. **A local result is a stop condition, not a gate.** The evidence contract says the task owner never commits its own final gate. A local run tells the agent to continue, stop or escalate. The independent run in CI is the one that counts for merge.
14. **One vocabulary.** Results use the evidence contract's outcomes: `PASS`, `FAIL`, `INCONCLUSIVE` and `ERROR`. The three states in Section 5 are derived from them.
15. **Test-first ordering is deferred.** Whether a test failed before the code existed is not verified for feature work in this plan. The evidence contract's "Timely" dimension stays unmeasured.
16. **The JSON report is canonical.** `govkit evidence` produces one lossless, versioned JSON report. Every other form is a projection of it: the text output, a verification run for the Product Definition Graph, and OpenTelemetry signals. A custom application reads the JSON directly.
17. **Nothing is transmitted automatically.** GovKit sends nothing anywhere by default. Each export is an explicit, opt-in step with an allowlist of what may leave the repository, as posture export already has.
18. **Use the graph's identity.** GovKit identifies a scenario and a criterion exactly as the Product Definition Graph does, and computes the same revision digest (Section 3.3). The JSON report is a superset of the graph's verification run.
19. **Only CI pushes to the graph.** The graph requires a service identity, an artifact link and a tagged baseline. A local run, or work on a feature with no baseline yet, is not recorded there.
20. **Scores travel in the verification run.** A measured score is carried as an optional measurement on a result, bound to the commit and revision that produced it. This needs a change in `discovery-engine` (Section 7). Scores are not sent as study findings.
21. **OpenTelemetry is an optional projection.**
    - It emits one event (log record) per scenario or criterion result, and metrics at feature level.
    - Scenario names are never metric labels, because vendors bill custom metrics by label combination.
    - Traces are deferred.
    - The OpenTelemetry SDK is not a core dependency. The exporter is an optional extra or writes a file a collector can ingest.
    - Endpoint and credentials come from the standard OpenTelemetry environment variables.

## 5. Target behaviour

For a selected feature, the later increments compose into one answer with three states. The report always lists every item; the state is a single value chosen in this order:

1. **escalate**, when the change itself needs a person now: it weakened the definition or an existing test (L06), or evidence is `ERROR`.
2. **continue**, when at least one required item is `FAIL` and the agent may fix it, or a result the agent can produce is missing, stale or unrecorded. Work the agent can do comes before waiting for a person.
3. **escalate**, when nothing is left for the agent and a required item is still not `PASS`: a paid or human evaluation is owed, a test was skipped, or a required check has no result.
4. **done**, when every required item is `PASS` and nothing that was passing now fails.

Rules 2 and 3 were changed on 2026-11-26 (maintainer): a stale, unrecorded or missing free result is work for the agent, so it gives continue. They first said escalate.

Required paid or human evidence that is still owed can never produce done.

The escalate state is the reason for the design. A two-state stop condition leaves an agent working on something it cannot legitimately fix, or tempts it to weaken the check.

## 6. Increments

Each increment is independently demonstrable and is tried in the pilot repository before the next is detailed.

| Id | Increment | Where | Depends on | Issue |
|---|---|---|---|---|
| L01 | Feature-scoped `validate` with a known-failures record | `validate` | — | #248, delivered in #254 |
| L02 | A skipped test is not a pass | `evidence` | — | #256 |
| L03 | Feature selection, scenario identity and binding, JSON report | `evidence` | L02 | #259 |
| L04 | Thresholds and measurements, with cost and authority classes | `evidence` | L03 | #261 |
| L05 | Results must belong to the current commit and revision | `evidence` | L03 | #263 |
| L06a | Scenarios, shared steps and criteria cannot be weakened by the change they judge | `conform` | L03 | #267 |
| L06b | Existing tests, test support and protected files cannot be weakened | `conform` | L06a | #269 |
| L07a | One answer per feature from `conform`: done, continue or escalate | `conform` | L02–L06 | #271 |
| L07b | Feature artifact checks on a level-free installation, through `conform` | `conform` | L07a | #273 |
| L08a | Evidence gate templates judge the features a change touches | payload, `evidence` | L07 | #275 |
| L08b | The generated pipeline judges every feature a change touches | pipeline | L08a | #277 |
| L09 | Push verification runs to the Product Definition Graph | CI step | L08, E1 | not opened |
| L10 | OpenTelemetry exporter | optional extra | L07 | not opened |
| L11 | Opt-in pack: skills, Claude Code guidance, prompt writer, run records | pack | L07 | not opened |

The order after L03 is provisional. The pilot decides it. E1 is a `discovery-engine` change (Section 7).

### L01 — Feature-scoped `validate` with a known-failures record (delivered)

`--feature`, `--known-failures`, `--known-failures-digest` and `--print-known-failures` on `govkit validate`, with stable check identifiers. The contract is ADR 0021 and `docs/KNOWN_FAILURES.md`. It serves legacy installations; on a level-free installation it selects no feature (Section 3.2). `govkit conform` keeps its positional feature codes; aligning them is #253.

### L02 — A skipped test is not a pass

`govkit evidence` reads the skipped count and skipped test cases from JUnit XML.

- "Working" is `PASS` only when at least one test ran and none failed, errored or was skipped.
- A report in which tests were skipped is `INCONCLUSIVE`, and the detail gives the counts and names the first few skipped tests.
- A report in which every test was skipped is `INCONCLUSIVE`, as an empty report is today.
- Failures and errors still take precedence and report `FAIL`.

This is a defect against the evidence contract. It changes an exit status from 0 to 1 for projects that have skipped tests, so the changelog must say so. Whether a project may declare accepted skips is decided in L06, not here.

### L03 — Feature selection, scenario identity and binding, JSON report

`govkit evidence --feature <name>` reports on one feature. It reads the scenarios from `features/<name>/acceptance.feature` and binds each one to a test result.

- **Identity.** Each scenario is identified as the graph identifies it, with the same revision digest (decision 18). Copied fixtures pin GovKit's slug rule to `aipos-plugins` and its revision digest to the engine (E3a and E3b).
- **Binding.** Each scenario reports one of: passed, failed, errored, skipped, or missing (no result found). An errored test is kept apart from a failed one, because Section 5 escalates on an error. How a scenario is matched to a JUnit test case is an open question (Section 10).
- **Outcome.** The feature's "Working" outcome is `PASS` only when every scenario passed. Otherwise it is `ERROR` when any scenario errored, else `FAIL` when any failed, else `INCONCLUSIVE`.
- **NFR scenarios.** Scenarios tagged `@nfr-*` are listed with their tags. A passing NFR scenario shows that its test passed. It does not show that the test asserts the value written in the scenario; L04 covers values that are declared as targets.
- **Selection.** A name that matches no feature directory is an error, as in L01.
- **JSON report.** `--json` prints the canonical report (decision 16), with the fields in Section 6.1 and a bundled schema and example.

This increment replaces per-project tests that prove every scenario has a runnable copy.

### L04 — Thresholds and measurements

`govkit evidence --feature <name>` reads the feature's criteria and compares each against a measured result.

- **Identity.** Each criterion is identified as the graph identifies it.
- **Measurement.** A result may carry a measurement: a metric, a value, a unit and optionally a sample size. The format of the file that supplies it is an open question.
- **Comparison.** Where a criterion declares a `target`, the measurement is compared with it. A criterion with only a `threshold` is compared with that threshold.
- **Declared NFR targets.** An NFR value is compared in the same way when it is declared as a target. An NFR value that exists only as scenario prose is covered by its test passing, and the report says the value itself was not compared. Whether NFR values gain a machine-readable form is an open question.
- **Class.** Each criterion has a class: `free`, `paid` or `human`.
  - A `free` criterion with a result reports `PASS` or `FAIL`.
  - A `free` criterion without a result is `INCONCLUSIVE`.
  - A `paid` or `human` criterion without a result is reported as owed. GovKit never starts a paid or human evaluation.
- **Forecasts.** The FIRST and virtue forecasts in `plan.md` remain forecasts. They are not read as results.

As delivered (ADR 0023): the fields are `target` and `execution_class`, and they are added to the backend `eval_criteria` schema only. The three schemas do not share a criterion shape: the data schema lists an `id` with a predicate in words, and the UI schema has no criteria list. Data-form criteria are not compared and prevent `PASS`. Measured scores come from `govkit-eval-results*.json`.

### L05 — Results must belong to the current commit and revision

A result counts only when it was produced from the current commit and names the current revision digest of its scenario or criterion. Anything else is `INCONCLUSIVE`, reported as stale. This is the graph's own rule (Section 3.3), applied locally. How a result file records the commit it came from is an open question.

A local result must also belong to the working tree that produced it. When a tracked or untracked file that the result depends on has changed since the run without a commit (implementation, tests, scenarios or criteria), the commit and the digests can still match. Such a result is `INCONCLUSIVE`, reported as stale. How the working tree is identified, for example by a tree digest recorded with the result, is part of the same open question.

Issue #152 should be rewritten around the verification run contract, or closed.

### L06 — The definition and its tests cannot be weakened by the change they judge

A check on the actual Git diff, composed through `change_conformance.py`, which already captures it.

Split on 2026-11-25. L06a covers scenarios, shared steps and criteria, which need no declaration from the project. L06b covers the rest, which needs the declarations described below.

- **Scenarios.** In `acceptance.feature`, a change may add scenarios. Every scenario that existed at the comparison base must still exist with the same revision digest. A removed or altered scenario is a finding that needs a person.
- **Shared steps.** A `Background` runs before every scenario it covers, and the revision digest does not include it. Any change to a `Background` that existed at the comparison base, at feature or `Rule` level, is a finding that needs a person. So is adding one above existing scenarios.
- **Criteria.** In `eval_criteria.yaml`, a change may add criteria. An existing criterion that is removed or altered is a finding.
- **Existing tests.** A test bound to a scenario at the comparison base may not have lines removed or changed. New tests and new test files are allowed. GovKit cannot judge whether an edit weakens a test, so any edit to an existing bound test needs a person.
- **Shared test support.** A bound test can be weakened through a helper, fixture or settings file it uses, without any of its own lines changing. The project declares its test support paths, and any change to an existing file under them is a finding. GovKit does not trace imports, so with no paths declared the report states that shared test support is not protected.
- **Other protected files.** The known-failures record and the CI workflows by default; datasets, rubrics, thresholds and test settings when the project declares them. Any change is a finding.
- **Declarations come from the comparison base.** The test support paths, the other protected files and the escape markers are read as declared at the comparison base, or from accepted policy held outside the inspected tree, never from the change being judged. A change may add to a declaration, and the addition applies. A change that removes or narrows one is a finding that needs a person.
- **Escape markers.** A project may declare escape markers (skip, xfail, a pending tag). Their count for a feature may fall but not rise against the comparison base.

### L07 — Preconditions, the verdict and `conform` integration

Split on 2026-11-26. L07a is the answer itself, from `govkit conform --feature`. L07b makes the feature artifact checks available on a level-free installation and reuses L01's identifiers and known-failures record. The service reachability precondition below was dropped (maintainer, 2026-11-26): an unavailable service shows as a skipped test, which escalates.

A read-only command composes L02 to L06 into the single state of Section 5, with stable exit codes and structured output.

- Preconditions are checked first: the feature exists, its artifacts are present, result files exist, and required services are reachable where the project declares them.
- The feature artifact checks that `validate` runs today become selectable by capability and reportable through `govkit conform`, so a level-free installation has them. This closes the gap in #220.
- L01's check identifiers and the known-failures record are reused.

### L08 — CI templates use the feature-scoped checks

Split on 2026-11-26. L08a changes the copied evidence gate templates, which have no request file or policy checkout, so they run the feature evidence report for each feature the change touches. L08b gives the generated pipeline the same selection and runs `govkit conform --feature`, which adds the checks on the change itself.

The evidence gate templates for GitHub and Azure, and `ci/README.md`, are updated together to run the feature-scoped checks and to treat `INCONCLUSIVE` as the contract requires.

### L09 — Push verification runs to the Product Definition Graph

An explicit CI step projects the JSON report into a verification run and posts it.

- It runs only in CI, with a service token the pipeline supplies. GovKit stores no credential.
- It sends identifiers, revision digests, outcomes, the build commit and the artifact link. With E1, it also sends measurements.
- It omits measurements when the engine does not accept them (E2).
- A refused run fails the step and changes no local result.

### L10 — OpenTelemetry exporter

An opt-in exporter projects the JSON report into OpenTelemetry events and feature-level metrics (decision 21), for local runs and CI alike. The attribute names follow the current OpenTelemetry semantic conventions for test results and evaluation scores, which must be checked when this increment is designed.

### L11 — Opt-in pack

A declarative pack under `extensions/` with agent-neutral skills for a feature loop and a pull request loop, Claude Code guidance for driving them, a skill that writes the goal prompt from the feature's artifacts, and a schema for self-reported run records. Proactive maintenance entry points are generated but never activated by GovKit.

### 6.1 Fields of a result

Fixed in L03 and L04, because an exporter cannot reconstruct them afterwards.

| Field | Meaning |
|---|---|
| Requirement identifier | `<package>#scenario:<slug>` or `<package>#evaluation:<name>` |
| Revision digest | The scenario or criterion revision that ran |
| Kind | `test` or `evaluation` |
| Outcome | Passed, failed, skipped, error, missing or owed |
| Tags | The scenario's tags, including `@nfr-*` |
| Measurement | Metric, value, unit, and sample size when known |
| Target | The declared target or threshold the value was compared with |
| Class | `free`, `paid` or `human` |
| Source | The tool and result file the outcome came from |

A report also carries the repository, the feature, the build commit, the execution time, a run reference and the report's schema version.

## 7. Changes needed in other repositories

Nothing in `discovery-engine` or `aipos-plugins` has been changed. These are proposals, raised as issues on 2026-11-23: E1 and E2 as discovery-engine#303, E3a as aipos-plugins#108 and E3b as discovery-engine#302. E4 is not yet raised.

| Id | Repository | Change | Needed by | Without it |
|---|---|---|---|---|
| E1 | `discovery-engine` | An optional `measurement` on a verification result: metric, value, unit and an optional sample size. Where the criterion declares a target, the engine compares the value and refuses a run whose outcome contradicts it. | L09, for scores | Runs carry outcomes only; scores reach the graph by no route |
| E2 | `discovery-engine` | A way for a client to learn which verification-run fields the engine accepts, such as a contract version on an existing route. The request model rejects unknown fields today. | L09 | GovKit must be configured by hand to send or omit measurements |
| E3a | `aipos-plugins` | The slug rule and its test pairs published as a versioned fixture beside the identifier reference document. | L03 | GovKit copies the rule and pins a fixture to a commit by hand, as the engine does today |
| E3b | `discovery-engine` | The revision digest rule published with a fixture of scenario text and expected digest, and the content digest rule for a criterion. | L03, L05, L06, L09 | GovKit copies the rule from the engine's source; a difference makes the engine refuse a whole run |
| E4 | `discovery-engine` | A published schema for the verification-run request that GovKit's projection can be validated against. | L09 | GovKit tests against a hand-copied shape |

E3 is split by owner. The engine already follows `aipos-plugins` for identifiers and slugs, so E3a belongs there. Neither part blocks L03, which starts from copied fixtures.

Not proposed:

- **Recording local or pre-baseline runs.** Decision 19 keeps the graph for CI results against a tagged baseline.
- **A paid or human class in the graph.** An owed evaluation shows there as `unverified`, which is accurate.
- **Splitting the graph into its own repository.** Deferred by the maintainer on 2026-11-22. E3a, E3b and E4 are useful either way.

## 8. Pilot repository

The maintainer is creating a pilot repository to try each increment. It replaces the single hand-run trial (L00) of version 0.1. To exercise this plan it needs:

- a level-free installation: `govkit profile apply` then `govkit pack apply`, with `application-governance`, `gherkin-delivery` and `llm-evaluation`;
- a test runner that executes Gherkin scenarios and writes JUnit XML;
- at least three features:
  - one deterministic feature whose scenarios all pass;
  - one with `@nfr-*` scenarios that carry values to test;
  - one with `mode: llm` criteria, including a criterion that is paid or needs a person;
- at least one scenario that skips when a service is unavailable, to exercise L02;
- one older feature left failing, to exercise the known-failures record;
- for L09, a tagged baseline that the graph has indexed.

After each increment, record in the ledger: what the pilot run showed, whether "done" survived an independent rerun, what the agent could not fix, how it read GovKit's output, and the cost.

## 9. Non-goals and risks

Non-goals:

- Invoking, scheduling or supervising an agent.
- Automatic transmission of anything. Exports are explicit and opt-in (decision 17).
- Further changes to `govkit validate`.
- Verifying that tests were written before the code.
- Judging whether an edit to an existing test weakens it. L06 flags the edit for a person.
- Scoring judgement-only dimensions such as "Clear" mechanically.
- Vendor-specific telemetry integrations. Standard OpenTelemetry output only.
- Parity of loop-driving guidance across all three agents in the first release.
- UI project types in the first pass.

Risks:

- **The agent grades its own work locally.** Decision 13 keeps the local result advisory; L05 and L06 limit what a local run can claim.
- **Scenario binding varies by test runner.** L03 is promised only for runners whose JUnit output can be matched to a scenario.
- **An NFR value in prose is not compared.** A test can assert a looser limit than the scenario states. L04 compares only declared targets and says so in the report.
- **L06 will flag legitimate test refactoring.** That is the intended cost of not letting a change edit its own tests unreviewed.
- **The graph does not see a `Background` edit.** The engine's revision digest stops at the scenario, so a changed `Background` leaves every scenario current in the graph. L06 catches it in the change that makes it. Whether the digest should cover it is a question for E3b.
- **Copies of the identity rules can drift.** E3a and E3b give each rule one published fixture; until then copied fixtures pin them.
- **Probabilistic results have no standard file format.** L04 may have to define one.
- **L02 turns some green runs red.** Projects with skipped tests will see `INCONCLUSIVE` where they saw `PASS`.
- **Exports can leak project detail.** Scenario names and failure text may be sensitive. Decision 17 requires an allowlist.
- **Two commands could drift.** `validate` and `evidence` both gain a `--feature` option. L07 brings them under `conform`.
- **The term may not last.** Decision 3 limits the exposure to the pack.
- **Thin evidence.** One legacy pilot and one synthetic level-free installation, until the new pilot reports.

## 10. Open questions

1. **Scenario binding (L03).** Settled on 2026-11-24 from the first pilot's pytest-bdd output: a `govkit.scenario` JUnit property first, then the scenario title against the test name (ADR 0022). Check it against the new pilot.
2. **Measurement file format (L04).** Settled on 2026-11-24: a GovKit results file, `govkit-eval-results*.json`, that the project's evaluation run writes (ADR 0023). No tool writes it today; a project adapts its tool's output.
3. **Machine-readable NFR values (L04).** Settled on 2026-11-24: no new form. A value to be compared is declared as a criterion with a target in `eval_criteria.yaml`.
4. **Recording the commit and working tree (L05).** Settled on 2026-11-24: a separate GovKit step, `govkit evidence --record`, writes a record of the commit, a working tree digest and each result file's digest (ADR 0024). Results with no record are `INCONCLUSIVE`.
5. **Schemas on a level-free installation.** Settled on 2026-11-26: the profile's `repository.project_type` picks the schema, which is read from the schemas bundled with GovKit. With no project type, validation is unknown (ADR 0029).
6. **Accepted skips.** May a project declare a skip as accepted, and if so where, without recreating the escape route of Section 3.1 item 4?
7. **The legacy pilot.** Can it be converted with `govkit migrate`, so that it also exercises the level-free path?
8. **Telemetry consumers (L10).** The first consumer is a custom application reading the JSON. Which OpenTelemetry backend should the exporter be proven against?

## 11. Related issues

- #152 proposes an evidence record and an emission to the graph. Rewrite it around the verification run contract, or close it in favour of L05 and L09.
- #220 tracks profile equivalents for marker-only features. L07b gives feature validation a profile route for one selected feature; the whole-repository route follows in L08.
- #253 aligns `govkit conform`'s feature codes with the named identifiers from L01.

## 12. What changed from version 0.1

Version 0.1 planned L02 to L06 as additions to `govkit validate`, with a new file in which a project declared its verification checks.

- **The definition of done moved.** It is the feature's own scenarios, tests and criteria (decision 10), so the separate declaration file is dropped.
- **The foundation moved.** New installations have no level and `validate` runs no feature checks there, so the work builds on `evidence` and `conform` (decision 11).
- **The order changed.** Skipped results come first, because the defect exists today. Scenario binding moved from fifth to third, because it connects the checks to the definition.
- **The trial changed.** A single hand-run trial became a pilot repository used after every increment.
- **Results became exportable.** One JSON report feeds a custom application, the Product Definition Graph and OpenTelemetry (decisions 16 to 21).

| Version 0.1 | Version 0.2 |
|---|---|
| L00 Hand-run trial | Section 8, the pilot repository |
| L01 Feature-scoped `validate` | L01, delivered |
| L02 Declared verification checks with classes | Dropped as a separate file; the classes move to L04 |
| L03 Skipped and degraded results; escape-marker ratchet | L02 (skipped results) and L06 (ratchet) |
| L04 Protected paths | L06 |
| L05 Machine-readable increments and scenario binding | L03 (scenario binding); machine-readable increments dropped |
| L06 Preconditions and the verdict | L07 |
| L07 Opt-in pack | L11 |
| — | L04 thresholds, L05 commit scoping, L08 CI templates, L09 graph push and L10 OpenTelemetry are new |

## 13. Execution ledger

| Date | Increment | Result | Next |
|---|---|---|---|
| 2026-11-20 | Plan | Version 0.1 written; #248 opened for L01 | Agree plan |
| 2026-11-22 | Plan | Version 0.1 merged as #252 | Start L01 |
| 2026-11-22 | L01 | Delivered in #254 (`af71fa9`): four `validate` options, `known-failures` v1 schema and example, ADR 0021, guide, runtime-only wheel smoke for three agents. Six open points recorded on #248; #253 filed for conform's codes | — |
| 2026-11-22 | Plan | Version 0.2: replanned after finding that new installations have no level, that `govkit evidence` is the level-free foundation, and that the Product Definition Graph already has a verification run contract (Sections 3.2 and 3.3) | Agree version 0.2; decide which Section 7 changes to raise in `discovery-engine`; create the pilot repository; open the epic and the L02 issue |
| 2026-11-23 | Plan | Version 0.2 merged as #255. Proposals raised as discovery-engine#303, discovery-engine#302 and aipos-plugins#108. Epic opened as #257 | Start L02 |
| 2026-11-24 | L02 | #256: `govkit evidence` reads skipped tests from JUnit XML; a run with skipped tests and no failure or error is `INCONCLUSIVE` for "Working" and a skipped test has no duration for "Fast". The run exits 1 even when another dimension passes; a dimension with no report still does not block | Open the L03 issue; settle scenario binding from the pilot's output |
| 2026-11-24 | L02 | Delivered in #258 | Start L03 |
| 2026-11-24 | L03 | #259: `govkit evidence --feature` with mirrored scenario identity (fixtures produced by the engine's reader at `3806d64`), binding by property then title, JSON report schema version 1, ADR 0022. The commit, run reference and execution time are left to L05 as optional fields | Check binding against the new pilot; open the L04 issue |
| 2026-11-24 | L03 | Delivered in #260 | Start L04 |
| 2026-11-24 | L04 | #261: criteria in the feature report, mirrored criterion identity and comparison (fixture produced by the engine at `3806d64`), the `evaluation-results` file, `target` and `execution_class` on backend criteria, ADR 0023. Found that the data and UI criteria schemas have a different shape; data-form criteria are not compared and prevent `PASS` | Open the L05 issue. Data-form criteria wait for a data architect's review of GovKit (maintainer, 2026-11-24); no issue is raised here or in `discovery-engine` until then |
| 2026-11-24 | L04 | Delivered in #262 | Start L05 |
| 2026-11-24 | L05 | #263: `govkit evidence --record` and the freshness check, a Git-based working tree digest that leaves out the result files, `provenance` in the report, ADR 0024. A stale result keeps its state and loses its authority. The plan's Section 5 treats stale as escalate; a stale local result needs a rerun, which L07 should treat as continue | Open the L06 issue |
| 2026-11-25 | L05 | Delivered in #264 | Before L06, let a project say where its test results are (maintainer, 2026-11-25; the first runner to verify is Python) |
| 2026-11-25 | — | #265: `govkit evidence --record --junit PATTERN`, kept in the record and read by the report, ADR 0025. Stated matches must be JUnit XML inside the target. Also closes a gap in L05: a recorded result file that was deleted left the rest current. Verified with a real pytest-bdd run; other runners are not verified, and TRX is not read | Open the L06 issue. Bind against other runners in L08 |
| 2026-11-25 | — | #265 delivered in #266 | Start L06 |
| 2026-11-25 | L06a | #267: `change:definition` in change conformance and the pure `definition_change.py`, ADR 0026. L06 was split: this half needs no project declaration. Criteria are compared by name, stricter than the graph's file digest. A file whose criteria are not all named is compared whole; no data-form rule is defined | Open L06b: bound tests, test support, protected files, declarations and escape markers. It needs a decision on where a level-free project declares paths |
| 2026-11-25 | L06a | Delivered in #268 | Decide where L06b's declaration lives |
| 2026-11-25 | L06b | #269: `change:protected` and the pure `protected_change.py`, with an optional `protected` section in the accepted conformance configuration, ADR 0027. Maintainer decisions: the declaration lives in accepted policy, and existing test files are additions-only. Differs from the L06 text above in three ways: tests are protected by declared path, not by binding to a scenario; nothing is protected by default; and no declaration is read from the comparison base. An inserted line inside an existing test is not seen | Open the L07 issue. L07 decides the level-free entry point and whether a project-held declaration is needed |
| 2026-11-26 | L06b | Delivered in #270 | Open the L07 issue |
| 2026-11-26 | L07a | #271: `govkit conform --feature`, the pure `feature_verdict.py`, the `evidence:feature` check and the `govkit.feature-verdict` document, ADR 0028. Maintainer decisions: the answer comes from `conform`; stale, unrecorded and missing free results give continue; no service reachability check. L07 was split. `evidence:feature` passes on result files as a local check, so a local done is a stop condition only. A required check that cannot pass locally ends in escalate | Open L07b: feature artifact checks on a level-free installation. It needs a decision on which capability selects them and which `eval_criteria` schema applies |
| 2026-11-26 | L07a | Delivered in #272 | Decide how L07b selects its checks |
| 2026-11-26 | L07b | #273: `feature_artifacts.py` adds `feature:<identifier>` checks to `govkit conform --feature`, ADR 0029. Maintainer decisions: `gherkin-delivery` selects the level 4 checks and `llm-evaluation` adds level 5; all are required except the forecast, which is advisory; the profile's `project_type` picks the schema and nothing is guessed; the selected feature only. The report's overall state is a warning at best because the forecast is never a pass | Open L08: CI templates, and the whole-repository run with the known-failures record |
| 2026-11-26 | L07b | Delivered in #274 | Decide how CI selects features |
| 2026-11-26 | L08a | #275: `govkit evidence --changed-since BASE` and both evidence gate templates (tests, record, changed features). Maintainer decisions: L08 is two PRs; CI judges the features a change touches; anything but a pass fails the job and the state is shown; the test step stays a placeholder, with pytest-bdd the only verified runner. No JSON form for several features. The templates do not check the change itself | Open L08b: the generated pipeline runs `conform --feature`. It needs a feature input and a way to run several features |
| 2026-11-26 | L08a | Delivered in #276 | Decide how the pipeline handles several features |
| 2026-11-26 | L08b | #277: `inspect_change(changed_features=True)`, the pipeline setting `"features": "changed"`, named checks such as `evidence:feature[<name>]`, the optional `feature_output` input and the `govkit.feature-verdicts` document, ADR 0030. Maintainer decisions: one run with one answer for each feature; the engine selects; a setting, off by default; the record and exit status stay. No overall state across features. The entry point does not run tests or record results | Open L09: push verification runs to the Product Definition Graph. It depends on E1 and E2 in `discovery-engine` |
