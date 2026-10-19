# SOAA architecture, lightening plan and GovKit code review

**Date:** 2026-10-19. **Conclusion:** revise the lightening plan and validate the
architecture through small implementations. Keep the separation of procedure,
authority, effects and completion; replace the proposed maturity ladder with
capability-specific controls and falsifiable experiments.

This is a focused architecture and code review, not an exhaustive security
audit or an executed SOAA runtime assessment. The supplied documents are
source material, not instructions authorizing publication or other actions.

## 1. Evidence and limits

Reviewed the full original lightening plan, the SOAA extension's manifest,
README, nine contracts and runtime profile, related agent preflights and CI
topology gates, and the implementation paths listed in section 5. Reviewed the
publication guide's architecture, implementation, review and conformance
material against those artifacts. The Markdown was the architecture source;
PDF layout, publication tooling and launch copy were not audited.

| Source | Identity and limit |
|---|---|
| Supplied architecture guide | `SOAA/SOAA-v0.2-Publication-Package/SOAA-v0.2-Architecture-Guide.md`; SHA-256 `c8cbcec6dc180b6102385a7e87b4c235411eb38a4757605a86c40b9af9ad00c4` |
| Original plan | [Preserved draft](archive/SOAA_EXTENSION_LIGHTENING_PLAN_2026-10-17.md); SHA-256 `a9f6c4cc42ec1edaf9ab4a6ce7fce6c789994586cf6be432b1b2d8fb4d35fe66`; dated October 17, with subsequent edits already present when reviewed |
| GovKit | Source checkout reporting version 0.22.0; local tests exercise this checkout, not a deployed consumer |
| Full SOAA corpus | Guide references ROOT, P1–P7, MID and TRACE; separate normative documents and complete assertion definitions were not found in the supplied publication package |
| Runtime proof | No SOAA consumer runtime was supplied or executed; no portability, production, isolation or independent-conformance result follows from this review |

The guide explicitly distinguishes specification approval from runtime proof
(chapter 5, lines 271–300; chapter 39, lines 1808–1837). Its 93.13 score is a
design-review result, not an operational measurement. Appendix G says the full
206-row catalog is not reproduced. These are useful limits, not reasons to
stop experimenting.

The original extension build record reports earlier access to the approved
corpus. That historical statement does not resolve today's discrepancies
without the exact source revision and definitions. Neither this review nor
the publication guide should silently overwrite that missing provenance.

## 2. Highest-priority findings

Priorities here mean P1: resolve before relying on the affected behavior or
claim; P2: address during the next relevant increment. A design finding is not
automatically a shipped code defect.

| ID | Priority / category | Finding | Disposition |
|---|---|---|---|
| C1 | P1, reproduced code defect | Legacy extension validation can report PASS for malformed declared fields and incomplete contract sets | Fixed with shared schema validation and regression tests |
| C2 | P1, reproduced parser discrepancy | Duplicate YAML keys silently replace declarations; aliases accepted on the legacy path but rejected by pack loading | Fixed by using the existing strict parser |
| C3 | P2, reproduced reporting defect | Numeric `description` causes extension reporting to raise `AttributeError` | Fixed by checking manifest shape before rendering |
| P1 | P1, proposed-plan defect | Three rungs use complexity as a proxy for security and consequence | Replaced with an applicability matrix and experiment sequence |
| P2 | P1, proposed-plan defect | Fixed pins substitute for admission, revocation and dependency controls | Retain these controls for fixed binding |
| P3 | P1, proposed-plan defect | Sequential switching, cancellation and takeover are included without sufficient atomicity/fencing/reconciliation detail | Explicit fault cases and capability prerequisites |
| P4 | P1, integration gap | Declarative installation paths are invisible to legacy SOAA preflight; a rung-only declaration does not activate existing topology checks | Discovery work required; preserve existing declaration until all readers change |
| P5 | P1, evidence-design gap | Result-file validation, optional check selection and runtime proof can be conflated | Distinct report-validation, observed-execution and conformance claims |
| S1 | P1 for compatibility claims, source discrepancy | Metadata names/profile ID and instruction hierarchy disagree across guide and extension | Resolve exact authority/version before publishing compatibility claims |
| S2 | P1 for authorization semantics, source discrepancy | Guide subtracts prohibited skill access explicitly; extension formula does not | Define and test the mapping, rather than assuming the requested-scope term covers it |
| A1 | P2, architecture proof gap | Ownership, recovery, evidence and security boundaries remain design claims without an exercised runtime | Minimum control skeleton plus negative controls and process-failure tests |
| C4 | P1 for untrusted execution, known limitation | Pack checks are unsandboxed and have no process deadline/output bound | Recorded; isolated worker integration remains separate work |

