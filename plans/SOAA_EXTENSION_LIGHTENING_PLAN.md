# SOAA Extension Lightening and Validation Plan

**Status:** Revised proposal, 2026-10-19. The experiments and payload changes
below are not implemented. The manifest-validation defect identified during
review is fixed separately; it does not establish SOAA conformance.

**Intent:** First enhance GovKit's development workflow to use experiments when
needed and refine the SOAA extension. After those changes are implemented,
tested and packaged, the user will install GovKit in the Value Builder project
and validate the approach by developing the application. SOAA v0.2 remains an
unproven architecture; project evidence will inform subsequent refinements.

**Delivery order:** Phase A delivers installable GovKit changes and refined
guidance. Phase B is the user's consuming-project pilot. Value Builder informs
Phase A's examples and acceptance cases, but building its runtime or completing
its experiments is not a prerequisite for finishing Phase A. The runtime
experiments below describe how the installed workflow will be used in Phase B.

This revision replaces the proposed three-rung ladder. The
[original draft](archive/SOAA_EXTENSION_LIGHTENING_PLAN_2026-10-17.md) is preserved
unchanged. The [critical review](SOAA_ARCHITECTURE_AND_GOVKIT_REVIEW.md) records
evidence, defects, source differences and disposition of the original decisions.
The existing extension remains unchanged pending implementation increments.

## 1. Source baseline and claim boundary

The supplied SOAA v0.2 Architecture Guide is derived from a separate normative
corpus. Chapters 35–39 recommend a small control skeleton, fault tests and
bounded claims. Appendix E defines composable conformance profiles, not
maturity rungs. Appendix G does not reproduce the 206 assertion definitions.

Use guide chapter and decision references for experiments, and local
`GK-SOAA-*` test identities until the corresponding normative assertions are
available and verified. Never manufacture a mapping from ID ranges or present
local tests as coverage of all 206 assertions.

Allowed result: “Experiment E1 passed these cases for this exact target,
configuration and environment.” Installation, document validation and imported
results do not demonstrate runtime behavior. First-party experiments are useful
evidence; independent assessment and certification are separate claims.

An unresolved source conflict blocks the affected conformance claim. It need
not block a contained, labeled experiment. Weakening accepted project controls
still follows that project's change policy.

## 2. Design decisions

### D1. Scale by capabilities and consequences

Do not adopt `agent_skills_rung` or the maximum feature rung as system policy.
Agent count, binding mode, memory, data sensitivity and effects are independent
dimensions. One fixed skill can be more consequential than a large read-only
catalog. Select controls by actual behavior and enforce their applicability.

The initial applicability record can be an ordinary reviewed document. Reuse
GovKit's accepted profiles and check engine; do not create a second policy
engine. If machine-readable applicability is later useful, version its schema
and update every consumer together.

| Behavior or boundary | Required control focus | Safe omission condition |
|---|---|---|
| Every adaptive AgentRun | Accepted task/principal, one current owner, trusted writers, bounds and completion gate | No adaptive loop: describe a workflow instead |
| Every activation, including fixed binding | Exact release, admission, compatibility, atomic activation, current authority, context and revocation behavior | No skill activation |
| Any untrusted input or model context | Source labels, controlled assembly, authorization and data/instruction separation | Not omittable merely because there is no RAG or persistent memory |
| External reads | Scope/data controls, deadlines, current authorization and evidence | No external access |
| External mutation | Durable operation identity, idempotency or reconciliation, bounded retries, cancellation and unknown-effect handling | Interface and credentials make mutation unavailable |
| Multiple tenants or classified data | Isolation, purpose/classification checks, credential and evidence separation | Single declared trust domain with rejection of other domains |
| Model choice among skills | Admission before ranking, null selection, confusability tests and catalog bounds | Trusted code selects one exact release without model ranking |
| Workflow or sequential skill switching | Versioned transitions, binding/context replacement, stale-call fencing and restart | Only one activation; no workflow transitions |
| Persistent memory or retrieval | Authorized access, provenance, freshness, poisoning tests and retention | Interfaces absent; ordinary context controls still apply |
| Human takeover/handback | Quiescence, atomic transfer, owner epoch and stale-owner rejection | No transfer interface; approval alone is not takeover |
| Delegation, adaptive parallelism, remote agents | Child acceptance, authority attenuation, joins, handoff and local verification | Interfaces absent; parallel bounded tools alone do not imply multiple agents |
| Executable package assets | Explicit invocation, constrained runner, declared dependencies and untrusted outputs | No assets; loading stays passive in either case |

