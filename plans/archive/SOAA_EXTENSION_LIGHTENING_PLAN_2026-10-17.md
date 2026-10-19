# SOAA Extension Lightening Plan

**Status:** Proposed — 2026-10-17. Plan only; nothing in
`extensions/skill-oriented-agent-architecture/` has changed. Increment 0's ADR
must be accepted before any payload increment starts.

Revise the bundled `skill-oriented-agent-architecture` extension so a team with a
handful of fixed skills can adopt it at a cost proportional to what it builds.
The plan adds a three-rung conformance ladder, replaces SOAA-specific names with
widely used ones, scales the preflight by rung, cuts the precedence stack to what
GovKit needs, and separates the two meanings of "skill". It also names what the
first consumer must demonstrate before Rung 1 counts as proven.

This is **payload** work. The plan touches no installer module (`cli/*.py`).
The single exception is increment 4, which converts the manifest to an explicit
`capability_pack` block that the existing loader already supports. The original
build record is `plans/SKILL_ORIENTED_AGENT_ARCHITECTURE_EXTENSION_PLAN.md`. This
plan supersedes its "Design rules" wherever the two disagree.

Virtues: **Proportionate** (the cost of adoption follows what the system does),
**Plain** (the patterns carry their common names), **Honest** (GovKit claims a
rung only once an executed suite supports it), **Traceable** (every SOAA
identifier survives in a Source alignment table).

## Motivation (evidence)

### 1. Adoption cost is flat, not proportional

| Requirement | Where | Cost for a three-skill, single-agent team |
|---|---|---|
| Map all eighteen logical roles to six attributes each | `SKILL_ORIENTED_AGENT_ARCHITECTURE.md:83-102` | 108 preflight cells, most "not applicable" |
| Twelve-item preflight for every feature | `SKILL_ORIENTED_AGENT_ARCHITECTURE.md:137-152` | Same list whether or not the feature touches selection or delegation |
| Eight-element skill tuple; "every production skill must declare all eight areas" | `SKILL_CONTRACT.md:16-33` | Applicability, dependencies and evaluation obligations for skills that trusted code binds by name |
| Four-stage selection pipeline | `SKILL_SELECTION_AND_ACTIVATION_CONTRACT.md:15-24` | Irrelevant to fixed binding, yet shipped in a set that agents load for any `*select*`, `*policy*` or `*permission*` path |
| Twelve task states and thirteen activation states | `RUNTIME_STATE_AND_EXECUTION_CONTRACT.md:51-71, 108-127` | Handoff and suspension states with no handoff or suspension in the system |
| "List every applicable SOAA contract" and "Classify every relevant component" | `manifest.yaml:164-166` | Full classification for each feature |

The extension has no notion of "applies only when the system does X". Every
requirement binds every adopter.

### 2. Known patterns appear under new names

The contracts use the established patterns but rename them. Examples: `owner_epoch`
is a fencing token; "authoritative durable envelope" is a transactional outbox;
"quiescence" means drained; "deterministic admission" is an eligibility filter;
"capability tuple" is a scoped permission; "fresh operation authorization" is a
time-of-use check; a "model judge" is an LLM-as-judge.

The same concept also carries two names inside the extension:

- **Operation record:** "OperationRecord" in `RUNTIME_STATE_AND_EXECUTION_CONTRACT.md:172` and "Operation ledger" in `RESILIENCE_AND_RECOVERY_CONTRACT.md:86`.
- **Activation lifecycle:** defined in full twice, in `RUNTIME_STATE_AND_EXECUTION_CONTRACT.md:108-137` and in `SKILL_SELECTION_AND_ACTIVATION_CONTRACT.md` ("Activation lifecycle").
- **SOAA package profile:** stated twice, in `SKILL_CONTRACT.md:61-140` and in `SKILL_LIFECYCLE_AND_INTEROPERABILITY_CONTRACT.md` ("SOAA profile for Agent Skills packages").

### 3. Conformance is unfinished, and the docs say so

`README.md:104-106` states that the suite, assertions, schemas, fixtures and
reference runtime are future work. `AGENT_RUNTIME_STACK.md:18-21` says no
blocking gate ships. The manifest's `implementation_profiles[].gate` field is
reserved and unused. A team cannot claim anything today. That is honest, but it
also gives no target short of all 206 assertions.

### 4. The governance surface outweighs the architecture

`README.md:108-117` defines a six-level precedence stack (invariant, decision
record, midpoint amendment, root cross-module rule, module contract, GovKit
guidance). It also says "an unresolved conflict blocks implementation". A
consuming team holds only level 6: the SOAA source set is not shipped, so levels
1–5 are unreadable to the people the rule binds.

### 5. "Skill" means two things, and the text says so only once

`README.md:28` says the extension "is distinct from the Agent Skills packages
used by Codex, Claude Code, or Copilot". `README.md:30-34` then explains the
`soaa/` side directory. Nothing says which meaning applies to:

- a GovKit `govkit-*` delivery skill
- a plain Agent Skills pack (such as `aipos`) moved into a product runtime
- an A2A AgentSkill

Nothing says what such a pack must add. The `aipos` pack (`aipos-plugins/plugins/aipos/`)
is the concrete case: fourteen `SKILL.md` packages. All fourteen have `evals/`,
twelve have `references/` and eight have `scripts/`. None has `soaa/` or any
`soaa-*` metadata.

### 6. The intended audience is never pointed here

Every L5 entry point loads the extension only when `eval_criteria.yaml` declares
`multi_agent: true`. That covers `agents/*/claude-md/l5-backend-*.md:28`, the
`govkit-architecture-preflight` skill (Section 15),
`governance/backend/templates/l5-architecture-preflight.md:219-237` and
`l5-plan.md:106`. A single agent with three fixed skills is not multi-agent, so
the guidance never reaches it. This finding is not in the review brief; it
changes increment 3.

### 7. Constraints found while reading

| Constraint | Source | Consequence for this plan |
|---|---|---|
| Contract-set `capabilities` become the pack's public `provides` IDs | `cli/pack_loading.py:55-80` | No capability token may be renamed or dropped. A profile can select any of them. Moving a document between sets is safe because `provides` is the union. |
| Windows wheel member budget is 116 characters | `tests/wheel_windows_smoke.py`, `tests/test_wheel_windows_paths.py` | New files under `cli/ext/skill-oriented-agent-architecture/docs/backend/architecture/` (68 characters) get at most 48-character names. New top-level folders (42-character prefix) are cheap. |
| Two sentences and four backticked outcomes are pinned verbatim | `tests/test_evidence_contract.py:47-54` | The sentences are "A producer self-check is advisory" and "never commits its own final gate". The outcomes are `PASS`/`FAIL`/`INCONCLUSIVE`/`ERROR`. They are already plain, so keep them. |
| Phrase pins in the extension's own tests | `tests/test_skill_oriented_agent_architecture.py:121-200` | Pinned phrases include "Eighteen", "Candidate retrieval", "Deterministic admission" and "task controller transition". Update the tests first, in the increment that changes the text. |
| Contracts must stay product-neutral | `test_contracts_are_provider_and_framework_neutral` | Plain pattern names are fine; product names stay in `AGENT_RUNTIME_STACK.md` only. |
| Bundled packs carry a version; different content at one version needs a digest pin | `docs/CAPABILITY_PACKS.md:45` | Bump `version` 0.1.0 → 0.2.0 in increment 2 and hold it until release. If a release ships mid-series, bump again. |
| Reviewer / approver / execution owner / accountable principal roles are reused verbatim elsewhere | `plans/AIPOS_BEHAVIOR_CONTRACT_PLAN.md:77`, `tests/test_approval.py:9` | Do not rename these four roles. The brief requires keeping them anyway. |
| The multi-agent CI gate greps four topology headings | `ci/github/multi-agent-gate.yml` (Orchestrator, Specialist Agents, Routing Logic, Failure Modes) | Keep those headings in `agent_topology.md`. The gate then needs no change in either CI system. |
| Only invariant ranges are in this repo | Every Source alignment table | The demotion register cites ranges. Exact per-invariant IDs need the SOAA source set (increment 0). |

## Decisions

### D1. Three rungs, chosen by what the system does

"Profile" already means four things here: GovKit declarative profile,
implementation profile, SOAA package profile and SOAA named profile. "Level" is
taken by GovKit L3–L5. The ladder therefore uses **rungs**.