## 3. Holes in the original lightening plan

### 3.1 Complexity is the wrong switch for many controls

Original D1 and the demotion register move full authority, classification,
release lifecycle, revocation and much recovery behavior to higher rungs. A
single pinned billing skill can cross tenants and mutate real accounts; a
large catalog can be read-only. These controls follow consequences and exposed
interfaces, not catalog size or agent count.

Memory or RAG also should not force unrelated MCP, delegation or package
obligations. Conversely, an ordinary user document or tool result creates an
untrusted context boundary without persistent memory. The revised plan treats
these dimensions separately and requires evidence for each omission.

The existing extension already supports topic-based contract loading in its
README. The original draft's assertion that every requirement binds every
adopter is too broad. The actual problem is that broad core obligations and
feature-based loading lack an easy, tested path through a small implementation.

### 3.2 Fixed binding removes search, not admission

Guide chapter 8, lines 427–457, explicitly retains compatibility, dependencies,
conflicts, authority, approvals, activation and evidence for fixed binding.
Exact digests do not prevent use after revocation or grant expiry. A changed
tool, dependency or environment can invalidate a previously usable release.

The original D1a allows the model to choose from a fixed menu. Under the
guide's definitions this still involves dynamic selection. It can be a small
selection implementation, but its admission and null-selection tests cannot
be dropped under a fixed-binding label.

### 3.3 Sequential binding is a transaction problem

Original D1b and R1-22 constrain order and permissions, but leave the hard
failure boundaries insufficiently specified: a crash between ending the old
activation and creating the new one; an old async call arriving after the
transition; stale skill instructions remaining in context; approval/revocation
changing between validation and commit.

Define one versioned transition over workflow state and active binding, with
an explicit context identity and stale-call rejection. If the implementation
uses separate stores, demonstrate recovery from partial commits. A simpler
state machine is a reasonable implementation; the control responsibilities
still exist even if no component is called a Workflow Controller.

### 3.4 Cancellation and human takeover cannot be deferred by rung

Once E2-style mutations or owner transfer exist, “stop” must distinguish
undispatched, in-flight, completed and unknown effects. Canceling a process
does not cancel a remote effect. Task fencing alone does not stop an already
dispatched external call. Late outcomes need an operation/evidence path that
does not mutate an immutable terminal task incorrectly.

Takeover requires quiescence and a committed owner transition. The guide also
requires a new AgentRun on handback, so counting more than one AgentRun over a
task's lifetime would misclassify ordinary sequential handback as multi-agent
coordination. Count actual concurrent/delegated responsibilities instead.

### 3.5 Consumer feedback needs an explicit place in delivery

Original increments 0–9 concentrate on trace tables, terminology, contracts
and check artifacts before the consumer result in increment 10. This risks
optimizing prose around an architecture that has not been built. Name the
consumer early to ground the use cases and acceptance examples, then include
an explicit feedback stage for real implementation findings.

The user clarified the delivery sequence after review: first implement and
test the GovKit workflow and refine the SOAA extension; then the user installs
GovKit in a project and develops Value Builder to verify the approach. Controlled
fixtures establish the tooling's behavior before that handoff. Actual runtime
evidence comes from the later pilot and informs subsequent refinement; building
Value Builder is not a prerequisite for delivering the GovKit changes.

An independent outside assessor is unnecessary for the first learning cycle.
Guide Appendix E explicitly allows first-party assessment. Keep its scope
honest; reserve independent claims for independently produced evidence.

### 3.6 New declarations need coordinated enforcement

The existing topology CLI checks and both CI templates detect
`multi_agent: true`. A temporary feature containing only
`agent_skills_rung: 3` made both topology checks return PASS/not applicable;
adding `multi_agent: true` made the missing topology fail. That reproduces a
hole in the proposed rollout, not a bug in a shipped rung feature: no such
feature exists yet.

Likewise, `govkit pack` installs content-addressed resources while architecture
preflight scans `extensions/*/manifest.yaml`, and GenAI preflight checks exact
legacy paths. A working loader does not make guidance discoverable to those
agents. Cover markerless, legacy and mixed installations before recommending
the route as complete.