Each omission needs a reason, a verified absent/disabled interface, an owner
and a change trigger. Unknown applicability stays unresolved, not automatically
`NOT_APPLICABLE`.

### D2. Reduce implementation and reading burden without removing controls

Logical roles need not become separate services, classes or products. One
process and one transactional store may implement the first experiment. Map
each authoritative aggregate to its trusted writer, authorization rule,
version/fencing check, durable commit and evidence path. Keep this at system
level; review changed rows per feature.

Do not delete admission, context assembly, lifecycle checks or workflow control
because their implementation is a small function. Retain canonical SOAA names
with plain explanations. An owner epoch is a fencing token; a durable envelope
is not necessarily an outbox. State and evidence can share one transaction.

### D3. Preserve the distinctions that prevent false success

- Skills provide procedure; models propose; trusted code authorizes and commits.
- Evaluators measure; deterministic gates evaluate required evidence; task
  controllers commit completion.
- Pins identify bytes. Admission, revocation and current authorization decide
  whether those bytes may be used now.
- Delivery skills installed in coding agents need explicit runtime binding and
  controls before they become governed application skills.
- Fixed model-call sequences are workflows, not automatically adaptive agents.
- Remote capabilities need explicit semantic mapping. A protocol name or
  remote completion claim supplies neither local authority nor local success.

### D4. Keep defaults optional and deviations visible

Provide a small worked example tested with controlled GovKit fixtures in
Phase A; use Phase B evidence to refine a real application recipe.
Framework/database choices are implementation details unless a control depends
on them. Do not require an ADR solely for choosing a different product than
an example.

Record significant trust-boundary and recovery decisions. An ADR can document
an experiment's deviation; it cannot turn a failed mandatory requirement into
conformance. Separate source alignment, accepted policy, advisory examples
and execution evidence.

### D5. Preserve compatibility until replacements work

Retain pack ID, capability tokens, existing paths and `multi_agent: true`.
Any new declaration needs coordinated schemas, templates, CLI checks, both CI
providers and three-agent payload coverage. Existing topology checks must not
silently become inapplicable.

Declarative packs install to `.govkit/packs/<id>/<digest>/`; legacy preflight
scans `extensions/*/manifest.yaml`. Implement verified resource discovery before
advertising a complete declarative SOAA workflow. Mixed installations must
surface conflicting copies. Installed guidance is not accepted project policy.

### D6. Make architectural learning part of feature delivery

GovKit should support a general development loop; the SOAA extension supplies
the architecture-specific questions and controls. This is proposed behavior,
not a claim that the current CLI closes the loop automatically.

| Step | Input and decision | Reviewable output |
|---|---|---|
| Requirements | Read incoming intent, acceptance criteria, affected code and accepted project contracts | Normalized request with explicit unknowns and impact scope |
| Architecture preflight | Map behavior to applicable SOAA responsibilities; distinguish supported decisions, known violations and untested assumptions | Changed architecture boundaries, required controls, evidence gaps and hypotheses |
| Experiment planning | Choose the smallest implementation that can answer each material uncertainty | Hypothesis, test conditions, oracle, acceptance threshold, limits and decision affected |
| Implementation and execution | Build the feature slice and run behavioral, evaluation and relevant fault tests | Working code and evidence tied to the exact target and conditions |
| Reassessment | Compare results with acceptance and hypotheses; inspect actual changes | Keep, revise or reject the proposed design; update affected decisions, controls and tests |
| Feature completion | Recheck accepted behavior and required controls after the last material change | Demonstrated feature acceptance, current architecture record and explicit remaining limitations |

Reuse request planning, architecture preflight, implementation planning and
actual-change conformance. Extend their existing artifacts with these fields
and links before adding new commands or mandatory documents. Give an ordinary
change within a tested boundary a short path; experiments are for material
uncertainty, not a ritual required for every edit. Use reusable evidence when
its target and assumptions remain valid, and invalidate it when relevant
runtime, skill, policy, interface or requirement changes occur.