| Rung | Name | A system is on this rung when it has… | Adds |
|---|---|---|---|
| 1 | **Core** | One agent run per task; skills bound by trusted code (fixed), chosen from a pinned menu (D1a), or switched one at a time by a trusted workflow (D1b); optional human takeover | The five rules, passive packages, operation records, durable approvals, completion gate |
| 2 | **Catalog** | Skills chosen from a catalog that changes independently of the code; or memory that outlives a task; or retrieved resources as context | Selection pipeline, release lifecycle and revocation, full permission model, context snapshots and memory, full failure handling, full evaluation specs, SOAA package format, MCP mapping |
| 3 | **Multi-agent** | More than one agent run per task (subtask delegation, ownership handoff, remote agents), or a multi-skill plan beyond D1b: skills active at once, joined results, or a plan the model writes or changes | Multi-skill plans, delegation and handoff, A2A mapping, live release migration, protocol version policy, portability claims |

**A team's rung is the highest rung whose trigger its system has.** It is not a
choice. A system that selects skills dynamically must meet Rung 2. Most
requirements moved off Rung 1 are therefore *trigger-gated*: they still bind every
system that has the feature they govern. The few genuine *relaxations* (items that
SOAA v0.2 requires even of a fixed-skill system) are marked as such in the
demotion register. They need the upstream acknowledgment described in D7.

`multi_agent: true` in `eval_criteria.yaml` implies Rung 3. D9 says how a coding
agent works out the rung and checks it against what is declared.

**D1a — pinned-menu choice stays on Rung 1.** Letting the model choose among a
small pinned set is how Claude Code itself uses skills. The extension's first
consumer will want it too. Rung 1 allows this when all four conditions hold:

1. Trusted code fixes the menu per route or task type, and every entry is eligible for every task that route accepts.
2. The menu always includes a no-skill option.
3. The choice is recorded with the task.
4. Binding happens in trusted code and grants nothing beyond the task's permissions.

Anything that retrieves from a catalog, filters per task, or routes through an
approval to become eligible is Rung 2. This is open question Q4.

**D1b — sequential workflow binding stays on Rung 1.** In this pattern, one agent
loads different skills as a workflow moves through its states. SOAA's selection
contract already treats the pattern as fixed binding: in its "Fixed workflow"
mode, an approved workflow names the exact skill for each step and nothing is
ranked. Rung 1 allows it when all five conditions hold:

1. Trusted code owns the state machine and the state-to-skill map, with each skill pinned by digest. The model may propose a transition; the task controller commits it (R-1).
2. Only one skill is active at a time. The previous binding ends before the next one starts.
3. Data moves between skills only through task records that trusted code writes. One skill never hands data directly to another.
4. The map is fixed in reviewed code or configuration, versioned with the release. Nothing amends it at runtime.
5. Each switch recalculates permissions for the incoming skill. Tools allowed for the previous skill do not carry over.

What moves the system up:

- **Rung 2:** the map resolves a skill from a catalog, for example "the latest skill for this state" from a registry (T1).
- **Rung 3:** skills run in parallel, results from several skills are joined, or the model writes or amends the plan (T5).
- **Model-chosen states:** if the model picks the next state freely, rather than proposing it for the task controller to commit, the model is choosing the skill. That is selection: D1a's conditions apply, or the system is Rung 2.

**Caveat.** SOAA requires a versioned composition plan for any run that uses
several skills (demotion register row 15). A state machine versioned with the
release meets the intent: an exact, reviewed, versioned sequence. It omits the
plan structure for parallel branches, joins and amendment, because none of those
exist under the five conditions. Row 15 records this as a relaxation, and open
question Q17 takes it upstream.

### D2. Contract-set mapping

Topic sets stay, because they drive progressive loading by touched files. Rung
labels are added at section level. Rung 1 consolidates into one document a small
team reads end to end.

| Contract set | After | Rung | Change |
|---|---|---|---|
| `soaa_core` | `SKILL_ORIENTED_AGENT_ARCHITECTURE.md` | 1 | Rewritten as the self-contained Rung 1 contract. `SKILL_CONTRACT.md` and `RUNTIME_STATE_AND_EXECUTION_CONTRACT.md` leave this set. |
| `soaa_selection_authority` | `SKILL_SELECTION_AND_ACTIVATION_CONTRACT.md`, `AUTHORITY_AND_APPROVAL_CONTRACT.md` | 2 | Rung 1 authority rules move to the core document; the remainder is labelled Rung 2. |
| `soaa_context_resilience` | `CONTEXT_MEMORY_AND_RESOURCE_CONTRACT.md`, `RESILIENCE_AND_RECOVERY_CONTRACT.md` | 2 (child budgets: 3) | Rung 1 operation and retry rules move to core. |
| `soaa_assurance` | `EVALUATION_EVIDENCE_AND_COMPLETION_CONTRACT.md` | 2 | Rung 1 gate rules move to core; the pinned sentences stay in this file too. |
| `soaa_ecosystem` | `SKILL_LIFECYCLE_AND_INTEROPERABILITY_CONTRACT.md`, **`SKILL_CONTRACT.md`** | 2 (A2A, migration, portability: 3) | `SKILL_CONTRACT.md` joins the set that already matches `**/SKILL.md` and `**/soaa/manifest.yaml`. The duplicate package-profile text collapses into `SKILL_CONTRACT.md`. |
| **`soaa_orchestration`** (new) | `RUNTIME_STATE_AND_EXECUTION_CONTRACT.md` | 2 (full lifecycles), 3 (plans, delegation, handoff) | `applies_to`: `*orchestrat*`, `*workflow*`, `*delegat*`, `*handoff*`, `*task*`. It carries the capability tokens it needs; `soaa_core` keeps all five of its tokens. |

All 32 capability tokens are preserved. With the pack ID, the loader reports 33
`provides` entries. No file is renamed, because the
three agents' rules, the L5 instructions, the CI gate comment and the README link
to these exact paths. No new contract file is added.

### D3. Rung 1 contract content (what moves from `soaa_core` and what moves into it)

**The five rules**, stated plainly and numbered R-1 to R-5 for reference:

1. **R-1:** Model output is a proposal; a trusted component commits every consequential transition.
2. **R-2:** A skill supplies procedure. It never owns a task, grants permission, or holds state.
3. **R-3:** One owner per task; a former owner's commands are fenced after transfer.
4. **R-4:** Approvals and external operations are durable records, never prompt state.
5. **R-5:** Only an evaluator completes a task; skill success and model confidence do not.

**Also kept on Rung 1, plainly worded:**

- **Passive package rule:** loading executes nothing; scripts run only through the script runner after an authorized, recorded call.
- **Proposal-to-commit ownership table:** the Rung 1 rows plus the delegation row marked "Rung 3".
- **Human roles:** reviewer, approver, human execution owner and accountable principal stay distinct.
- **Skill boundary:** the "skill versus application code" table.
- **Prohibited patterns:** a short list.
- **Binding modes:** fixed, pinned menu (D1a) and sequential workflow (D1b), each with its conditions.
- **Minimum state machine:** `READY`, `RUNNING`, `WAITING` (with a durable reason: input, approval or dependency), `VERIFYING`, `COMPLETED`, `FAILED`, `CANCELED`. Human takeover is an ownership transfer, recorded as a new owner plus a new fencing token.
- **Skill binding states:** `ACTIVE`, `SUCCEEDED`, `FAILED`, `STOPPED`, `ESCALATED`, `ACTIVATION_FAILED`. These are kept separate from task state.
- **Operation record:** an idempotency key, written before the call. Unknown outcome is a distinct result; reconcile before any retry. Retries are bounded with one retry owner.
- **Timeouts and limits:** a timeout on a mutating call is never treated as failure. Every task has a finite budget (time, model calls, tool calls, cost), and exhaustion stops work visibly.
- **Time-of-use authorization:** a revoked or expired approval blocks the next call.
- **Instruction precedence in three tiers:** policy and accepted task, then active skill instructions, then everything else as data.
- **Completion gate:** outcomes `PASS`/`FAIL`/`INCONCLUSIVE`/`ERROR`, with evidence levels 0–3 bound at acceptance. A producer self-check is advisory; the task owner never commits its own final gate. An LLM-as-judge is never the sole blocking check for authority, side effects, evidence integrity or state correctness.
- **Evidence and recovery:** evidence is append-only and commits with the state change. Restart works from durable records without a provider transcript.
- **Exact pins:** skills are pinned by exact digest, and a mutable `latest` never identifies behavior.
- **Rung 1 assertions R1-01 … R1-22** (listed under "Reference implementation"; R1-22 applies only to sequential workflow binding).