A direct `load_pack` probe also confirms that the current SOAA snapshot omits
its README and declares no executable checks. The original draft correctly
proposes explicit resources including the README; retain that work and add
the missing discovery integration.

The original motivation also says L5 SOAA loading happens only for multi-agent
features. GenAI preflight section 6 already triggers on agents, skills and
adaptive orchestration. Its problem includes path coupling. A follow-up check
also confirms that the L5 backend entry instructions still condition their
SOAA reading instruction on `multi_agent: true`, creating inconsistent routing
guidance. Align those entry points with the broader preflight applicability;
keep multi-agent topology requirements separate. The current template flags
are in `eval_criteria.yaml`, while `nfrs.md` carries supporting requirements.

### 3.7 Passing reports need stricter scope semantics

Original R1-22 is conditional on sequential binding, while the proposed result
validator rejects skipped assertions and expects all results to pass. Define
valid conditional non-applicability and its proof. Preserve required unknown,
error and missing evidence as non-passing. An ADR records a deviation, not a
waiver inside a conforming result.

The original draft correctly notes that a pack check can start optional and
become required through accepted policy. Implementation must actually connect
that policy, the claimed target and the executed evidence. Merely listing a
check in a manifest cannot enforce a claim or authenticate a results file.

Original R-5 (“Only an evaluator completes a task”) assigns the wrong writer.
The guide separates evaluation result, gate decision and task-state commit.
The revised plan preserves all three. It also avoids replacing every durable
envelope with an outbox, or reducing instruction hierarchy without a tested
semantic mapping.

## 4. SOAA itself: what needs proving or refining

These are implementation questions exposed by the architecture, not claims
that the guide ignores the topics. Much of it describes the right safeguards;
the missing evidence is whether the safeguards compose and remain practical.

| Question | Concrete failure to test | Decision/evidence needed |
|---|---|---|
| Where does trusted authority begin? | Edited local policy or a compromised publisher supplies a valid-looking release/approval | Identify control-plane writers, policy custody, release provenance and credential boundaries; a digest alone proves no publisher identity |
| Can one owner actually prevent duplicate effects? | Fenced worker's earlier request reaches an external system after takeover | Adapter/broker fencing where possible, stable operation IDs, resource concurrency rules and reconciliation where external fencing is unavailable |
| Are recovery and evidence commits compatible? | Task checkpoint, operation ledger and evidence advance to different versions across a crash | Commit protocol plus observable crash-point tests; reconstruction cannot rely on a model transcript |
| What happens during lifecycle-store outage? | Cached “admitted” status outlives a revocation or fresh check cannot complete | Explicit freshness window, safe stop behavior and availability tradeoff by consequence; recovery cannot use revoked instructions |
| Can completion run when execution exhausts its budget? | Agent spends the remaining time/cost before evaluation, evidence or reconciliation | Reserved bounded recovery/evaluation capacity and terminal/unknown outcome rules |
| Does context governance protect control authority? | Injection is correctly labeled but the model still proposes a forbidden operation | Enforce permission and state checks outside the model; source labels are useful metadata, not proof of injection resistance |
| What makes an evaluator independent enough? | Same model/context reproduces the producer's mistake and votes PASS | Define independence dimensions by consequence; objective oracles, calibration and counterexamples; a second call alone is not independence |
| How do immutable records handle sensitive data? | Evidence contains secrets/customer content that must later be removed | Data minimization, access control, retention and redaction/deletion validity rules; a content digest may not be enough to reconstruct a semantic claim |
| Can “not applicable” hide reachable behavior? | Memory or delegation omitted from scope while an adapter still exposes it | Capability guard tests, disabled interfaces and re-review on configuration changes |
| Does the architecture repay its cost? | Small teams implement broad abstractions and documentation without measurable reliability benefit | Time-to-first-task, fault detection, recovery burden, latency/cost and comparison with the same workload's baseline |

The most valuable next artifact is a small running implementation that fails
under deliberately broken controls and recovers under injected faults. Another
large cross-reference document cannot substitute for that result. Full
portability requires a separately implemented second runtime; two adapters
sharing the same controller do not establish independent semantics.

## 5. GovKit code review

### Reproduced defects fixed in this working tree

`cli/extensions.py` previously checked field presence and selected paths but
did not invoke the bundled manifest schema. Examples such as
`contract_sets: broken`, `id: 42`, or a contract set with no `paths` returned no
validation issues. `cli/check_adapters.py` consequently emitted a narrow but
incorrect PASS for declared shape/path validity.