Preflight needs an explicit “experiment required” outcome. It must not force
an unproven design to be labeled aligned merely to begin a contained prototype.
A known violation of an accepted boundary still requires an authorized change
or a narrower experiment. Experimental findings may motivate a revision to
SOAA; they do not silently rewrite accepted product requirements or policy.

The intended benefit is to integrate architecture work into useful delivery
slices and reduce speculative infrastructure built far ahead of need. Some
decisions still precede consequential execution: task/state identity, tenant
and data boundaries, authority, effects and recovery. GovKit should expose
those dependencies without demanding a complete design for every future pillar.

### D7. Distinguish model use, runtime skills and multi-agent coordination

Extension applicability follows the application behavior, independently of
agent count:

| Behavior | Applicable guidance |
|---|---|
| Calls language models | LLM application contracts for model access, evaluation, observability and guardrails |
| Uses governed runtime skills, adaptive agents or their control boundaries | Applicable SOAA contracts, including for one agent with fixed skills |
| Coordinates multiple agents through delegation, handoff or adaptive parallel work | Additional topology and coordination requirements |

Value Builder's 2–3 discovery skills do not by themselves make it multi-agent.
If its runtime invokes models and governed skills, both extension concerns
apply. Its actual agent topology must be established separately.

Current legacy templates use `mode: llm` and optional `multi_agent: true` in
`eval_criteria.yaml`. The associated `nfrs.md` contains LLM latency, cost,
fallback and safety requirements, not those routing switches. General
architecture preflight discovers contracts by feature intent and touched
files. GenAI preflight section 6 already has a broad agent/skill trigger, but
L5 backend entry instructions condition their SOAA reading instruction on
`multi_agent: true`. Reconcile this inconsistent guidance across all three
agents and both backend API/CLI variants.

There is no dedicated machine-checked SOAA feature flag in this path today.
The declarative request path's `impacts.llm` selects LLM evaluation obligations;
it is not equivalent to installing every LLM architecture resource. Keep
installation, applicable guidance and required checks distinct. Choose a
canonical capability declaration integrated with accepted profiles/request
planning before adding machine-readable SOAA routing. Keep NFRs as supporting
requirements and avoid conflicting duplicate switches. Any new field must
arrive with schema, templates, preflight, CLI/CI and parity coverage; until
then preserve existing LLM and multi-agent declarations.

## 3. Consuming-project pilot after GovKit delivery

The user identified **AIPOS Value Builder** as the proposed pilot on 2026-10-19.
The user-described application has five pillars: Pillar 1 leads a team through
discovery using 2–3 skills; rapid validation uses a different skill set; three
further pillars follow. The count and behavior are user-provided context, not
an inspected catalog. The remaining pillar names, checkout, runtime and exact
task are not yet verified. The original draft's package counts are not a basis
for this pilot.

The user will install the completed Phase A package in the consuming project
before using its preflight and experiment workflow to develop Value Builder.
GovKit implementation can proceed with representative fixtures; access to the
Value Builder checkout is needed when the pilot begins, not before.

For that pilot, choose one useful bounded adaptive task, one exact skill, one tool boundary,
one completion gate and one recovery path. Start with synthetic data and a
reversible local effect. Use a service fixture capable of “effect applied,
response lost” faults before enabling real external mutation.

For Value Builder, use these bounded slices:

1. **One discovery task:** select an actual task and representative skill from
   the application. Exercise the E1 control skeleton through a team-facing
   result, with an observable acceptance criterion. Do not implement all
   discovery procedures before testing the runtime boundaries.
2. **Selection among the discovery skills:** extend the first skeleton with
   admission and selection tests for the 2–3 discovery skills. First
   establish whether selection is made by a person, trusted workflow, model,
   or a combination; catalog size alone does not require model ranking or
   semantic retrieval. Include overlapping descriptions, ambiguous requests,
   missing facts, null choice,
   incompatible/revoked releases and skills belonging to other pillars.
   Check appropriate selection and task outcomes with held-out cases, and
   record latency and cost. This can be part of E1; no separate large-catalog
   retrieval or scalability experiment is justified by the stated scope.