**Moved off Rung 1:** everything in the demotion register below.

### D4. Preflight by rung

`architecture_preflight.md` declares the rung first, then answers only that
rung's list. Today's preflight is twelve items plus 18 roles × 6 attributes.

**Rung 1 (ten items, eight to ten roles):**

1. Rung determination (D9): the six trigger answers with evidence, the computed rung, the declared feature rung and the recorded system rung.
2. Accountable principal.
3. Where a task is accepted and who owns it; how ownership transfer is fenced.
4. The skills: name, pinned digest, binding mode (fixed, pinned menu, or sequential workflow with its state-to-skill map), the tools each may request, and whether it ships scripts.
5. Consequential transitions and their commit owner (the proposal-to-commit table, filled in).
6. External side effects: effect type, idempotency key and reconciliation route.
7. Approval points: approver role, scope and expiry.
8. Completion: evidence level and the evaluator or verifier that decides each acceptance criterion.
9. Budget limits.
10. Role map. Each role gets four columns: component, records it writes, trusted (yes/no), proving test.

The Rung 1 roles are task controller, agent loop, authorization service, tool
gateway, completion gate, state store, evidence log and skill registry (a pinned
list). Two more apply when relevant: model gateway when an LLM is called, and
script runner when skills ship scripts. That is 8 required plus 2 conditional.

**Rung 2 adds:**

- Roles: skill binder, context builder, resource gateway, memory store and request adapter (15 total).
- The full six-column role map: adds ports, trust boundary and deployment.
- Preflight items: catalog and release lifecycle, selection pipeline and approval routes, memory and resource trust, revocation policy, and evaluation specs.

**Rung 3 adds:**

- Roles: workflow engine, delegation service and agent directory (18 total).
- Preflight items: multi-skill plan, delegation versus handoff per edge, remote protocol versions, child budgets.

The manifest's `agent_guidance.architecture_preflight` is rewritten to match.
`l5-architecture-preflight.md` Section 15 and `govkit-architecture-preflight`
Section 15 trigger on "uses agent skills" (D8) and branch by rung.

### D5. Precedence: three tiers for consumers, one rule for maintainers

**For a consuming team:**

1. **R-1 to R-5 and the passive package rule.** No ADR waives them. A conflict touching them blocks *the affected change* and goes to architecture review.
2. **The contract for the team's rung.** A more specific section wins over a general one. Any deviation needs an ADR in the consuming project.
3. **`AGENT_RUNTIME_STACK.md`.** It is advisory: the contract wins, and any deviation needs an ADR (unchanged).

**For GovKit maintainers:** SOAA v0.2 is the upstream source. A divergence between
this guidance and the SOAA source is a GovKit defect. Fix it, or record it in the
README's "Deviations from SOAA v0.2" list with its SOAA identifier. Consumers never
need the SOAA source to resolve a conflict.

The blocking scope narrows from "implementation" to "the affected change". The
upstream midpoint amendments (`SOAA-MID-001`–`006`, `plans/SKILL_ORIENTED_AGENT_ARCHITECTURE_EXTENSION_PLAN.md:13`)
and the root cross-module rule are traced in increment 0, not ranked in consumer
guidance. Whether SOAA itself makes the six-level order normative is open
question Q11.

### D6. Two meanings of "skill"

A table opens `SKILL_CONTRACT.md` and is summarized in the README:

| You have… | It lives in | It is run by | Governed by |
|---|---|---|---|
| A GovKit delivery skill (`govkit-*`) | `.claude/skills/`, `.agents/`, `.github/skills/` | Your coding agent, while you build | GovKit core. **Not this extension.** |
| An Agent Skills package | A folder with `SKILL.md` | Any Agent Skills host | The Agent Skills specification |
| A **governed skill** | An Agent Skills package that *your product's runtime* binds | Your product's runtime, in production | This extension, at your rung |
| An A2A AgentSkill, MCP prompt or tool descriptor | A remote system | Someone else | An untrusted claim. **It is not a skill.** |

**What a Claude Code skill pack must add to become a governed skill:**

- **Rung 1: nothing inside the package.** The runtime supplies what Claude Code supplied:
  - It pins each package by digest.
  - It keeps a registration record per skill: name, version, digest, inputs and outputs, tool ceiling (`allowed-tools` treated as a ceiling, never a grant), stop and escalation conditions.
  - It runs `scripts/` only through its script runner.
  - It replaces Claude Code's interactive permission prompt with its authorization service and durable approval records. A human answering a terminal prompt is not an approval record.
  - It binds skills in trusted code, from a pinned menu (D1a), or through a sequential workflow (D1b). Claude Code's own model-invoked choice by `description` would be Rung 2 selection.
- **Rung 2: add the SOAA package format** to the package itself:
  - `soaa/manifest.yaml`
  - the four flat `soaa-*` metadata keys
  - the evidence-profile, compatibility and provenance files
  - two-stage validation

  Existing `evals/` folders become the admission and regression suites. This is what lets a package move between catalogs and runtimes with its governance attached.

### D7. Claims are GovKit claims until SOAA names the rungs

A Rung 1 claim reads "GovKit SOAA guidance, Rung 1, version 0.2.0". It is never
"SOAA v0.2 conformance". SOAA's conformance boundary already speaks of a "named
profile" (`EVALUATION_EVIDENCE_AND_COMPLETION_CONTRACT.md`, "Conformance
boundary"). Increment 0 proposes the three rungs upstream as named profiles. Until
SOAA accepts that, the relaxations below are GovKit deviations and are listed as
such.

### D8. Trigger: "uses agent skills", not "multi-agent"

The new feature declaration is `agent_skills_rung: 1 | 2 | 3` in
`eval_criteria.yaml`. The feature's author sets it when writing the spec. The L5
instructions, preflight Section 15 and the plan template load the extension when
it is present, or when D9 step 4 finds an undeclared feature that needs it.
`multi_agent: true` keeps working and implies `agent_skills_rung: 3`. The
multi-agent CI gate is unchanged. A CI check on the declared rung is not part of
this plan (see Out of scope). This is open question Q5.

### D9. How the coding agent determines the rung

A declared value alone is not enough: nothing would notice a feature that says
Rung 1 while its code adds a memory store. The agent therefore derives the rung
itself, and a human resolves any disagreement. The agent never lowers a rung.

**1. Trigger questions (the primary control).** In preflight, the agent answers
six yes/no questions. Each answer cites its evidence: a spec line, a scenario, an
NFR or a file. The computed rung is the highest rung with a "yes".