The legacy parser also used `yaml.safe_load`, which silently accepted repeated
keys. A later `contract_sets: []` could erase the earlier declaration. The
declarative pack path already rejected these inputs via `schema_validation.py`.

Changes:

- Reuse `parse_document` for unambiguous JSON-shaped YAML on the legacy path.
  Duplicate keys, aliases and non-JSON values now receive diagnostics.
- Validate the existing `extension-manifest` schema before path/relationship
  checks. Invalid nested types cannot be skipped or crash later traversal.
- Check shape before display so malformed descriptions produce a warning.
- Add 18 regression cases, including actual `inspect_repository` results and
  read-only snapshots. Update existing diagnostic expectations to the shared
  schema's messages; change one test that previously required silently
  ignoring malformed `relates_to` to require rejection.

Compatibility effect: previously tolerated malformed manifests now produce
issues. Valid bundled packs retain their paths/IDs. This does not change
legacy warn-versus-strict policy or make `extension add` an atomic validation
gate; it still surfaces validation notes after installation. It also does not
establish runtime contract compliance.

### Reviewed boundaries and remaining limits

| Area | Code reviewed | Assessment |
|---|---|---|
| Loading/resolution | `pack_loading.py`, `pack_resolution.py`, `schema_validation.py` | Useful strict schemas, contained resources, pinned bytes, explicit dependency/provider resolution; pins are not publisher authentication or accepted policy |
| Installation | `pack_store.py`, relevant `cmd_extension.py` paths | Declarative integrity/protection checks are distinct from legacy copy-and-warn behavior; keep migration and consumer-path semantics explicit |
| Check semantics | `check_models.py`, `check_runner.py`, `check_adapters.py`, `conformance.py` | Required non-pass states remain unsatisfied; report parsing explicitly does not authenticate origin; extend this engine rather than inventing SOAA success aggregation |
| Command boundary | `pack_store.execute_check`, `change_conformance.py`, `command_worker.py`, ADR 0019 | Pack check has no timeout/output cap and inherits process environment. Change command has a timeout but ordinary subprocess authority. Isolated worker is intentionally separate; no integration was added here |
| Architecture routing | `validate.py`, backend architecture/GenAI preflights, GitHub/Azure multi-agent gates | Current topology behavior is based on `multi_agent`; declarative resources require a discovery bridge before the proposed adoption path works end-to-end |
| SOAA tests | `test_skill_oriented_agent_architecture.py` and related extension/pack tests | Useful manifest, content, installation and preservation checks; phrase presence and package validation do not exercise a runtime's authority/recovery behavior |

The unsandboxed execution limitation is already disclosed in the 0.22.0
changelog and ADR 0019. It is a prerequisite for stronger untrusted-execution
claims, not a newly discovered secret or a reason to claim the whole CLI is
unsafe. The smallest scope here was to fix the false structural pass and leave
the worker integration as its own tested change.

Other unchanged release limits include unverified protected enforcement and
absence of consenting-team adoption measurements. A passing local suite cannot
close either gap.

## 6. Source reconciliation register

| Topic | Guide | Current extension / original draft | Required treatment |
|---|---|---|---|
| Package metadata | Chapter 30, lines 1442–1445: dotted `soaa.*` keys; profile example `urn:soaa:agent-skills:1` | `SKILL_CONTRACT.md` lines 90–104: hyphenated `soaa-*`; `soaa-agent-skills/0.2` | Verify canonical profile version; version aliases/migration and test conflicting dual declarations; do not silently rename |
| Instruction hierarchy | Chapter 17, lines 820–828: five instruction sources plus data, including AgentDefinition | Authority contract lines 129–141: seven levels with different grouping and current user interaction | Publish an explicit mapping or correction; keep deterministic permission enforcement separate from prompts |
| Skill prohibitions | Chapter 16, line 781 explicitly subtracts `ProhibitedAccess(s)` | Authority contract lines 26–30 subtracts only `ExplicitDenies` after requested scope | Prove that requested scope/denies encode all prohibitions or add the missing term; denial test must cover overlapping requested and prohibited access |
| Primitive decision identity | Appendix B names SOAA-003 “Primitive Responsibility Boundaries”; SOAA-010 covers trusted roles | Original Q9 treats SOAA-003 as unknown; role-demotion mapping uses wrong/coarse decision references | Correct decision mapping; exact assertion mapping remains pending TRACE |
| Precedence of sources | Appendix G documents normative source precedence | Original plan assumes simplifying consumer precedence may be merely advisory | Retain source authority; scope conflict to affected claim/path; label experimental deviations |
| Assessment | Appendix E supports first-party, second-party and independent modes | Original reference implementation requires reviewer outside implementing team | Permit honest first-party learning; require independence only for its corresponding claim |
| Applicability | Appendix E allows justified conditional `NOT_APPLICABLE` | Original all-pass validator and conditional R1-22 are inconsistent | Explicit guard, reason, disabled-interface evidence and re-evaluation trigger |