3. **Discovery to rapid validation:** implement one real transition with an
   accepted input/output contract, versioned artifacts and a gate based on
   the team's required outcomes. Change skill eligibility and context through
   trusted workflow state. Test a premature transition, a delayed discovery
   operation, a restart at transition and a later revision of an upstream
   artifact. Whether teams may revisit earlier pillars remains to be specified;
   if supported, define which downstream evidence becomes stale.
4. **Subsequent pillars:** add one useful slice at a time, reusing proven
   boundaries and testing only new assumptions plus affected regressions.
   Discover common abstractions from these implementations before building
   a general engine for all five pillars.

The pillar workflow, workspace artifacts, skill eligibility and business
progression gates belong to Value Builder's runtime. Pillars and skill counts
do not determine AgentRun count. A long-lived team workspace can span many
bounded tasks and runs; each active task still has one current owner. Keep
business progression criteria distinct from runtime task-completion controls.

GovKit governs the development of these capabilities: requirements, preflight,
experiments, implementation, architecture decisions and evidence. The SOAA
extension guides that work; it does not make GovKit the application's runtime
or automatically execute the application's business skills.

Record repository/revision, accountable owner, task acceptance criteria, actual
adaptive decision, data/tenant boundaries, credentials and effects. Pin runtime,
skill, dependencies, policy, gate and test adapter. Declare unsupported actions,
persistence/failure model, writer map and applicability decisions. Measure
baseline build effort, task outcomes, latency/cost and recovery burden.

These facts are needed for the consuming-project pilot. They do not block
Phase A's GovKit implementation. Value Builder is the proposed application;
its runtime has not been inspected, executed or certified in this review.

## 4. Phase B experiments and stopping conditions

These cases guide experiments during Value Builder development after the
GovKit changes are installed. Phase A tests the workflow with controlled
examples; those tests establish tooling behavior, not application correctness.
Select experiments for actual uncertainty and exposed capabilities. This is
not a mandatory experiment suite for every feature.

Each experiment adds a hypothesis and a bounded capability. Run positive,
negative and fault cases against the actual adapter. Deterministic fixtures
help test faults but have disclosed limits. Execute the real model-facing
adapter before claiming model-driven behavior; keep most control tests
deterministic and inexpensive.

| Experiment | Hypothesis and scope | Evidence required before expansion |
|---|---|---|
| E1: control skeleton | One adaptive task preserves ownership, authority, activation and completion with modest effort | Accepted/rejected offers; exact binding; denied model writes; labeled context; blocked false success; finite budgets; process restart and reconstruction |
| E1b: Value Builder skill choice (part of E1) | The 2–3 discovery skills can be selected appropriately without weakening activation controls | Held-out selection/null/ambiguity cases; eligibility and release-state rejection; task outcome, latency and cost evidence |
| E2: controlled mutation | Lost acknowledgment does not duplicate effects or create false terminal success | Intent-before-effect; stable operation ID; crashes before/after effect; reconciliation; cancellation; late results; retry/recovery budgets |
| E3: sequential skills | A versioned workflow switches skills without stale authority or instructions | Atomic transition; context replacement; delayed old calls rejected; version conflicts; crash/restart; failed activation leaves consistent state |
| E4: targeted extension | A needed feature does not import unrelated obligations | Choose ranking, memory/RAG, multi-tenant use or takeover separately; run relevant D1 cases and common invariants |
| E5: delegation/portability | A product need justifies cross-owner or cross-runtime complexity | Child acceptance, authority attenuation, transfer/joins, remote false completion or independently implemented differential behavior |

Do not enable mutation beyond the fixture until E2 demonstrates failure
semantics. Timeout does not mean rollback. Unreconcilable effects stop new
unsafe work and remain unknown for an authorized operator. Compensation is a
new authorized operation. Do not finalize success while required effect/evidence
outcomes are unresolved.

Halt expansion when a counterexample breaks ownership, authority, evidence or
completion, or the control burden is unjustified for the consequence. Revise
the control or narrow supported behavior; do not weaken tests to preserve a label.

## 5. Local behavioral catalog

These are proposed consuming-project cases, not implemented tests or
replacements for SOAA's assertion catalog. Phase A may use representative
results to test routing, evidence and reassessment. Executing an applicable
case against Value Builder is Phase B work.