| # | Question | "Yes" means at least |
|---|---|---|
| T1 | Are skills chosen from a catalog that can change without a code change, or filtered per task (anything beyond D1a's pinned menu)? | Rung 2 |
| T2 | Does the system keep memory that outlives a single task? | Rung 2 |
| T3 | Does the model receive retrieved resources (documents, search results, MCP resources) as context? | Rung 2 |
| T4 | Can one task involve more than one agent run (subtasks, handoff, parallel branches)? | Rung 3 |
| T5 | Does a task have several skills active at once, join results from several skills, or follow a plan the model writes or amends? (One skill at a time switched by a trusted workflow, D1b, is "no".) | Rung 3 |
| T6 | Does the system send work to, or accept work from, remote agents (for example over A2A)? | Rung 3 |

"Unsure" is not an answer. The agent stops and asks; it never resolves doubt
downward.

**2. A human confirms; the agent never lowers.**

- **Computed rung higher than declared:** preflight blocks. A human either raises the declaration or changes the design to remove the trigger, and the preflight records which.
- **Computed rung lower than declared:** the agent reports it and keeps the declared rung. Declaring higher is allowed, because it is stricter.
- **Equal:** the agent proceeds.

**3. One rung for the system.** The system rung is the highest rung across its
features. It is recorded once, as an "Agent skills rung" line in the project's
`docs/backend/architecture/TECH_STACK.md`, which agents already read. That line
replaces today's agent-runtime comment in the baseline and in the five backend
stack overlays. Raising the system rung needs an ADR in the consuming project.

- **Feature rung above system rung:** preflight blocks until the ADR raises the system rung.
- **Feature rung below system rung:** allowed. The feature's preflight answers its own rung's list, but it must not weaken controls the system rung already requires.
- **No line in `TECH_STACK.md`:** the system rung is undeclared and the agent asks. This is the normal case for existing installs, because `TECH_STACK.md` is never overwritten once present.

The system rung also decides which assertion suite the project must pass before
it claims a rung.

**4. Undeclared features that need it.** The extension is installed, but neither
`agent_skills_rung` nor `multi_agent` is set, and the feature touches paths matching
`soaa_core`'s `applies_to` patterns. In that case the agent stops and asks whether
the feature uses governed skills. If the answer is yes, it runs step 1. Without the
extension installed, this step does nothing. That keeps an ordinary
task-tracking app from tripping over `*task*`.

**5. Path backstop (a heuristic, not the control).** The manifest gains two
lists of path patterns:

- `agent_guidance.rung_2_trigger_paths`: for example `**/*memory*`, `**/*catalog*`, `**/*retriev*`, `**/*rank*`, `**/*embedding*`
- `agent_guidance.rung_3_trigger_paths`: for example `**/*delegat*`, `**/*handoff*`, `**/*subtask*`, `**/*a2a*`, `**/*composition*`

The existing schema already allows them, because `agent_guidance` values are
string arrays. They are deliberately not the contract sets' `applies_to`
patterns. Those cover Rung 1 concerns too: `*approval*`, `*permission*` and
`*retry*` all appear in a Rung 1 system. Patterns that Rung 1 code legitimately
uses, such as `*registry*` for the pinned skill list, are excluded.

When a feature declares rung N and touches a path in a higher rung's list, the
agent flags the mismatch and re-answers the matching trigger question, citing the
file. The patterns miss a memory store in `notes.py` and flag a `ranking.py` that
sorts invoices. That is why step 1 is the control and this is only a backstop.

**6. Later, in CI.** The same comparison, between the declared rung and the
trigger patterns of the changed paths, can become a pack check. It is out of
scope here.

## Demotion register

Nothing is removed. Every row is either a demotion to a higher rung or a
replacement on Rung 1 with a smaller equivalent.

**Kind:**

- **T (trigger-gated):** the requirement binds every system that has its trigger, so it is not weakened.
- **X (relaxation):** a fixed-skill system no longer has to meet it. X rows are D7's deviations until SOAA names the rungs.

**IDs:** decision IDs are taken from each contract's Source alignment. Invariant
IDs are the contract's declared range. Increment 0 replaces each range with exact
IDs.

| # | Requirement today | Goes to | Kind | SOAA identifiers | Reason |
|---|---|---|---|---|---|
| 1 | Map all 18 logical roles | R1: 8+2; R2: 15; R3: 18 | T | SOAA-001/003 (unclaimed by any contract; confirm in inc. 0) | The roles not mapped on Rung 1 own features that Rung 1 systems do not have. |
| 2 | Six attributes per role | R1: 4 columns; R2: 6 | X | as #1 | Ports, deployment and trust-boundary detail add no assurance on a single-process Rung 1 system; "trusted yes/no" is kept. |
| 3 | Twelve-item preflight for every feature | R1: 10 items | X | as #1 | Items for selection, context and delegation move with their triggers. |
| 4 | Twelve port families | R1: task, authorization, tool, model, evaluation, evidence; rest R2/R3 | T | as #1 | Selection, composition, delegation and discovery ports exist only on higher rungs. |
| 5 | Eleven verification families | R1: state/concurrency, authority/denial, injection, side effect/idempotency, restart, completion/evidence | T | as #1 | The others test Rung 2 and 3 features. |
| 6 | All eight skill-tuple areas declared | R1: identity, procedure, termination, interface, permission ceiling; R2: applicability, dependencies, evaluation obligations | X | SOAA-002, SOAA-004; INV-006–020 | Applicability and dependencies drive dynamic selection. On Rung 1, evaluation criteria sit on the task, not the skill. |
| 7 | SOAA package format (`soaa/`, four keys, two-stage validation) | R2 | X | SOAA-019; INV-175–182 | With fixed binding the runtime holds the registration record. The format matters when packages move between catalogs or runtimes. |
| 8 | Release identity includes `soaa_profile_version` | R1: name, version, digest; R2: full tuple | X | SOAA-018, SOAA-019; INV-147–206 | Profile version only exists with the package format (#7). |
| 9 | Separate task offer record; rejected offers preserved | R2 | X | SOAA-005; INV-001–005 | Rung 1 keeps an explicit acceptance point that creates a task with one owner. |
| 10 | Twelve task states | R1: 7 states; `SUSPENDED` and distinct `WAITING_*`: R2; `HANDOFF_PENDING`, `HUMAN_CONTROLLED`: R3 / owner change | T | SOAA-005, SOAA-010–013; INV-038–067 | Collapsed waits keep a durable reason. Human takeover remains an owner transfer with fencing. |
| 11 | Task revision with revalidation | R2; R1: accepted terms are immutable and a change creates a new task | — (stricter) | SOAA-005; INV-038–067 | Rung 1 is stricter, not weaker. |
| 12 | Twelve-row record-ownership table | R1: task, binding, approval, operation, gate, evidence; rest R2/R3 | T | SOAA-005, SOAA-010–013; INV-038–067 | The other records belong to higher-rung roles. |
| 13 | Thirteen activation states | R1: 6 states; `SELECTED`, `APPROVAL_PENDING`, `ACTIVATING`, `SUSPENDED`, `TERMINATING`, `DENIED`, `STALE`: R2 | T | SOAA-006, SOAA-009; INV-030–037 | The removed states belong to selection and revalidation. |
| 14 | Eight-item decision-cycle record | R1: observation, proposal, trusted decision, outcome, budget update; context-snapshot ID and event offset: R2 | X | SOAA-005; INV-038–067 | Snapshots are Rung 2 (#18). |
| 15 | Multi-skill composition plan; leases and merge rules | R3 for concurrent, joined or model-amended plans; R1 for sequential workflow binding (D1b), where the versioned state machine stands in for the plan | T for R3; X for D1b | SOAA-010–013; INV-038–067 | Concurrency, joins and amendment are the Rung 3 trigger. Under D1b's five conditions those plan elements have nothing to govern; Q17 asks SOAA to accept the state machine as the plan. |
| 16 | Subtask delegation and two-phase handoff | R3 | T | SOAA-010–013; INV-038–067 | Delegation is the Rung 3 trigger. |
| 17 | Four-stage selection pipeline; admission outcomes; fallback rules | R2; R1 keeps fixed binding and the D1a menu | T | SOAA-006, SOAA-008, SOAA-009; INV-021–024, INV-030–037 | Catalog selection is the Rung 2 trigger. |
| 18 | Ten-field scoped permission; full intersection formula | R2; R1: action, target, expiry, deny-overrides, intersection with task permissions | X | SOAA-007, SOAA-008; INV-025–031 | Tenant, purpose and data-class attributes matter where catalogs and memory cross boundaries. |
| 19 | Seven-layer instruction precedence | R1: 3 tiers; R2: 7 layers | X | SOAA-007; INV-025–031 | The three tiers keep the injection rule (data never becomes instruction). |
| 20 | Full approval record fields | R1: scope, task, approver identity and role, decision, expiry, revocation, evidence link; R2: the rest | X | SOAA-007, SOAA-008; INV-025–031 | Rung 1 keeps every field that R-4 and the four roles depend on. |
| 21 | Context snapshots, assembly pipeline, compaction, resources, memory | R2; R1 keeps "no authoritative state only in context" and "retrieved content is data" | T | SOAA-014; INV-068–088 | Memory and retrieved resources are Rung 2 triggers. |
| 22 | Six-class failure taxonomy; cancellation propagation; compensation; resume revalidation list; telemetry metrics | R2; R1 keeps unknown outcome, reconcile before retry, bounded retry, timeout ≠ failure, finite budget, restart | X | SOAA-015; INV-089–102 | Rung 1 keeps the rules that prevent duplicate or phantom side effects. |
| 23 | Child budget reservations; delegation timeouts | R3 | T | SOAA-015; INV-089–102 | These only exist with delegation. |
| 24 | Evaluation spec structure, dataset partitions, oracle ladder, eight independence dimensions, stochastic reliability, review records | R2 | X | SOAA-016, SOAA-017; INV-103–146 | Rung 1 keeps the gate semantics, the self-check rule and the LLM-as-judge limit. |
| 25 | Release lifecycle states; revocation; compatibility lock; change impact; supply-chain review; drift revalidation; MCP mapping | R2; R1 keeps immutable pinned digests and regression evals on re-pin | T | SOAA-018, SOAA-020; INV-147–206 | A changing catalog is the Rung 2 trigger. |
| 26 | Live migration at safe points; A2A mapping; protocol version policy; portability claims | R3 | T | SOAA-018–020; INV-147–206 | These concern remote agents or multiple runtimes. |
| 27 | Six-level precedence stack; unresolved conflict blocks implementation | D5 | — (governance, not an invariant) | README only | Consumers cannot read levels 1–5. Q11 confirms SOAA does not make the order normative. |

## Vocabulary pass

**Rule:** prose uses the plain term. Each contract's Source alignment table gains
a "SOAA term" column so traceability survives. Enum values that teams put in code
(state names, `SUBTASK`/`HANDOFF`, `PASS`/`FAIL`/`INCONCLUSIVE`/`ERROR`,
`EP0`–`EP3`) are kept as identifiers next to their plain names.

### Roles (all contracts and the runtime profile)

| SOAA role | Plain name | Rung | Note |
|---|---|---|---|
| Task Controller | task controller | 1 | Kept: plain already, and pinned by tests |
| Agent Decision Runtime | agent loop | 1 | |
| Policy and Authority Controller | authorization service | 1 | Standard policy-decision-point role |
| Tool Gateway | tool gateway | 1 | Kept: the standard policy-enforcement point |
| Evaluation Controller | completion gate | 1 | Distinct from the *evaluator* component type, which measures but never decides |
| State Repository | state store | 1 | |
| Evidence Recorder | evidence log | 1 | Append-only |
| Skill Registry | skill registry | 1 (pinned list) / 2 | Kept |
| Model Gateway | model gateway | 1 if LLM | Kept: shared with `llm-application`'s `ModelGatewayPort` |
| Skill Asset Runner | script runner | 1 if scripts | Runs package scripts in isolation |
| Capability Controller | skill binder | 2 | Selection and binding |
| Context Controller | context builder | 2 | |
| Resource Gateway | resource gateway | 2 | Kept: matches MCP "resources" |
| Memory Gateway | memory store | 2 | |
| Interaction Adapter | request adapter | 2 | API, chat or UI entry point |
| Workflow and Composition Controller | workflow engine | 3 | |
| Delegation and Handoff Controller | delegation service | 3 | |
| Agent Directory | agent directory | 3 | Kept |

### `SKILL_ORIENTED_AGENT_ARCHITECTURE.md`

| SOAA term | Use | Reason |
|---|---|---|
| trusted controller / trusted deterministic component | trusted component | Shorter; same meaning |
| primitive | component type | |
| logical role / plane | role (planes dropped) | Planes are grouping only |
| runtime owner | task owner | |
| agent run | **keep** | Common in agent SDKs; precise (one bounded loop) |
| accountable principal | **keep** | Standard IAM term; reused verbatim by AIPOS |
| proposal / commit | **keep** | Plain; "Model output is a proposal" is R-1 |
| authoritative state | authoritative record (system of record) | |

### `SKILL_CONTRACT.md`

| SOAA term | Use | Reason |
|---|---|---|
| `Skill = (I, C, P, T, R, D, G, E)` | "a skill declares:" followed by a named list | The tuple notation adds nothing for readers |
| executable assets | scripts | Agent Skills spec folder name |
| authority needs / ceilings | permission ceiling | |
| skill lineage ID | skill name (stable ID) | |
| release identity | release: name, version, digest | |
| SOAA package profile, `soaa/`, `soaa-*` keys | **keep** | External format identifiers; renaming would break packages |
| Agent Skills-format conformance | **keep** | The spec's own term |
| two-stage validation | **keep** | Plain |

### `RUNTIME_STATE_AND_EXECUTION_CONTRACT.md`

| SOAA term | Use | Reason |
|---|---|---|
| TaskOfferRecord | task request | |
| TaskRecord, AgentRunRecord | task record, agent run record | Lower-case prose |
| `owner_epoch` | fencing token | Widely used name for the same mechanism |
| aggregate / aggregate version | record / record version (optimistic concurrency) | |
| authoritative writer | single writer | Single-writer principle |
| quiescence | drained (no in-flight operations) | |
| SkillActivation | skill activation | **Keep "activation"**: it is the Agent Skills spec term for loading a skill |
| adaptive decision loop | agent loop | |
| observation cursor | event offset | |
| CompositionPlan | multi-skill plan | |
| safe amendment point / safe-point migration | plan checkpoint | |
| OperationRecord (+ "operation ledger" in Resilience) | operation record | One name for one concept |
| side-effect class | effect type (read-only, idempotent, non-idempotent, irreversible) | |
| result certainty / unknown effect | outcome certainty / unknown outcome | Standard distributed-systems term |
| prepare / commit handoff | two-phase handoff | |
| state and evidence commit / authoritative durable envelope | transactional outbox | |
| restart rule | recovery from durable records | |
| task revision, reconciliation, lease, fencing, idempotent consumer | **keep** | Already the standard names |
| `SUBTASK` / `HANDOFF`, state names | **keep as identifiers** | Code-level enum values |

### `SKILL_SELECTION_AND_ACTIVATION_CONTRACT.md`

| SOAA term | Use | Reason |
|---|---|---|
| four-stage pipeline | search → filter → rank → bind | |
| candidate retrieval | search | |
| deterministic admission | eligibility filter (hard rules only) | |
| agent ranking | model ranking | |
| atomic activation | transactional binding | |
| `INELIGIBLE` / `ELIGIBLE` / `APPROVAL_ROUTABLE` | ineligible / eligible / eligible with approval (identifiers kept) | |
| null selection | no-skill option | |
| fixed workflow binding | fixed binding | |
| catalog snapshot | catalog version | |
| dependency lock | lockfile | |
| instruction binding / exposure point | instructions loaded | |

### `AUTHORITY_AND_APPROVAL_CONTRACT.md`

| SOAA term | Use | Reason |
|---|---|---|
| `BaseAuthority` / `EffectiveAuthority` formula | effective permissions = grants ∩ boundaries − explicit denies | Least privilege with deny-overrides; the formula stays as a block |
| capability tuple | scoped permission | |
| RequiredAccess | required permissions | |
| authority envelope | the binding's permission set | |
| fresh operation authorization | time-of-use authorization | |
| decision authority | approver role | |
| data-to-instruction promotion | treating data as instructions (prompt injection) | |
| reviewer / approver / human execution owner / accountable principal | **keep** | Required by the brief; reused verbatim elsewhere |
| ApprovalRecord, instruction precedence, scoped approval, expiry, revocation | **keep** | Plain |

### `CONTEXT_MEMORY_AND_RESOURCE_CONTRACT.md`

| SOAA term | Use | Reason |
|---|---|---|
| ContextSnapshot | context snapshot: "the recorded inputs of one model call" | Kept as a name, now defined |
| source class | source label | |
| protected budget allocation | reserved context | |
| rehydration | reload from records | |
| ResourceDescriptor | resource metadata | |
| promotion state | review state | |
| Memory Gateway | memory store | |
| progressive disclosure, compaction, poisoning, working/episodic/semantic memory | **keep** | Agent Skills, Claude Code and OWASP terms |

### `RESILIENCE_AND_RECOVERY_CONTRACT.md`

| SOAA term | Use | Reason |
|---|---|---|
| operation ledger | operation record | Merged with Runtime |
| unknown-effect failure | unknown outcome | |
| BudgetEnvelope | budget | |
| child reservations | child budgets | |
| one execution chain | distributed trace (one correlation ID) | |
| retry owner, backoff, jitter, reconciliation, compensation, checkpoint | **keep** | Standard; note "saga compensation" at first use |

### `EVALUATION_EVIDENCE_AND_COMPLETION_CONTRACT.md`

| SOAA term | Use | Reason |
|---|---|---|
| EvaluationDefinition | evaluation spec | |
| model judge | LLM-as-judge | |
| HumanReviewRecord | review record | |
| Evaluation Controller | completion gate | |
| conformance assessor and report authority | assessor | |
| `EP0_OBSERVED` … `EP3_HUMAN_GATED` | evidence levels 0–3: observed, verified, independent, human-gated (codes kept) | |
| EvidenceRecord → EvidenceClaim → GateDecision | evidence → claim → gate decision | |
| oracle | **keep** | Standard testing term ("test oracle") |
| "A producer self-check is advisory", "never commits its own final gate", gate outcomes | **keep verbatim** | Pinned by `tests/test_evidence_contract.py` and already plain |
| evaluator independence | **keep**, glossed as separation of duties | |

### `SKILL_LIFECYCLE_AND_INTEROPERABILITY_CONTRACT.md`

| SOAA term | Use | Reason |
|---|---|---|
| skill definition or lineage | skill name | |
| version class | semver change type | |
| safe degraded mode | declared fallback mode | |
| revocation-staleness limit | revocation cache TTL | |
| `CANDIDATE` … `REVOKED`, drift, provenance, supply chain | **keep** | Standard release terms |
| MCP and A2A primitive names | **keep** | Protocol vocabulary |
| SOAA package profile text | moves to `SKILL_CONTRACT.md`; one pointer remains | Removes the duplication |

### `AGENT_RUNTIME_STACK.md`

| SOAA term | Use | Reason |
|---|---|---|
| "SOAA responsibility" column | plain role names from the table above | |
| `owner_epoch` fencing | fencing token | |
| `OperationRecord` | operation record | |
| Evaluation Controller | completion gate | |
| §1 "The runtime is more than a graph library" | **keep verbatim** | Required by the brief |
| implementation profile, checkpointer | **keep** | Manifest key; the profile may use product terms |

The profile gains one column, "Rung", so a Rung 1 team sees that only the agent
loop, durable state, task controller, authorization, operation and evidence rows
apply.

## Reference implementation: what proves Rung 1

The first consumer is the backend of a product UI that runs the `aipos` pack
inside its own runtime. Its repository is not named in this repo (Q1). Rung 1 is
**demonstrated** only when all of the following hold:

1. **Every applicable assertion R1-01 … R1-22 passes in CI** (R1-22 when the backend uses sequential workflow binding) against the real runtime with durable storage (PostgreSQL or equivalent). Fakes may support unit tests but never count as evidence for an assertion. The restart, fencing and unknown-outcome assertions each include a fault-injection test.
2. **The `aipos` scenarios below are covered.** These are the places where the pack meets the five rules.

| Rule | Scenario the consumer must show |
|---|---|
| Passive package | Installing all 14 `aipos` skills executes nothing and makes no network call. The 8 skills with `scripts/` (for example `aipos-map-render`, `aipos-metrics-emit`) run scripts only through the script runner, after a recorded and authorized call. A modified `SKILL.md` byte fails binding. |
| R-1 | Model output that claims a feature package is ready, or writes a Development Token record directly, changes no authoritative record. Only the task controller commits. |
| R-2 | Skill text or `allowed-tools` that "permits" a tracker write does not authorize it (injection test). The skill never owns the task. |
| R-3 | A PM takes over a running `aipos-feature-refine` task from the UI. A late agent command carrying the old fencing token is rejected. |
| R-4 | An `aipos-feature-readiness` token request or an explicitly requested tracker write requires a durable, scoped, expiring approval. The approval survives a backend restart; an expired one blocks; a chat "yes" does not count; a reviewer cannot approve. The tracker write has an operation record with an idempotency key before the call. A simulated timeout produces an unknown outcome, then reconciliation, and no duplicate write. |
| R-5 | `aipos-feature-readiness` reporting success does not complete the task. A deterministic verifier (for example the pack's `verify_vision.py` or `verify_scores.py`) yields `PASS` before `COMPLETED`. `INCONCLUSIVE` does not complete. |
| Recovery | The backend is killed mid-task and restarted; active tasks reconstruct from records without the provider transcript. |

3. **The results pass the GovKit Rung 1 check** (increment 4): every assertion executed and `PASS`, and none skipped, unknown or inconclusive.
4. **The runtime choice is recorded.** It is LangGraph per `AGENT_RUNTIME_STACK.md`, or an ADR records the alternative.
5. **Someone outside the implementing team reviews** the evidence package and the mapping of tests to assertions.
6. **GovKit records the result honestly.** The README records "Rung 1 demonstrated by one implementation" with the evidence reference and date. It never says "certified". Portability still needs two independent runtimes, as the lifecycle contract already requires.

**Rung 1 assertions** (normative text lands in increment 2; R-numbers refer to
the five rules):

| ID | Assertion | Rule |
|---|---|---|
| R1-01 | Loading or installing a skill executes nothing and makes no external call | Passive |
| R1-02 | Package scripts run only through the script runner, after an authorized proposal and an operation record | Passive, R-4 |
| R1-03 | Binding uses the exact pinned digest; any changed byte fails binding | R-2 |
| R1-04 | Skill text, `allowed-tools`, tool descriptions and retrieved content cannot grant a permission | R-2 |
| R1-05 | Model output cannot write task, binding, approval, operation, gate or evidence records | R-1 |
| R1-06 | Zero-owner and two-owner task states are rejected | R-3 |
| R1-07 | After ownership transfer, commands with the old fencing token are rejected | R-3 |
| R1-08 | Writes against a stale record version are rejected | R-1 |
| R1-09 | Every mutating external call has a durable operation record with an idempotency key before invocation | R-4 |
| R1-10 | Replaying a mutating command causes no duplicate side effect | R-4 |
| R1-11 | A timeout on a mutating call yields unknown outcome; no retry before reconciliation | R-4 |
| R1-12 | Retries are bounded with one retry owner; budget exhaustion stops work visibly | R-1 |
| R1-13 | Each external call is authorized at time of use; revoked or expired approval blocks the next call | R-4 |
| R1-14 | Approvals are durable, scoped, expiring records that survive restart; chat acknowledgment and authentication are not approval | R-4 |
| R1-15 | A reviewer cannot approve; approval does not transfer ownership | R-4, R-3 |
| R1-16 | Skill success or model confidence never completes a task; completion passes `VERIFYING` and a completion-gate `PASS` | R-5 |
| R1-17 | `INCONCLUSIVE`, `ERROR`, missing or stale evidence never yields `COMPLETED` | R-5 |
| R1-18 | The task owner never commits its own final gate; an LLM-as-judge is never the sole blocking check for authority, side effects or evidence integrity | R-5 |
| R1-19 | State change and its evidence commit together, or recover together; evidence is append-only | R-4, R-5 |
| R1-20 | Restart reconstructs active tasks from durable records without a provider transcript | R-1, R-4 |
| R1-21 | Terminal tasks reject mutation | R-1 |
| R1-22 | Under sequential workflow binding (D1b): a skill switch happens only on a transition the task controller commits; the previous binding ends before the next starts; the incoming skill cannot use tools allowed only to the previous one | R-1, R-2 |

## Increments

Each increment must leave the extension installable and `./run_tests` green. Each
adds a `## [Unreleased]` CHANGELOG entry that names the extension. Each runs Qodo
local review before its PR, per `CLAUDE.md`.

**Sizes:**

- **S:** under ~200 changed lines, one reviewer sitting.
- **M:** one contract or template family.
- **L:** cross-payload, or multiple files that must stay in lockstep.

### 0. Trace baseline and ladder ADR (S, plans only)

- **ADR `plans/decisions/0020-soaa-conformance-ladder.md`:** records D1, D1a, D1b, D5, D7, D9, the claim wording, and the rule that a rung is set by triggers, not chosen.
- **Trace:** obtain from the SOAA source set:
  - the 206 invariant IDs, with one-line titles
  - the subject of `SOAA-003` (cited nowhere)
  - where `SOAA-MID-001`–`006` and the root cross-module rule land

  Fill the demotion register's exact IDs and add a "Deviations from SOAA v0.2" draft. Whether the IDs and titles may be vendored into the payload is Q3.
- **Upstream:** propose the three rungs as SOAA named profiles, with the X rows attached.
- **Needs:** ADR (yes). Upstream spec change (proposal sent; not blocking increments 1–3, but blocking any claim wording beyond D7).

### 1. Guard what must survive (S, tests first)

- **New tests in `tests/test_skill_oriented_agent_architecture.py`:**
  - R-1 to R-5, the passive package rule, the proposal-to-commit table, the four human roles, and "more than a graph library" are each present somewhere in the extension. Match normalized plain phrases, not today's wording.
  - The pack's `provides` set is a superset of the 0.1.0 snapshot (33 entries, including the pack ID).
  - Every contract path is ≤ 48 characters after `docs/backend/architecture/`.
- **Expected state:** passes on `main` today, apart from the phrase forms that increment 2 introduces. Write those as the target phrases and mark them `xfail(strict=True)` until increment 2.
- **Needs:** no ADR.

### 2. Rung 1 contract and README (L)

- **Rung 1 contract:** rewrite `SKILL_ORIENTED_AGENT_ARCHITECTURE.md` as the self-contained Rung 1 contract (D3, D4, D6 summary, R1-01 … R1-22). It opens with "Which rung are you on?": the trigger table T1–T6 and the D9 procedure, steps 1–4.
- **README:**
  - add the ladder, the two-skill-meanings table, the D5 precedence and the demotion register
  - add "Deviations from SOAA v0.2"
  - note that the declarative `govkit pack` route installs this extension without L5 (Q14)
- **Manifest:**
  - rewrite `agent_guidance` by rung, starting with the D9 determination
  - add `agent_guidance.rung_2_trigger_paths` and `rung_3_trigger_paths` (D9 step 5)
  - remove `SKILL_CONTRACT.md` and `RUNTIME_STATE_AND_EXECUTION_CONTRACT.md` from `soaa_core`
  - add `soaa_orchestration` and put `SKILL_CONTRACT.md` in `soaa_ecosystem` (D2)
  - bump `version` to 0.2.0
- **Topic contracts:** each gets a one-line header, "Rung 1 requirements for this topic are in `SKILL_ORIENTED_AGENT_ARCHITECTURE.md`; this document applies at Rung 2 and above unless a section says otherwise". Until increments 5–9, some Rung 1 text is duplicated there; that is acceptable for the interim and is tracked.
- **Tests first:**
  - `REQUIRED_CONTRACT_SETS` gains `soaa_orchestration`
  - the "Eighteen" pin becomes the rung role counts
  - the selection pins move to increment 6
  - increment 1's `xfail`s flip
  - the core document contains T1–T6 and the never-lower rule
  - both trigger-path lists exist, are non-empty and valid globs, and share no pattern with each other
  - neither list contains a pattern from a deny list of Rung 1 concerns (`*registry*`, `*approval*`, `*permission*`, `*retry*`, `*task*`)
- **Needs:** ADR 0020 accepted. No installer change. Unblocks the consumer.

### 3. Point the L5 payload at the right audience (L, three agents in lockstep)

- **Trigger (D8):** add `agent_skills_rung` (commented) to `features/starter_backend_l5/eval_criteria.yaml`. Update its schema and examples if one validates the file.
- **Agent instructions:** update in all three agents:
  - `agents/*/claude-md|agents-md|copilot-instructions/l5-backend-*.md:28`: load on `agent_skills_rung` or `multi_agent`, or ask when D9 step 4 applies; read the rung's documents only
  - every entry point follows D9: answer T1–T6 with evidence, block when the computed rung exceeds the declared feature rung or the system rung, and never lower a declared rung
  - `agents/*/rules/backend/multi-agent.md`: the contract list leads with the Rung 1 document
  - `agents/*/skills/backend/govkit-multi-agent-design/SKILL.md`: Rung 3 only; frontmatter unchanged and byte-identical
  - `govkit-genai-preflight` §6 and `govkit-architecture-preflight` §15: branch by rung
- **Templates:**
  - `governance/backend/templates/l5-architecture-preflight.md` §15 becomes "Agent Skills (when `agent_skills_rung` or `multi_agent` is declared)". It starts with the T1–T6 table (answer and evidence columns) and the computed, declared and system rungs, followed by a Rung 1 checklist and Rung 2/3 additions
  - `l5-plan.md` "Multi-Agent Configuration" gains a rung line
- **System rung (D9 step 3):** replace the agent-runtime comment in `docs/backend/architecture/TECH_STACK.md` and the five backend overlays (`cli/stacks/{python-fastapi,java-spring-boot,nodejs-fastify,dotnet-aspnet,go-gin}/TECH_STACK.md`) with an "Agent skills rung" line (`undeclared` by default). The data stacks carry no such comment and are unchanged. Edit protection keeps existing projects' copies, and the agent treats a missing line as undeclared.
- **Topology starter:** `features/starter_backend_l5/agent_topology.md` keeps its four gated headings and adds a "Conformance rung" field. The CI gates are unchanged.
- **Tests:**
  - `pytest -k parity`, `tests/test_agent_skills.py`, `tests/test_govkit.py`, `tests/test_instruction_surface.py`, `tests/test_validate.py`
  - `tests/test_overlay.py` for the six `TECH_STACK.md` files
  - a new test that the baseline and all five backend overlays carry the identical "Agent skills rung" line
  - a new test that all three agents' entry points contain the D9 never-lower and block-on-mismatch instructions
- **Needs:** no ADR. This is a payload contract change, so the CHANGELOG entry goes under "Changed". The entry must note that existing projects keep their `TECH_STACK.md`, and that agents will ask for the system rung once.

### 4. Rung 1 assertion suite and results check (L)

- **New `conformance/` folder** in the extension (path budget is ample at that depth):
  - `rung-1.feature`: one Gherkin scenario per R1 assertion, written against the role names, for teams to bind to their runtime
  - `rung-1-results.schema.json`
  - one passing and one failing example results file
- **New check `checks/rung_1_results.py`:** validates a team's results file. Every R1 assertion must be present, executed and `PASS`; skipped, unknown, `INCONCLUSIVE` and `ERROR` fail; a valid file does not authenticate its origin (ADR 0004 semantics). It **runs nothing** from the team's repo.
- **Manifest:** convert to an explicit `capability_pack` block declaring:
  - every `provides` entry the legacy derivation (`cli/pack_loading.py:55-80`) produced
  - the nine contracts as `contract` and `AGENT_RUNTIME_STACK.md` as `defaults`, as today
  - additions only: the README as `advisory` (the legacy derivation omits it) and the new `conformance/` files as `example`/`contract`
  - the check as `required: false` (Q12)
- **Tests:**
  - the explicit block's `provides` equals the legacy set, and its resources equal the legacy set plus exactly the listed additions
  - the check accepts the pass example and rejects every failure class
  - `tests/wheel_pack_smoke.py` catalog and install
  - `tests/wheel_windows_smoke.py` byte-identical install
  - a real wheel in a clean venv (`wheel-smoke` mirror)
  - scoped `ruff` on the new check file only
- **Needs:** an ADR 0020 amendment, or a short ADR, for shipping a pack check that defines a claim. Pack execution stays opt-in.

### 5. Runtime state contract (M)

- Label each section of `RUNTIME_STATE_AND_EXECUTION_CONTRACT.md` with its rung (Rung 2 for the full lifecycles, record table and task revision; Rung 3 for multi-skill plans, delegation and handoff).
- Apply its vocabulary rows.
- Delete the Rung 1 text that duplicates the core document and replace it with pointers.
- Remove the duplicate activation lifecycle, keeping it in the selection contract.
- Extend the Source alignment table with Rung and SOAA-term columns.
- **Needs:** no ADR.

### 6. Selection and authority contracts (M)

- Same treatment for `SKILL_SELECTION_AND_ACTIVATION_CONTRACT.md` and `AUTHORITY_AND_APPROVAL_CONTRACT.md`.
- **Tests first:** the four stage-name pins in `test_selection_contract_preserves_four_stage_pipeline_and_null_option` become the plain names. The SOAA names stay asserted in the Source alignment table.
- **Needs:** no ADR.

### 7. Context and resilience contracts (M)

- Same treatment for both contracts. Merge "Operation ledger" into "operation record" with one definition (in the core document) and one pointer.
- **Needs:** no ADR.

### 8. Evaluation contract (M)

- Same treatment. Keep the two pinned sentences and the four backticked outcomes verbatim.
- Run `tests/test_evidence_contract.py`. Re-read `docs/{backend,ui}/evaluation/EVIDENCE_CONTRACT.md` for any vocabulary they lifted; they import the gate outcomes and the self-check rule only.
- **Needs:** no ADR.

### 9. Skill, lifecycle and runtime-profile documents (M)

- **`SKILL_CONTRACT.md`:** opens with the D6 table and becomes the single home of the SOAA package format.
- **`SKILL_LIFECYCLE_AND_INTEROPERABILITY_CONTRACT.md`:** keeps lifecycle, MCP and A2A, with a pointer for the package format.
- **`AGENT_RUNTIME_STACK.md`:** gains a Rung column and plain role names. §1 is kept verbatim.
- **Tests first:** `test_agent_skills_profile_defines_standard_compatibility_boundary` asserts the lifecycle phrases against the pointer section. Keep "Flat string metadata keys", "may ignore `soaa/`" and "must not claim SOAA conformance" there, or move those assertions to `SKILL_CONTRACT.md`.
- **Cross-reference check** (`llm-application`):
  - `extensions/llm-application/README.md` §"Relationship to Skill-Oriented Agent Architecture" and `GATEWAY_STACK.md:58` reference the extension and `AGENT_RUNTIME_STACK.md` by name, and both names are unchanged
  - update their wording only if they use a renamed role ("Evaluation Controller" and similar). Grep before and after; expect no change.
- **Needs:** no ADR.

### 10. Record the reference-implementation result (S here; L in the consumer)

- **In the consumer repo (outside GovKit's control):** bind `rung-1.feature`, run it in CI, and produce the results file and evidence package.
- **In GovKit:**
  - add the "Rung 1 demonstrated" line in the README (date and evidence reference)
  - bump to 1.0.0 only if Q8's answer says so
  - add a CHANGELOG entry
- **Needs:** no ADR. The independent review comes from someone outside the implementing team.

**Later, not planned here:** Rung 2 and Rung 3 assertion catalogs and checks. These
wait for a consumer at those rungs, so GovKit does not ship assertions it has never
seen run.

**Ordering rationale:** increments 2–4 give the Rung 1 audience the contract, the
entry points and a check. Increments 5–9 are clean-up that no Rung 1 team reads.
They can run in parallel after increment 2, but they must merge one at a time
because they share the manifest and the extension test module.

## Verification

Every increment runs:

```sh
pip install -e ".[test]"
pytest tests/test_skill_oriented_agent_architecture.py tests/test_evidence_contract.py \
       tests/test_cmd_extension.py tests/test_schemas.py
./run_tests                                   # fast tier
```

Then, by increment:

| Check | What it proves | Increments |
|---|---|---|
| `test_manifest_matches_extension_schema`, `test_extension_validates_cleanly_against_repo` | Manifest validity against `governance/schemas/extension-manifest.schema.json` and `validate_extension` | all |
| `test_every_required_contract_is_declared_once_and_exists` plus the new rung-mapping test | Contract-set coverage: each of the nine contracts is in exactly one set, and each set declares its rung in the README table | 2, 5–9 |
| `provides` superset test | No capability token lost, so profiles and locks keep resolving | 1, 2, 4 |
| Survivor-phrase tests (increment 1) | The five rules and the other kept items are still present | all |
| `test_contracts_are_provider_and_framework_neutral` | No product names in the neutral contracts after the vocabulary pass | 2, 5–9 |
| `tests/test_evidence_contract.py` | The two lifted sentences and four outcomes remain | 8 (and every run) |
| `pytest -k parity`, `tests/test_agent_skills.py`, `tests/test_govkit.py`, `tests/test_instruction_surface.py` | Three-agent lockstep, byte-identical skill frontmatter | 3 |
| `tests/test_validate.py` and the multi-agent gate headings | The topology starter still satisfies both CI gates | 3 |
| Trigger-path list tests (D9 step 5) | The backstop lists exist, are valid, and exclude Rung 1 concerns | 2 |
| D9 instruction and `TECH_STACK.md` rung-line tests | All three agents determine the rung the same way, and every backend stack records the system rung in the same place | 3 |
| Check unit tests (pass and failure classes) | The Rung 1 results check cannot pass skipped, unknown or inconclusive evidence | 4 |
| `tests/wheel_pack_smoke.py`, `tests/wheel_windows_smoke.py`, clean-venv wheel install | New files ship in the wheel under `cli/ext/` and install byte-identical within the Windows budget | 4 (and any increment adding files) |
| `./full_test` | Same coverage as CI's plain `pytest` | before each PR |
| Qodo local review | Delivery review per `CLAUDE.md`; record the actual result | before each PR |

**Before any rung can be claimed:**

- **Rung 1:** increments 2 and 4 merged, plus the six conditions under
  "Reference implementation". A results file that only passes increment 4's check
  is necessary but not sufficient: the check proves the file is complete, not that
  the tests behind it ran against a real runtime.
- **Rung 2 or 3:** a published assertion catalog for that rung, a check for it,
  and one demonstrating implementation. None of these exist, and this plan does
  not create them.

A blocked or skipped check is reported as such and is never counted as passed.

## Out of scope

- The `llm-application` extension, except the increment 9 cross-reference check.
- A CI check comparing the declared rung against changed paths (D9 step 6). Increment 4's check is consumable through `govkit conform` with explicit pack-check opt-in. A provider gate template is a follow-on that needs both `ci/github/` and `ci/azure/`.
- Renaming the extension or its pack ID (Q7).
- Rung 2 and Rung 3 assertion suites.
- The SOAA source set itself; increment 0 only reads from it and proposes to it.

## Open questions

| # | Question | Recommended answer |
|---|---|---|
| Q1 | Which repository is the first consumer backend, and is it a separate `api` service? | Name it in this plan before increment 10 starts. Prefer a separate `api` backend; the extension supports `api`/`cli` only, and a `ui-nextjs` server would need `supported_project_types` widened (a separate decision). |
| Q2 | Will SOAA adopt the three rungs as named profiles? | Propose it in increment 0. Until accepted, use D7's wording and list the X rows as deviations. Do not wait on it for increments 1–9. |
| Q3 | May GovKit vendor the 206 invariant IDs and titles into the payload? | Vendor IDs and one-line titles only, with the SOAA owner's approval, as a reference resource inside the extension (not a contract). Without approval, keep ranges in the payload and the exact trace in `plans/`. |
| Q4 | Is pinned-menu choice (D1a) truly Rung 1? | Yes, with the four conditions. It covers how `aipos` will be used. A catalog, per-task filtering or approval-routed eligibility stays Rung 2. |
| Q5 | Field name and home for the rung declaration, and who sets it? | The feature author sets `agent_skills_rung` in `eval_criteria.yaml`; `multi_agent: true` implies 3, so existing features need no edit. The system rung lives once in `TECH_STACK.md`. The declaration is an input the agent checks (D9), never the control itself. |
| Q15 | Should "unsure" on a trigger question block, or default to the higher rung? | Block and ask (D9 step 1). A silent default upward hides the question from the person who can answer it, and a default downward is the failure D9 exists to prevent. |
| Q16 | Should the D9 step 5 path backstop warn or block? | Warn. It must make the agent re-answer the matching trigger question, but it may not block on its own, because its false-positive rate is unknown until a real project uses it. Revisit once a reference implementation has run against it. |
| Q17 | Will SOAA accept a state machine versioned with the release as the composition plan for sequential workflow binding (D1b)? | Propose it in increment 0, alongside the rungs. SOAA's own "Fixed workflow" binding mode is the precedent. Until SOAA accepts it, list D1b as a deviation (register row 15, kind X). If SOAA rejects it, D1b systems need a minimal versioned plan record (skill per state, data passed, permissions per step), still on Rung 1, not Rung 3. |
| Q6 | Rename roles in prose, or keep SOAA role names? | Plain names in prose, SOAA name at first use and in Source alignment. Keep "task controller", "tool gateway", "model gateway" and the four human roles unchanged. |
| Q7 | Rename the extension (for example `governed-agent-skills`)? | No. The pack ID is public in profiles and locks, and the vocabulary pass already removes the jargon readers meet. |
| Q8 | Version after this series: 0.2.0 or 1.0.0? | 0.2.0 through increment 9. 1.0.0 only after increment 10 records a demonstrated Rung 1. |
| Q9 | What is `SOAA-003`, and where do `SOAA-MID-001`–`006` land? | Resolve in increment 0 from the source set. If `SOAA-003` covers content moved off Rung 1, add it to the register before increment 2 merges. |
| Q10 | Can the implementing team's own CI evidence prove Rung 1? | The suite may run in their CI from the protected branch, but someone outside the implementing team reviews the evidence and the test-to-assertion mapping before GovKit records "demonstrated". This mirrors "the task owner never commits its own final gate". |
| Q11 | Is the six-level precedence order normative in SOAA (the root cross-module rule)? | Treat it as guidance-level and adopt D5. If increment 0 finds it normative, keep D5 for consumers and keep the six levels only in the maintainer section. |
| Q12 | Should the Rung 1 check be `required: true` in the pack? | No. Use `required: false` so installing the pack never fails a project that has not yet claimed a rung. A team that claims Rung 1 makes it required through its accepted policy. |
| Q13 | Should the duplicate Rung 1 text in the topic contracts be removed in increment 2 rather than 5–9? | No. Keeping increment 2 reviewable matters more than a short window of duplication; each later increment removes its own duplicates. |
| Q14 | Should `supported_levels: [5]` widen so L3/L4 teams can install the extension the legacy way? | Not in this series. The declarative `govkit pack` route already installs it without levels. Say so in the README in increment 2 and revisit if a Rung 1 team needs the legacy route. |