Do not interpret the guide's publication release checklist as a blocker on
this user's internal analysis. No source publication or upstream document
modification was performed.

## 7. Disposition of the original decisions

| Original element | Decision |
|---|---|
| D1 three rungs and D9 inferred maximum | Replace with consequence/capability applicability; unknowns remain explicit |
| D1a fixed model-selected menu | Keep as small selection experiment with admission/null choice |
| D1b sequential fixed binding | Keep as E3 with atomicity, context and stale-call fault tests |
| D2 contract-set remap | Refine applicability and guidance in the GovKit delivery; preserve IDs/tokens and use later pilot evidence for further changes |
| D3 common contract / D4 preflight | Retain a concise entry point, system-level writer map and per-feature deltas |
| D5 precedence and ADR deviations | Separate source alignment, project policy, experiments and formal conformance |
| D6 two meanings of skill | Retain and strengthen explicit runtime-admission requirements |
| D7 honest GovKit-only claims | Retain; name exact experiment and target instead of a new conformance rung |
| D8 agent-skill trigger | Retain intent; repair discovery and preserve existing topology enforcement |
| Demotion register / vocabulary pass | Replace blanket demotion with guarded applicability; use plain explanations without erasing semantic distinctions |
| Reference implementation in increment 10 | Name the pilot early; verify tooling with GovKit fixtures, then obtain runtime evidence after the user installs it |
| 206-item prerequisite | Needed for exact formal mapping, not a prerequisite for all experiments |
| Mandatory default stack / outside reviewer | Use tested example and first-party mode initially; stronger claims require stronger evidence |

## 8. Verification record

- Baseline focused architecture, evidence, extension, pack and conformance
  suites: **126 passed** before changes.
- New defect regressions: **18 failed before the fix**, covering malformed
  shapes, ambiguous YAML, reporting and false PASS through the real adapter.
- Installer fixture suite: **57 passed, 1 skipped**; the skip is the existing
  Codex glob-frontmatter case because Codex uses nested `AGENTS.md` files.
- Scoped Ruff checks passed for all changed Python files. Diff whitespace,
  report/plan links and the archived original's hash were checked.
- Full fast suite (`PATH="$PWD/.venv/bin:$PATH" ./run_tests -q --tb=short`):
  **5,239 passed, 2 skipped, 150 deselected** in 498.80 seconds. Both skips are
  existing non-Copilot `applyTo` cases; the wrapper deselects the e2e tier.
  The separate fixture run above covers 58 of those e2e cases. The remaining
  e2e/toolchain tier and a new installed-wheel run were not executed.

The plan's `GK-SOAA-*` catalog is proposed work. These are not tests executed by
the GovKit unit suite. No SOAA runtime, live tenant, remote effect, external
model, Docker isolation pilot or production pipeline was exercised here.

## 9. Next decisions

Following this review, the user identified AIPOS Value Builder as the proposed
pilot: discovery with 2–3 skills, then rapid validation with another
skill set and three further pillars. This context has been incorporated into
the revised plan; no Value Builder code or catalog has yet been inspected.

The user clarified that implementation next is in GovKit: deliver the
experiment-aware development workflow and refined SOAA extension, test them
with representative fixtures, and provide an installable package. Value Builder
development begins after the user installs that package in the consuming project.

At pilot start, obtain the checkout, one bounded discovery task, acceptance
criteria, actual skills, effect/data boundary and owner. Use E1/E1b and the
other experiments where uncertainty and application capabilities warrant them.
The cross-pillar slice also needs progression criteria and backward-transition
semantics. Exact normative documents are needed for formal mappings and
compatibility claims; they are not prerequisites for every tooling increment
or contained experiment.

The [revised plan](SOAA_EXTENSION_LIGHTENING_PLAN.md) contains the applicability
matrix, local case catalog, implementation order, stopping conditions and
measurements. This review does not approve production deployment or claim
that implementing every written control will be cost-effective.