| Local case | Trigger | Required observation |
|---|---|---|
| GK-SOAA-01 | Rejected/replayed task offer | Rejection has no owner; replay creates no duplicate work |
| GK-SOAA-02 | Concurrent task claim/advance | One writer succeeds; stale writer fenced |
| GK-SOAA-03 | Model/skill requests state, policy or credential write | Trusted boundary refuses and records reason |
| GK-SOAA-04 | Pinned release incompatible, tampered or revoked | Admission/activation fails despite known name |
| GK-SOAA-05 | Activation crash or authority change before commit | No partial activation or early instruction exposure |
| GK-SOAA-06 | Grant expires/revokes after activation | Next operation denied; cached activation cannot restore access |
| GK-SOAA-07 | Input/tool output contains instructions | Remains data; cannot expand permissions or change policy |
| GK-SOAA-08 | Skill/evaluator claims success without evidence | Gate refuses; controller cannot commit success |
| GK-SOAA-09 | Evidence failure at state commit | Transaction/envelope preserves reconstruction; no evidence-free success |
| GK-SOAA-10 | Effect succeeds; response lost | Identity and reconciliation prevent blind duplicate mutation |
| GK-SOAA-11 | Cancel before dispatch, in flight or after effect | Stop unsafe dispatch, record late results and preserve uncertainty |
| GK-SOAA-12 | Restart with active/uncertain work | Reconstruct, reauthorize and reconcile before retry |
| GK-SOAA-13 | Retry/time/cost/output exhaustion | Safe stop and bounded recovery capacity |
| GK-SOAA-14 | Workflow advances with delayed old call | Old binding/context/owner version cannot mutate new step |
| GK-SOAA-15 | Stale, forged, duplicate or incomplete results | No authenticated execution claim or broader pass |
| GK-SOAA-16 | Omitted feature's interface is reachable | Applicability fails or unsupported operation is denied |

Conditional features add cross-tenant access, poisoned memory, null selection,
revoked approval, in-flight takeover, delegated authority widening and false
remote-completion cases as appropriate. Use deliberately broken implementations
to demonstrate that critical tests detect the failures they claim to detect.

## 6. Evidence and result handling

Record exact runtime/skill/policy/test/adapter revisions, environment, model
configuration where observable, fixtures, task/operation IDs, times, result
states, applicability, evidence references, assessor mode, limitations and
invalidation triggers. Disclose limits on provider model reproducibility.

Reuse GovKit's check/evidence states. Required unknown, skipped, failed or
unconfigured cases cannot satisfy obligations. `NOT_APPLICABLE` requires a
verified absent trigger for a conditional requirement. Reject or withhold pass
for missing rows, duplicate/unknown IDs, stale scope, contradictory evidence
and unapproved waivers.

Keep three claims distinct:

1. Report validation checks schema, identity, coverage, applicability and
   internal consistency of supplied data.
2. Observed execution comes from a trusted runner binding target/cases to
   collected evidence. An uploaded JSON assertion alone cannot supply this.
3. Formal conformance requires the released applicable SOAA profile and
   verified assertion catalog. Certification is separate.

Required checks derive from accepted policy outside inspected content. A pack
check with `required: false` is optional until project policy requires it. Packs
cannot remove existing obligations. Evidence should minimize sensitive content;
specify access, retention, deletion/redaction and validity effects before using
customer data. Append-only logs alone do not establish evidence authority.

## 7. Implementation increments

### Phase A: deliver GovKit and the refined SOAA extension

| Increment | Deliverable | Exit criterion |
|---|---|---|
| A0: baseline | Review, original archive, source/defect register and agreed delivery boundary | Tooling changes, illustrative fixtures and later application proof clearly separated |
| A1: development loop | Extend request planning, preflight, implementation planning and reassessment with uncertainty, experiment and decision/evidence links | D6's loop works on representative changes; established boundaries use a short path; material unknowns produce explicit experiment work |
| A2: SOAA refinement | Revise README/common contract, applicability guidance, control/writer examples and experiment guidance; retain necessary topic contracts | Single-agent and 2–3-skill cases are usable without a maturity ladder; controls remain intact; source discrepancies are resolved or bounded explicitly |
| A3: routing and discovery | Align LLM/SOAA/multi-agent triggers; supply explicit pack resources and verified legacy/declarative discovery | Three-agent API/CLI parity; no lost topology checks; markerless/legacy installs work; conflicting copies are surfaced |
| A4: checks and evidence | Implement result validation, scope/coverage/applicability checks and reassessment using existing infrastructure | Missing/stale/failed required evidence cannot pass; results cannot authenticate themselves; changed assumptions invalidate affected decisions/results |
| A5: installable handoff | Build and verify the package, worked examples and installation/use instructions | Installed-wheel tests demonstrate the complete development loop and compatibility; user can install and start the pilot |

Phase A acceptance includes these end-to-end fixture scenarios:

- A requirement within an established boundary proceeds without unnecessary
  experiments.
- An uncertain architectural assumption produces a bounded experiment with
  explicit acceptance criteria and permitted effects.
- A failed experiment returns the work to design/implementation with the
  original requirement intact; a revised implementation is retested.
- A passing experiment supports only its observed scope, and feature completion
  still checks all applicable accepted requirements and controls.
- A changed requirement, skill, policy or implementation invalidates affected
  evidence and causes reassessment.
- Model-backed features, single-agent runtime skills and multi-agent topology
  receive their respective guidance/checks without conflating the triggers.

Use actual installed GovKit code in these fixture workflows. Clearly identify
synthetic experiment results and mocked application boundaries. Phase A is
complete when the tooling and guidance satisfy these acceptance conditions
and the package is ready for the user's installation; it does not claim SOAA
runtime proof or require Value Builder to be built first.

### Phase B: user installation and Value Builder validation

| Increment | Deliverable | Exit criterion |
|---|---|---|
| B0: install and configure | User installs the completed package in the Value Builder project and establishes project requirements/policy | Applicable LLM/SOAA guidance is discoverable; first task and acceptance criteria are ready for preflight |
| B1: discovery slice | Develop the first useful task with E1/E1b experiments when needed | Working discovery behavior with evidence for its 2–3 skills and applicable controls |
| B2: effects and pillar transition | Develop relevant mutation/recovery and discovery-to-validation behavior using E2/E3 where applicable | Requirements, effects, state transfer and recovery are demonstrated against the actual runtime |
| B3: subsequent pillars and feedback | Deliver later slices, use E4/E5 only for a named need, record architectural and adoption findings | Findings drive explicit follow-up changes to GovKit, the SOAA extension or the application |

Payload changes require Codex/Claude Code/Copilot parity. Preserve contract-set
IDs and capability tokens; version the extension when behavior changes. This
plan revision alone needs no extension version bump.

Do not route untrusted runtime scripts through today's pack-check subprocess
path. It is opted in but unsandboxed, without deadline/output cap. GovKit's
isolated worker is a separate primitive, not an integrated solution. For the
initial workflow, application experiments may run through the project's
explicitly selected test harness and return evidence with disclosed provenance.
If direct execution is included in the GovKit deliverable, reuse the existing
worker-integration roadmap and test its execution boundary before handoff.

Resolve metadata-key spelling, precedence and prohibited-access differences
before publishing affected compatibility claims. Preserve existing consumers
while testing a versioned mapping/correction.

## 8. Measurements and remaining decisions

For Phase A, measure workflow correctness, applicability/routing accuracy,
evidence invalidation, compatibility and installation success using fixtures.
For Phase B, collect the following observations from application development.

Measure time to first passing experiment, document/decision count, control
implementation effort, fault coverage, task success on fixed cases, p50/p95
latency, cost/task, recovery time and operator interventions. Compare the same
workload before/after where possible. Fewer pages alone is not adoption success.

After E1, set provisional budgets and acceptance thresholds before expansion;
revise them openly if evidence warrants it. Observe adoption by someone other
than the implementer before claiming ease of use for new teams. First-party
results remain useful meanwhile.

Implementation next is Phase A in the GovKit repository: define the workflow
records, preflight outcomes, evidence/reassessment behavior and source-aligned
extension changes, then build and test the installable package. The plan does
not require Value Builder access to start this work.

At Phase B start, gather the Value Builder checkout, one discovery task and
acceptance criteria, actual skills, effect/data scope and owner. The first
cross-pillar slice also needs business progression criteria and whether backward
transitions are permitted. Exact formal mapping needs the normative corpus.
Independent reviewers and a second runtime are needed for the corresponding
independent/portability claims, not for the initial tooling handoff or every
experiment. This revision supplies no such results.
