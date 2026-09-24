# Declarative governance implementation plan

Status: I00–I06 merged; I07 delivered in PR #187 with review remediation, awaiting re-review/merge.
Plan version: 1.20.
Prepared: 2026-09-23.
Baseline inspected: govkit 0.21.1, commit af819455cb19ebc01ce6bd56b6d6490e128bc1a5.
Primary epic: [#142 — Declarative, composable GovKit governance](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/142).

## 1. Authority and how to use this plan

This file is the execution source of truth for the agreed GovKit refactor. It consolidates the product decisions, implementation order, maintenance requirements, and issue acceptance criteria reviewed on 2026-09-23. A coding agent must be able to continue the work from this file and the repository without needing the originating conversation.

- Follow explicit current user/maintainer instructions and applicable repository instructions. Use this plan for scope, sequencing, implementation boundaries, and completion evidence.
- Linked issues provide traceability. Their acceptance criteria are captured in Appendix A. Read later issue changes as new input; reconcile material changes into this plan before implementing affected work. Do not silently expand the scope from an issue comment.
- Earlier plans in this directory describe historical decisions or completed work. They do not override the composable-capability and brownfield decisions below. Preserve still-applicable implementation constraints and compatibility.
- Routine implementation choices can be resolved and recorded by the coding agent. Escalate only unresolved product/architecture decisions, incompatible requirements, or actions beyond the authorized task.
- Update the execution ledger and handoff record after each increment. An unchecked criterion stays unchecked until its required behavior is demonstrated.
- Standing delivery instruction (2026-09-23): when an increment is finished and verified, commit the changes, push its branch, and create a PR without waiting for another request. Include plan/issue status updates; do not merge the PR unless separately authorized.
- Standing review instruction (2026-09-23): run Qodo local review (`qodo-review`) with self-contained session context before creating every future PR. Evaluate findings, remediate verified bugs test first, and record the actual result before delivery. Do not silently skip the review or claim completion if authentication, entitlement or approval blocks it; report the exact limitation. This new explicit instruction supersedes the earlier choice not to attempt local review after I00's export rejection. Existing PR findings use `qodo-review-resolver`; local review is the pre-PR path.
- Creating this document does not implement any feature. The initial next increment is I00.

### Start or resume a coding session

1. Read this plan, the current repository instructions, and the execution ledger.
2. Inspect the working tree and recent commits. Preserve work already in progress; do not reset unrelated changes.
3. Select the next ready increment and check its prerequisites. Continue an in-progress increment before starting unrelated work.
4. Inspect the named code seams and existing tests. Confirm current behavior rather than treating historical line numbers or test counts as facts.
5. State the bounded change and its relevant acceptance criteria. Implement in small reviewable changes.
6. Run the narrow checks that prove the changed behavior, then the integration checks required by Section 8.
7. Before creating a PR, run Qodo local review with the implementation rationale and issue/spec references; evaluate its findings and verify any fixes.
8. Record files changed, results, failures/skips, decisions, and the next step. Do not mark a feature complete just because one of its increments is done.

Suggested instruction for a future session:

> Use plans/declarative-governance-implementation-plan.md as the source of truth. Inspect the execution ledger and current repository state, then implement the next ready increment. Preserve the compatibility and ownership guarantees, run the required checks, and update the ledger with evidence and the next step. Do not merge or publish unless separately authorized.

## 2. Outcomes and product decisions

### Capabilities replace maturity levels in the new model

The original bundles were:

- L3: application development governance.
- L4: application governance plus spec-driven development with Gherkin.
- L5: the preceding bundle plus LLM development and an evaluation suite.

Preserve that meaning when translating existing installs. New profiles select capabilities and policy explicitly, without L3–L5 or renamed opaque tiers. Application governance, Gherkin delivery, and LLM development/evaluation can be combined independently subject to genuine dependencies and accepted policy.

A repository can handle a defect, a bounded enhancement, and a substantial feature without changing its profile between requests. Select planning steps and evidence by impact, applicable capabilities, and policy. A small security or public-contract change still requires the relevant controls.

### Brownfield discovery precedes installation

Inspect existing accepted architecture sources, ADRs, agent guidance, manifests, tests, CI, and bounded representative code before proposing files.

Separate:

- Observed practice: what evidence says the repository currently does.
- Proposed decisions: inferred or suggested conventions awaiting a decision.
- Accepted policy and architecture: what governs the work.
- Target architecture: an explicitly scoped intended transition.

Existing code does not approve its own architecture. Unknown or conflicting facts remain visible. Reuse accepted documents rather than requiring copies in GovKit's exemplar layout. Confirm only decisions needed for the selected capability or immediate work; an unresolved dependency blocks its affected work, not all independent work.

Support retain, gradually improve, and deliberately migrate decisions per component/boundary. A transition identifies current and target rules, applicability to new/changed code, existing exceptions, and completion evidence. Editing a target document does not authorize unrelated application refactoring.

Exemplars remain optional design aids. Their installation alone never adopts their architecture decisions. Comprehensive nine-step calibration is not a prerequisite for the new brownfield path; the legacy command remains supported during transition.

### Packs deliver capabilities; skills provide the interaction

A versioned capability pack may contain skills, reference resources, contracts, configuration, validators, and check/gate contributions. A skill-only pack is valid. Skills guide work; independently executable local/CI controls verify it. An agent's assertion is not final enforcement evidence.

Use an agent-neutral pack contract and integrations for Claude Code, Codex, and Copilot. Reuse existing bundled and explicit pinned-source distribution. No new registry, marketplace, hosted service, or replacement coding harness is required.

Install only selected integrations and necessary resources. Reference shared pinned resources where practical; preserve project decisions, overrides, and configuration in the repository. Resources must resolve reproducibly on another developer machine and in CI. Request resolution uses pinned available inputs offline and never silently downloads a pack.

### Maintenance is a distinct read-only assessment

Evaluate four independent dimensions:

1. Release availability and compatibility.
2. Synchronization of actual installed resources with selected/locked versions.
3. Fit between current repository evidence and accepted governance.
4. Health of required CI integrations.

An update can be available without being required. A compatible intentional pin is not a failure. A locally current CLI is not proof of the latest published release. Matching version strings do not prove installed files are present or correct. Current packages can coexist with changed repository needs.

Every maintenance recommendation records evidence, affected resources/controls, uncertainty, policy-derived urgency, prerequisites, customization impact, and the appropriate next action. Record assessment time, repository revision and relevant dirty-tree identity, profile/resolution identity, comparison baseline, and release-source/as-of/lookup status.

Assessment is offline and side-effect free by default. An approved metadata refresh is explicit or explicitly configured and separate from request resolution. It must not upload repository content or posture, install code, alter locks, or accept architecture decisions. Missing/stale release information means unknown freshness.

### Compatibility and authority remain explicit

- Preserve supported legacy workflows through adapters until a documented deprecation boundary.
- Preserve edited contracts, project-local packs, user-authored instructions, and project artifacts; make proposed changes reviewable.
- Do not broaden agent authority or let an editable request label disable required controls.
- Preserve behavioral baseline/commitment checking and optional PDG authority behavior. This refactor must not make PDG mandatory or silently disable it.
- Distinguish configured, applicable, executed, passed, failed, unknown, skipped, not-applicable, and waived states.
- Keep telemetry/reporting local or CI-controlled. Do not collect developer identities, request/prompt or ticket text, source code, secrets, or behavioral telemetry.
- Do not treat a maintained version, installed gate, or compliance score as proof of developer value.

## 3. Scope and issue ownership

| Issue | Responsibility | Main increments |
|---|---|---|
| [#151](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/151) | Existing ADR gate false pass | I00 |
| [#143](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/143) | Pure models, resolution, legacy adapter | I01 |
| [#144](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/144) | Profile, accepted policy, maintenance policy | I02 |
| [#145](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/145) | Pack composition, skills/resources, locking, versions/update candidates | I03, I09 |
| [#178](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/178) | Initial and repeat brownfield discovery | I05 |
| [#179](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/179) | Request normalization and proportional workflow/evidence | I06 |
| [#146](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/146) | Checks, integrated conformance, maintenance assessment | I04, I07, I09 |
| [#149](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/149) | Migration, post-change verification, self-hosting, retirement policy | I08, I12, I13 |
| [#147](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/147) | Pipeline contract, renderers, CI integration evidence | I10 |
| [#148](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/148) | Human/JSON reports, aggregate metrics, adoption evaluation | I11 |
| [#142](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/142) | End-to-end outcomes | All increments and pilot |

Adjacent work:

- [#129](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/129): address Windows path-length installation failures before a Windows pilot; do not make success on Linux evidence of Windows compatibility.
- [#43](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/43): possible Langfuse pack example once I03 is stable. Never copy credentials from issue bodies into code, tests, documentation, or logs; use placeholders and explicit environment inputs.
- [#152](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/152): align evidence authoring with I07's evidence contract. Keep evidence proportional and declare producer independence accurately. Its PDG emission is separate follow-up work, not a prerequisite for ordinary adoption.
- FeaturePeers remains undefined in the supplied requirements. Do not invent its architecture or a dedicated pack.

The release candidate includes the nine epic features and #151. Actual removal of legacy level inputs is a later-release action. Adjacent issues do not silently become mandatory scope except where a selected pilot depends on them.

## 4. Repository boundaries and implementation seams

This repository produces the GovKit installer and payload. It is not currently a GovKit-governed consumer project. Do not run govkit apply against its root or invoke assumed installed govkit-* skills to develop it. Use temporary consumer fixtures until the limited self-hosting increment.

Read [CLAUDE.md](../CLAUDE.md) for the existing architecture. The files below are starting points, not a mandate to put new domain behavior into existing command modules.

| Concern | Existing locations |
|---|---|
| CLI dispatch | cli/govkit.py and cmd_*.py; dedicated doctor.py/calibrate.py registrars |
| Selection and installation | cli/manifest.py, cli/compat.py, cli/cmd_apply.py, cli/install_common.py |
| Ownership and persisted state | cli/marker.py, cli/headers.py, cli/cmd_upgrade.py |
| Repository discovery | cli/detect.py, cli/stack_select.py, cli/skill_context.py |
| Existing setup UX | cli/calibrate.py, cli/setup_review.py |
| Packs and skills | cli/extensions.py, cli/cmd_extension.py, cli/agent_layout.py, extensions/ |
| Validation and evidence | cli/validate.py, cli/doctor.py, cli/evidence.py, cli/approval.py, cli/fixes.py |
| Existing authority checks | cli/baseline_check.py, cli/authority_check.py, cli/contract_gate.py |
| Agent payload | agents/{claude-code,codex,copilot}/ |
| Schemas and gates | governance/schemas/, ci/github/, ci/azure/, ci/README.md |
| Packaging and test configuration | pyproject.toml, .github/workflows/test.yml |

Rules for implementation:

- Keep CLI dispatch thin. New public commands use a dedicated module, register(subparsers), set_defaults(func=...), and registration in govkit._REGISTRARS.
- Command handlers consume shared/domain services; command modules must not depend on one another. The dispatcher is the intentional registration point.
- Keep pure resolution separate from observation, metadata retrieval, rendering, and writes.
- Access bundled paths through the live paths module at use time. Do not capture its constants in imports or module-level aliases. Keep paths.py independent of other CLI modules.
- Update all three agents' equivalent rules/skills together. SKILL.md name/description frontmatter stays byte-identical; body semantics and actual resource loading must agree.
- Update paired GitHub/Azure templates, schemas, starter examples, and referenced documentation together where the behavior changes. Document real provider limitations.
- Preserve packaged asset discovery. extensions/ maps to cli/extension_packs/, not cli/extensions/; changes must work from an installed wheel.
- Existing managed-file overwrite categories are legacy behavior to characterize, not permission to overwrite project-owned content. Hash-based edit protection and explicitly protected customizations remain binding.
- New public command names, module names, and final schema fields are design choices to record during the owning increment. Names in this plan describe responsibilities unless already present in the code or explicitly required by an issue.

## 5. Shared contracts to settle early

I01 supplies typed concepts and interfaces. Implement only the fields needed by real consumers, with versioned serialization. Avoid a speculative framework.

| Concept | Required distinction |
|---|---|
| Repository observation | Evidence, source scope, confidence, observation identity/time; no automatic approval |
| Accepted decision/policy | Authoritative source, scope, conditions, approved exceptions and expiry |
| Project profile | Desired capabilities/integrations and accepted policy; no observed facts or transient release responses |
| Pack descriptor/lock | Versions, source, digests, dependencies/conflicts, skills/resources/check contributions |
| Resolution/installation plan | Effective choices, reasons, unresolved decisions, ownership, proposed operations; no writes |
| Change context/workflow plan | Normalized intent, affected scope, policy identity, selected procedure/artifacts/checks, provenance |
| Finding/evidence result | Stable ID, applicability, execution/result state, source/method/context/limitations, action |
| Gate contract | Applicability, mandatory/advisory status, prerequisites, permissions/configuration, evidence, platform limitations |
| Release metadata/inventory | Running CLI, recorded install, selected versions, actual resources, known releases and compatible candidates |
| Maintenance assessment/action proposal | Independent dimensions, evidence, urgency from policy, next actions and preview inputs, source freshness |

I02 implements the desired profile at .govkit/profile.yaml and generated resolution at .govkit/resolution.json through explicit `govkit profile preview/apply` commands. These metadata files are created only by an authorized profile apply; their existence does not mean capabilities are installed. The legacy marker remains backward compatible. Decide ownership and trust boundaries for workflow/evidence records in I06–I07.

The observation/read adapters and command layer gather inputs; the pure core resolves explicit inputs; authorized operation handlers apply a previewed plan. CI re-evaluates requirements from trusted policy and the actual change rather than accepting the producing agent's workflow label.

## 6. Implementation increments

Default sequence: I00 → I01 → I02 → I03 → I04 → I05 → I06 → I07 → I08 → I09 → I10 → I11 → I12 → I13.

I04's foundation can start after I01. Discovery can begin after I02 and integrate I03's installation contract later. These are dependency freedoms, not a requirement to delegate or run concurrent workers. Do not skip integrated acceptance.

### I00 — Repair the existing ADR gate (#151)

Prerequisites: none.

Deliver:

- Reproduce the real shell/input failure in both provider templates.
- Keep the checker program and changed-path data on separate channels.
- Fail visibly when the diff/base cannot be obtained; use the correct provider PR base and handle monorepo-relative paths.
- Preserve approval semantics and provider parity. Keep this separate from the broad refactor.

Exit evidence:

- A regression executes the actual shell/data plumbing, not only extracted Python with injected stdin.
- A changed ADR is demonstrably seen; an unauthorized Accepted ADR fails.
- Valid approval, no changed ADR after a successful diff, unavailable base/diff, and nested-repo cases are covered.
- Update tests/test_adr_approval_gate_checks.py and ci/README.md as needed; do not claim fixing this transport defect addresses every possible approval-policy limitation.

### I01 — Establish the resolution foundation (#143)

Prerequisites: I00 for the release sequence.

Deliver:

- Record an ADR for the contracts in Section 5 and inward dependency direction.
- Build a pure typed resolver with deterministic serialization, reasons, provenance, conflicts, and unresolved decisions.
- Add legacy manifest/flag adapters, keeping resolve_variant_files() as a compatibility facade.
- Confine level interpretation to compatibility/provenance.

Exit evidence:

- Valid representative legacy agent/type/level/CI/stack configurations preserve artifact selection and behavior.
- Unsupported legacy combinations still fail as before.
- No new CLI behavior, installed layout, marker-format change, or edit-protection regression.
- Resolution performs no printing, exiting, network access, or writes.

### I02 — Add declarative profiles and policy (#144)

Prerequisites: I01.

Deliver:

- Runtime-validated versioned profile and resolution schemas/loaders.
- Independent capabilities, accepted source references, integration settings, permitted workflow rules, required controls, and scoped architecture transitions.
- Explicit unknown/partial repository characteristics; no forced choice of a bundled framework.
- Maintenance policy: approved sources/channels, pins/compatibility, metadata-age limits, and explicit refresh permission.
- A no-write preview and authorized materialization, preserving flag-only behavior and detecting conflicting explicit inputs.

Exit evidence:

- LLM development/evaluation can be expressed without mandatory Gherkin; Gherkin can be expressed without LLM support.
- One profile permits different task workflows.
- Current and target rules can coexist by scope; observations remain separate from accepted decisions.
- Profile/resolution examples validate; accepted documents can be referenced rather than duplicated.

### I03 — Implement capability packs, skills, and lighter installation (#145, core)

Prerequisites: I01–I02.

Deliver:

- Normalize existing pack manifests into explicit capability dependencies/contributions; adapt legacy supported_levels without retaining level inference in new resolution.
- Deterministic graph validation, compatible versions, conflicts/cycles, minimum GovKit version, digests, and local-override handling.
- Skill-only and skill-plus-controls pack examples using the same agent-neutral source.
- Supported-agent integrations and independently executable checks.
- Minimal installation previews with ownership, pinned portable resource references, edit protection, add/remove effects, and idempotency.
- Existing bundled/explicit-source distribution and offline request resolution.

Exit evidence:

- All shipped packs resolve through the applicable compatibility/new paths.
- Missing/cyclic/incompatible inputs fail before writes.
- Only necessary resources/integrations are materialized; exemplars are not automatically authoritative.
- Skills and references work for all three agents and from a clean wheel installation.
- A policy-required control cannot disappear by removing a skill or optional pack.
- Do not close #145 yet: update inventory/candidate acceptance finishes in I09.

### I04 — Establish the check and evidence foundation (#146, foundation)

Prerequisites: I01; integrate I02–I03 as available.

Deliver:

- Check protocol/registry, typed findings, explicit execution/result states, and versioned raw results.
- Adapters around existing doctor/validate/extension/policy checks, with legacy output/exit-code compatibility.
- A concise local rendering and machine-readable output for developing the pilot.
- Dependency injection at external boundaries; checks do not print or exit internally.

Exit evidence:

- A failing check cannot suppress unrelated findings.
- Unknown, missing, unreadable, skipped, and unconfigured required evidence cannot become PASS.
- Evidence records source, scope and limitations; agent-produced assertions do not imply independent verification.
- Existing checks run through adapters with demonstrated failing controls.

### I05 — Deliver focused brownfield setup and rediscovery (#178)

Prerequisites: I02; installation integrates I03.

Deliver:

- Read-only evidence-led inspection of ungoverned or existing GovKit repositories.
- A concise architecture/convention/check summary with confidence and sources.
- Minimal proposed profile/resource changes that reuse accepted repo documents.
- Scoped retain/improve/migrate choices and focused handling of conflicts.
- Repeat discovery that compares relevant evidence to the accepted baseline without restarting full calibration.
- Change signals suitable for maintenance: dependency/framework shifts, moved boundaries, model/tool usage, changed references, tests or CI.

Exit evidence:

- Documented service, sparsely documented repo, unfamiliar MCP server, and monorepo fixtures all produce useful bounded findings.
- A Python MCP fixture does not silently adopt FastAPI as accepted architecture.
- No app refactoring or source-of-truth rewrite occurs during discovery/installation.
- New evidence is not automatically a policy violation or an approved replacement.
- A current-version repo with changed needs can receive focused review/capability recommendations.

### I06 — Deliver workflows selected per request (#179)

Prerequisites: I02–I03; use I04's evidence/check contract.

Deliver:

- Structured request input plus agent-assisted normalization; deterministic resolution begins after normalization.
- Workflows for established-behavior restoration, bounded enhancement/refactor/maintenance, full spec-driven delivery, and deliberate architecture change.
- An inspectable plan with relevant guidance, reused acceptance/NFR references, required checks, unresolved decisions and provenance.
- Minimal evidence/record requirements for eligible small changes; preserve existing defect eligibility.
- Re-evaluation when intent or actual changed scope expands; missing capabilities produce explicit setup actions.
- A short next-step experience that uses skills actually shipped/available.

Exit evidence:

- One unchanged profile supports a defect, small enhancement, refactor and full feature.
- A new bounded behavior does not automatically require five documents.
- Small security/auth/data/public-contract/NFR/ownership/architecture changes trigger applicable controls.
- LLM changes select applicable evaluations independently of Gherkin.
- No automatic tracker writes, pack downloads, policy waivers or repository reconfiguration.
- Reference the current intent durably; CI does not require a live ticket lookup to know what was agreed.

### I07 — Integrate request/repository conformance (#146, core)

Prerequisites: I04–I06.

Deliver:

- Read-only evaluation of repository policy and the resolved request against actual change scope.
- Policy-derived artifact/evaluation requirements, scoped architecture transitions, exceptions and expiry.
- Protection against stale workflow plans, misleading labels, and path filters that suppress required checks.
- Reuse accepted source/evidence references and expose unmeasured dimensions.
- A common local/CI consumption contract and useful local summary.

Exit evidence:

- Same explicit inputs yield equivalent local/CI results for checks available in both environments.
- All pilot workflow combinations have meaningful passing and failing fixtures.
- Mandatory checks remain in scope even when relevant files were not directly edited.
- Existing exceptions and new violations are distinct.
- Missing platform-only approval evidence stays unknown; local tooling does not manufacture approval.
- A pilot can exercise the new path on an ungoverned or isolated-copy existing repo. Legacy consumers wait for I08 before migration.
- Do not close #146 yet: consolidated maintenance completes in I09.

### I08 — Safely migrate existing installations (#149, migration)

Prerequisites: I02–I03, I05, I07.

Deliver:

- Preview translation of actual L3/L4/L5 selections and customizations into explicit capabilities/policy.
- Separate configured controls from demonstrated active enforcement.
- Preserve marker migration, edited contracts, custom packs, agent guidance, workflows and opt-in authority settings.
- Bind the proposed operations to current inputs; detect stale previews before writes.
- Idempotent authorized application, rollback, and post-operation conformance verification.
- Document the difference between updating the CLI package and refreshing repository resources.

Exit evidence:

- Representative legacy installs lose no configured requirement silently.
- Inactive/broken gates are exposed; their copied files do not count as parity.
- Customized content survives and unresolved reconciliations remain visible.
- A stale preview is rejected/refreshed before writes.
- Post-change verification does not mark a finding resolved just because a version marker changed.
- Integrate canonical maintenance actions from I09 when available; #149 remains open for I12–I13.

### I09 — Add version intelligence and maintenance assessment (#145 + #146)

Prerequisites: I02–I03, I05, I07; feed I08's operations contract.

Deliver:

- Inventory running CLI, recorded install, locked/resolved packs, and actual materialized resources/digests.
- Approved release-metadata providers using existing distribution channels; offline/cached inputs first, explicit read-only refresh second.
- Separate newest known release from compatible policy-allowed candidates; respect pins, channels, ordering and dependency/runtime requirements.
- Source/as-of/retrieval status, explicit metadata age and unknown freshness.
- One canonical read-only maintenance assessment covering all four dimensions in Section 2.
- Evidence-backed recommendations and operation previews for CLI/pack upgrades, resource reconciliation, capability setup, CI repair and scoped architecture/policy review.

Exit evidence:

- Cover compatible updates, newer incompatible releases, intentional pins, altered/missing resources at matching versions, current packages with new repo needs, and unavailable/stale/failed lookups.
- Assessment never installs code, updates locks or policy, or uploads repo content.
- Explicit metadata cache refresh is distinct from project mutation.
- Partial assessments remain useful when a provider is unavailable; no missing input is silently converted to healthy/current.
- Confirm every acceptance item for #145 and #146, including earlier increments, before marking either feature complete.

### I10 — Integrate CI contracts and providers (#147)

Prerequisites: I02–I03, I06–I07; maintenance integration uses I09.

Deliver:

- Shared GateSpec/catalog and compatibility adapter instead of duplicated agent-owned CI selection.
- GitHub/Azure renderers with pinned versions and preview/check/generate operations.
- Stable pipelines that select request-specific checks at execution while retaining mandatory repository controls.
- Minimal reviewable integration with existing pipelines, drift detection, and provider limitation documentation.
- Evidence describing configured, executed, and enforced controls separately; contribute facts to maintenance.
- Optional explicitly configured metadata refresh and assessment-artifact publication with existing privacy guarantees.

Exit evidence:

- Provider-neutral gate IDs/policy match; actual platform differences are stated and covered.
- An editable plan or untrusted changed workflow/policy cannot silently authorize itself. Document trusted policy sources and external branch/reviewer requirements.
- Local and CI results agree for shared explicit inputs.
- Missing provider/runtime facts remain unknown; static YAML presence is not execution evidence.
- Workflow generation is deterministic and does not overwrite existing pipelines by default.
- A candidate update preview identifies affected gates, permissions/configuration, and follow-up validation.

### I11 — Deliver posture and maintenance reporting (#148)

Prerequisites: I07 for core results, I09 for maintenance, I10 for complete pipeline evidence.

Deliver:

- Human-readable summaries and versioned deterministic JSON using canonical findings, not another assessment engine.
- Capability, version, control/evaluation, exception, architecture-transition and CI facts.
- Actionable maintenance recommendations with metadata freshness, compatibility/pin constraints, customization impact, and preview references.
- Aggregate metrics with defined denominators and overlapping categories: assessed repos, compatible updates, required upgrades, resource drift, governance reviews, CI repairs, assessment age and unknown metadata.
- Local/CI-controlled export without automatic transmission or developer tracking.
- A separate voluntary team-level adoption pilot protocol.

Exit evidence:

- Human and JSON outputs represent the same findings/actions.
- Missing assessments, unknown results, stale metadata, and unexecuted controls cannot inflate healthy/compliant counts.
- An intentional pin can coexist with an available update and compliant policy.
- Export only allowed descriptors/references, not raw source, prompts, tickets or sensitive evidence.
- Demonstrate aggregation without a central service.
- Collect setup effort separately from recurring overhead; installed/conformant is not a productivity metric.

### I12 — Demonstrate limited GovKit self-hosting (#149, self-hosting)

Prerequisites: I08, I10–I11.

Deliver:

- A minimal explicit profile suited to the GovKit source repository.
- Real conformance execution, pipeline-contract checks and posture output.
- No blanket installation of all consumer-facing architecture docs/rules.

Exit evidence:

- GovKit resolves and validates its own chosen model.
- Evidence identifies checks actually executed and remaining unknowns.
- Preserve the distinction between this repository's installer architecture and consumer payload examples.
- At this increment, update the applicable bootstrap guidance to reflect actual self-hosting; do not claim it earlier.

### I13 — Pilot feedback, release hardening, and deprecation policy

Prerequisites: all previous increments for full release-candidate completion; pilot observations start at I07.

Deliver:

- Address verified pilot defects and workflow burdens with focused fixes.
- Complete documentation, examples, migration/rollback guidance, and installed-skill inventory checks.
- Verify clean built-wheel installs and supported agent/provider/stack combinations.
- Set an explicit compatibility warning period and release boundary for legacy level inputs; make new onboarding capability-based.
- Reconcile all remaining Appendix A acceptance items and issue completion evidence.

Exit evidence:

- Release checklist in Section 10 passes with limitations stated.
- No outstanding required check is hidden by a skip or optimistic status.
- No feature is declared complete solely because time/estimate is exhausted.

Actual deletion of legacy flags/manifests belongs to a later release after the documented boundary and migration evidence. It is not required for this initial release candidate and must not be rushed to fit the estimate.

## 7. Pilot and fixture plan

Use isolated fixture directories/copies for installation tests. Do not modify another team's repository or connect to live services merely to run a fixture. Real pilot participants choose and authorize their own changes.

| Fixture/scenario | What it must establish |
|---|---|
| Documented existing API/service | Reuse accepted documents, tests and CI; minimal setup changes |
| Sparse/unfamiliar Python MCP server | Preserve unknowns; avoid unrelated framework defaults |
| Monorepo with conflicting conventions | Component scoping, source conflicts, no cross-service contamination |
| Legacy L3/L4/L5, including customized content | Translation preserves requirements, overrides, ownership and authority settings |
| One repo with defect/enhancement/refactor/full feature | Stable profile, different applicable workflows |
| LLM evaluation without Gherkin; Gherkin without LLM | Independent supported capability combinations |
| Tiny auth/data/public-contract change | Impact-based escalation independent of line count/label |
| Gradual architecture transition | Current/target scope, exceptions, expiry and new-violation detection |
| Skill-only and skill-plus-controls packs | Portable resources and checks independent of agent sessions |
| Release metadata/resource drift cases | Honest compatibility/freshness results and distinct next actions |
| Both CI providers | Real passing and failing gate behavior; provider differences explicit |
| Actual built wheel in a clean environment | Bundle paths and skill/resource availability work outside editable checkout |

First useful pilot exit:

- A conventional existing service and an MCP/LLM-oriented repo can try the selected new path.
- A small enhancement uses proportionate artifacts/evidence.
- Applicable LLM evaluations and mandatory controls still execute.
- No unsupported governance decision is silently accepted.
- Legacy migration is used only after I08 is verified.

Record aggregate setup effort, recurring workflow overhead, review rework, useful findings, and repeat-use preference with participants' consent. Compare similar work and repository familiarity. Do not instrument individual productivity or use sprint completion percentages as the success criterion.

Re-estimate after five focused working days using completed increments and pilot evidence. Do not schedule an automatic reminder or collect telemetry as a side effect of this plan.

## 8. Verification and evidence

### Meaningful tests

- Protect behavior and invariants, not coverage percentages or implementation wording.
- Tests set up explicit isolated state and control environmental/network dependencies.
- Mock external dependencies, not the production resolver/check being evaluated.
- Every test has programmatic assertions. For controls, include an input known to fail; a green exit alone does not prove the control examined its input.
- Prefer narrow deterministic tests when they provide equal confidence. Keep necessary shell/packaging/provider integration tests where narrower tests would miss the defect.
- Assert no target writes for discovery, preview, resolution and assessment, except a separately requested metadata-cache operation.
- Cover retry/re-run idempotency and protected-file preservation for write paths.

### Repository commands

Use the repository's Python environment with its test dependencies. The existing development extra is [test], not [dev]. The following are established commands; select targets appropriate to the increment.

```bash
python -m pip install -e ".[test]"
./run_tests
./full_test
python -m pytest -k parity
python -m pytest tests/test_agent_skills.py tests/test_govkit.py
python -m pytest tests/test_schemas.py tests/test_fixtures.py
python -m pytest tests/test_adr_approval_gate_checks.py
```

Do not pass -m to run_tests/full_test; the wrappers own their marker expressions. Activate the intended environment so their python command resolves correctly. Use direct pytest for custom marker selection.

The Ruff configuration has automatic fixes enabled. For inspection, use ruff check --no-fix scoped to changed Python files; format only changed files when needed. Never run a repository-wide rewriting lint command as incidental cleanup.

Validation scope:

- Each increment: relevant focused tests, then the fast suite for affected Python/payload behavior.
- Agent payload changes: parity plus affected skill/manifest tests.
- Schema changes: runtime rejection cases and every associated starter/example.
- CI changes: both provider variants and execution of real data plumbing, plus conformance contract tests.
- Packaging/resources changes: build a real wheel and run the relevant clean-environment smoke cases; editable-install results are insufficient.
- Milestone/release integration: full suite and the required toolchain/wheel CI jobs from .github/workflows/test.yml. Report local missing tools/skips honestly and use actual CI evidence before claiming full coverage.
- Windows pilot: resolve/verify #129 with a representative deep-path install.

Do not run the entire suite repeatedly after no relevant change. Conversely, do not use a smaller passing subset to claim unrun requirements passed.

### Evidence to record

For each increment/acceptance item, record:

- Commit or current worktree identity and relevant files.
- Commands/cases executed and their results.
- Demonstrated failure cases for controls.
- Missing dependencies, skips, unmeasured dimensions and remaining uncertainty.
- Applicable rule/issue criterion and where the evidence establishes it.
- PR/run/artifact links only when they actually exist.

A proposed document, passing mocked checker, updated marker, or installed workflow is not enough to establish runtime enforcement.

## 9. Estimates and checkpoints

Planning assumption: one experienced maintainer directing a coding agent, same-day decisions/reviews, existing distribution channels, and access to representative repositories.

| Work group | Planning allowance |
|---|---|
| Enforcement repair and foundation | 1–2 working days |
| Profiles and capability packs | 2–3 working days |
| Brownfield setup and request workflows | 2–3 working days |
| Conformance, maintenance and migration | 2–3 working days |
| CI, reporting, self-hosting and release verification | 2–4 working days |

Budget 10–15 focused working days for a release candidate, with a useful bounded pilot in approximately 5–8 days. Allow approximately 3–5 calendar weeks to incorporate team feedback and rollout. These are uncertain planning ranges, not measured agent throughput or deadlines. The pilot can precede every maintenance/reporting integration; required controls for its scope cannot.

Review the estimate after five working days. Use actual discovery difficulty, compatibility failures, review turnaround, and completed acceptance evidence. Keep unresolved work visible rather than compressing verification to preserve the forecast. Later physical removal of legacy level inputs is outside the initial release-candidate estimate.

## 10. Release-candidate definition of done

- [ ] I00–I13 exit criteria are supported by evidence.
- [ ] All included feature acceptance criteria in Appendix A are reconciled and satisfied; any agreed scope change is recorded in this plan.
- [ ] Legacy compatibility, project-owned content and local customizations are preserved.
- [ ] Independent capability/workflow combinations work across supported agent integrations.
- [ ] Brownfield setup is useful without mandatory full exemplar customization or comprehensive calibration.
- [ ] Controls execute independently; actual-diff checks prevent label/plan-based bypasses.
- [ ] Maintenance distinguishes release updates, resource refreshes, governance adaptation and CI repair with honest freshness/unknowns.
- [ ] Generated integrations and reports preserve provider limits, evidence provenance, and privacy.
- [ ] Clean wheel and required CI/toolchain validation pass; remaining limitations are explicit.
- [ ] Pilot findings, migration/rollback documentation and deprecation boundaries are recorded.
- [ ] User-facing instructions reference real shipped commands/skills; no phantom skill paths.
- [ ] A release candidate is reviewable. Merging, publishing and changing other repositories remain subject to the authorization for that task.

## 11. Execution ledger and handoff

Allowed statuses: not started, in progress, blocked, complete. Complete requires evidence; blocked requires a concrete unresolved dependency and does not imply unrelated work must stop.

| Increment | Status | Evidence / commit / PR | Next action or blocker |
|---|---|---|---|
| I00 | complete | Merged as bfa4f76 through [PR #180](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/180); 16 failing shell regressions before fix → 74 ADR tests passing; fast suite 3496 passed, 2 skipped; hosted Tests run succeeded | #151 closed; I00 delivery complete |
| I01 | complete | Merged as 941fe34 through [PR #181](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/181); 258 frozen selections; 284 focused tests; fast suite 3780 passed, 2 skipped; clean-wheel smoke and hosted Tests run passed; see I01 record | #143 closed; I01 delivery complete |
| I02 | complete | Merged as b7d2f2f; implementation 27871fa; [PR #182](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/182); 51 focused tests; fast suite 3831 passed, 2 skipped; clean-wheel profile/legacy smoke plus 258 frozen selections; new CI step executed locally; see I02 record | #144 closed; hosted Tests run passed |
| I03 | complete | Merged as b379a5a through [PR #183](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/183); 53 pack tests; 3884 fast-suite passes; 21 wheel installs; hosted Tests passed for 9ed7f6a | #145 remains open for I09 |
| I04 | complete | [PR #184](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/184), initial implementation 78b1069; five review bugs remediated with 23 additional regressions; 3943 fast-suite passes; runtime-only wheel smoke passed | Merged 5426abe; final-head Tests run 35920010148 passed; #146 stays open for I07/I09 |
| I05 | complete | [PR #185](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/185), implementation 09a1de3; three Qodo bugs remediated with 13 regressions; 3995 fast-suite passes; runtime-only wheel smoke passed | Merged 21ccef2; final-head Tests run 35926710002 passed; #178 remains open for I07 |
| I06 | complete | [PR #186](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/186), merged b938a3b; three review bugs fixed in 9325749; 4,036 fast tests and clean-wheel smoke passed | Final-head Tests run 35929565253 passed; #179 remains open for I07 |
| I07 | delivered; awaiting merge | [PR #187](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/187), implementation 9e40330; 39 new tests, 4,075 fast-suite passes, runtime-only wheel smoke passed | Review/merge; Qodo local review remains blocked by recorded repo_not_connected |
| I08 | not started | — | Wait for I02–I03, I05, I07 |
| I09 | not started | — | Wait for I02–I03, I05, I07 |
| I10 | not started | — | Wait for core prerequisites; integrate I09 |
| I11 | not started | — | Core reporting after I07; full report after I09–I10 |
| I12 | not started | — | Wait for I08, I10–I11 |
| I13 | not started | — | Pilot observations may begin at I07 |

Current handoff:

- Completed: I00–I06 merged. PR #186 merged as `b938a3b515e44cc73acb9dbe4b6bbe530cd824a8`; final-head [Tests run 35929565253](https://github.com/Accelerated-Innovation/governed-ai-delivery/actions/runs/35929565253) passed for `9325749`. Individual logs/artifacts were not re-audited; no Qodo clean verdict is inferred from the merge.
- Current increment: I07 (#146 core) is delivered in [PR #187](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/187), implementation `9e40330`, on `feat/146-request-conformance`. 39 new tests; **4,075 fast-suite passes**, 2 existing skips, 150 e2e tests deselected. Runtime-only wheel smoke passes all seven actual-change pilots, plus existing request/check smokes. This source repo has no consumer installation.
- Next action: review PR #187. After its merge, confirm/synchronize/clean up and begin I08 safe legacy migration test first. Preserve `.venv`; the current known I07 temporary artifacts are `/private/tmp/govkit-i07-dist`, `govkit-i07-wheel-venv`, `govkit-i07-examples.py` and `govkit-i07-schemas.py`.
- Review limitation: the user reported Qodo reconnected on 2026-09-24. Fresh verification confirmed CLI 1.0.3 authentication and 49 managed tools, but repository search returned no matches and a direct public-repository read failed `MT-WORKSPACE-NO-REPOS` / `WORKSPACE_HAS_NO_AUTHORIZED_REPOS` (HTTP 403). The authenticated CLI workspace still has no authorized repositories. Resolve its GitHub installation/workspace association before another local-review attempt. No I07 local review or clean Qodo verdict is claimed; existing PR work uses the structured review resolver.
- Issue tracking: #151/#143/#144 are closed. I07 demonstrates the remaining #178/#179 criteria; keep both open until the integration PR merges. The first nine #146 conformance criteria are locally demonstrated; its maintenance criteria and closure remain I09. #145 awaits I09; #142 remains open.
- Open product input: FeaturePeers definition, representative team repos, pilot participants and the actual legacy-retirement release boundary remain later decisions; none blocks I07.

Use this record after each session:

```text
Date / agent or task:
Increment and status:
Changes and affected paths:
Acceptance items demonstrated:
Checks run, results, and evidence references:
Skips / unknowns / limitations:
Decisions made and rationale:
Remaining work / blocking decision:
Next ready action:
```

### I00 execution record — 2026-09-23

- **Initial verification identity:** completed locally on baseline af819455cb19ebc01ce6bd56b6d6490e128bc1a5. The implementation session ended without a commit, pull request, deployment, or hosted CI run; the user subsequently requested a commit and PR.
- **Worktree fingerprint:** SHA-256 of `git diff --binary -- ci/github/adr-approval-gate.yml ci/azure/adr-approval-gate.yml ci/README.md tests/test_adr_approval_gate_checks.py` is `f97c1209ca6ded59b5cf147a1b6dcd32630153560f63afbccdafc0321c2243f1`. The plan itself is outside that implementation fingerprint.
- **Test-first red:** before editing either template, `.venv/bin/python -m pytest tests/test_adr_approval_gate_checks.py -q` passed the existing 54 tests. Added 20 real-shell regression cases; `.venv/bin/python -m pytest tests/test_adr_approval_gate_checks.py -k TestShellTransport -q --tb=short` produced **16 failed, 4 passed, 54 deselected**. Changed ADR cases incorrectly printed "No ADR changed"; missing base and no-merge-base cases incorrectly returned success.
- **Implementation:** separate the program (stdin here-document) from changed paths (`CHANGED_ADR_PATHS` environment input); require a successful diff before invoking Python; fail explicitly on unavailable base/diff; use `--relative` for service-root execution. GitHub uses the event base SHA. Azure fetches the exact `System.PullRequest.TargetBranch` ref with the existing checkout credentials. Preserve byte-identical Python checkers and existing approval rules. Document provider setup and limitations in ci/README.md.
- **Acceptance demonstrated:** actual template Bash executes real Git and Python, with known unauthorized Accepted ADRs failing and printing the ADR path; valid current-head approval passes and prints the path; successful empty diffs pass; missing/unavailable bases and missing merge bases fail; non-main PR targets work without origin/main; nested service paths resolve against service-local policy and sibling services are excluded. Both providers execute all 20 shell cases against isolated local repositories/remotes without network access.
- **Green:** `.venv/bin/python -m pytest tests/test_adr_approval_gate_checks.py -q --tb=short` → **74 passed**. `source .venv/bin/activate && ./run_tests -q` → **3496 passed, 2 skipped, 150 deselected**. The two skips are existing non-Copilot applyTo cases in tests/test_behavior_contract_rule.py; deselected tests are the e2e tier. `.venv/bin/python -m ruff check --no-fix tests/test_adr_approval_gate_checks.py` and `git diff --check` passed.
- **Pre-PR review:** reviewed the local diff and confirmed the implementation fingerprint still matches the tested worktree. Qodo review submission was rejected by automatic approval review because exporting the private diff/context to that external service was not authorized; no Qodo findings or clean-review claim exists. Only plan delivery metadata changed after the tests, so the passing implementation checks were not rerun.
- **Delivery:** at the user's request, committed the repair and plan as `1b781bf9794329640ed0f0fea7989bf9037b55ba`, pushed `fix/151-adr-gate-input`, and opened [PR #180](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/180) against main with `Fixes #151`. PR #180 merged on 2026-09-23 as `bfa4f76ae2179b9f14d17f1ee2d109bf4946666f`, closing #151. Its [Tests workflow run](https://github.com/Accelerated-Innovation/governed-ai-delivery/actions/runs/35904543702) completed successfully for PR head `5ccd290a915bdd4245ae4c13c08ee91c552d6bd9`; individual job logs/artifacts were not re-audited. Local main also includes the independently merged dependency update #177 (`fa6b982`).
- **Standards applied:** Appendix B's ERROR 2297577 (isolated explicit fixture state), ERROR 2297569 (real production shell/checker; only provider metadata/review input substituted), ERROR 2297588 (explicit status/path assertions), and WARNING 2287169 (paired templates plus README). The existing checker-parity test passes. Reused the plan's recorded Qodo standards; no fresh rule-search result is claimed.
- **Limits:** the reported test counts are local shell integration results, not live GitHub/Azure review API or branch-policy execution. The full e2e/toolchain tier, clean-wheel smoke, and Windows pilot were not run locally; hosted workflow status is recorded separately above. Azure compares against the target tip fetched at execution, unlike GitHub's event base snapshot. This does not address the separate limitations around unchanged/Proposed ADRs, approval-policy trust, or provider enforcement configuration.
- **Next:** begin I01's characterization tests and ADR from the merged main baseline. Leave all broader feature acceptance items unchecked; the merge-status update to this plan can accompany the next implementation increment.

### I01 execution record — 2026-09-23

- **Initial verification identity:** implemented and verified locally on `feat/143-resolution-foundation`, based on `bfa4f76ae2179b9f14d17f1ee2d109bf4946666f`. The implementation session ended with uncommitted changes; the user subsequently authorized a commit and PR. The I00 merge-status edit present at session start is preserved.
- **Implementation:** `cli/resolution_models.py` defines explicit repository/request inputs, requirements with reasons/source authority, integration selections, policy/contract/transition references, unresolved decisions, and versioned installation/workflow plans. `cli/resolution.py` checks explicit dependencies, conflicts, missing provenance and unaccepted requirement sources without I/O; request requirements cannot remove repository controls or dependencies. Plans snapshot mutable input metadata and serialize deterministically; workflow results bind to an installation-plan identity. `cli/legacy_resolution.py` owns the existing level/merge/replace/dispatch interpretation and lossless legacy conversion. `cli/manifest.py` retains loading/prompts and its existing public selection facade. [ADR 0001](decisions/0001-resolution-boundaries.md) and CLAUDE.md explain the boundary and later consumers.
- **Test-first characterization:** before production edits, recorded ordered selection fingerprints for **258** supported combinations across all three agents, both providers, all six project types, the three supported levels, and applicable stacks. `tests/test_legacy_resolution.py` passed **260 tests**, including readable base-duplicate/attribute and option-order cases. Existing unsupported data/L5 and UI/explicit-stack cases passed **4 tests** before the refactor.
- **Test-first red:** `tests/test_resolution.py` first failed collection with `ModuleNotFoundError` for the absent adapter/core modules. After implementing the initial contracts, an additional behavioral pass produced **5 failed, 18 passed**: requests lost existing dependencies or failed to add constraints, observed/proposed requirements appeared ready, and unresolved plans converted to legacy lists. Fixed those failures. A final diagnostic-identity regression produced **1 failed, 23 deselected**, demonstrating that delimiter-containing identifiers could collapse distinct findings; hashing the canonical affected-subject array fixed the collision.
- **Final green:** `.venv/bin/python -m pytest tests/test_resolution.py tests/test_legacy_resolution.py -q` → **284 passed** (24 core tests and 260 characterization tests). `source .venv/bin/activate && ./run_tests -q` → **3780 passed, 2 skipped, 150 deselected**. Skips are the existing non-Copilot applyTo cases; the deselected tier is e2e. An expanded compatibility run covering test_govkit, test_maturity_model, headers, markers, marker authority, and stack upgrades passed **689 tests** before the final diagnostic-identity refinement. Scoped `ruff check --no-fix` and `git diff --check` passed; only touched/new Python files were formatted.
- **Built-wheel evidence:** built `govkit-0.21.1-py3-none-any.whl` with an isolated hatchling 1.32.4 build environment, installed it with PyYAML 6.0.3 into a clean temporary venv, and executed with isolated Python from outside the checkout. Verified all four changed/new module bytes match the final source and bundle paths resolve inside the installed wheel. **258** frozen selections and associated installation/request plans passed; the distinct-decision-ID regression passed. Fresh apply/upgrade fixtures for Codex API L4/GitHub/python-fastapi, Copilot data L4/Azure/databricks-lakehouse, and Claude Code API L5/GitHub/dotnet-aspnet preserved marker options, edited governed contracts, and user-owned files.
- **Acceptance mapping:** legacy ABI, order and metadata → frozen matrix/synthetic cases plus existing install tests; level-free inputs and independent capabilities → core tests; repository/request separation and policy retention → request tests; provenance, authority, deterministic serialization and structured conflicts → core tests; no effects/inward dependencies → forbidden-I/O test and import-boundary assertions; architecture/trust/migration seams → ADR 0001. All eight #143 acceptance items are demonstrated and integrated through PR #181; #143 is closed.
- **Standards applied:** Appendix B's typed-domain/shared-helper rules shaped the core and compatibility boundary; 2287157/2287159 preserve live path access and inward imports; 2287173/2287166 preserve category semantics and user customizations; ERROR 2297577/2297569/2297588 are supported by isolated explicit fixtures, real resolver execution with only I/O dependencies guarded, and programmatic assertions. Reused the recorded Qodo standards. No external Qodo review submission was retried after the prior authorization rejection.
- **Worktree fingerprint:** SHA-256 `0775ec82addb0f3f62cedc753523ac3b8e0441a0e0135394d6011492aa1bdfa6`, computed over compact sorted-key JSON mapping each of the nine non-plan delivery paths to its file-content SHA-256. The execution plan is excluded to avoid a self-referential fingerprint.
- **Pre-PR verification:** confirmed the final implementation fingerprint matches the tested worktree, the ten delivery paths contain no unrelated changes, whitespace checks pass, and remote main still points to bfa4f76. Only plan delivery metadata changed after validation, so the implementation checks were not repeated. No external Qodo submission was retried.
- **Delivery:** at the user's request, committed the implementation and plan as `dd70fb1082b16f3c60fbd9ca2cc2ba67a5a4ca38`, pushed `feat/143-resolution-foundation`, and opened [PR #181](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/181) against main with `Fixes #143`. The plan-link follow-up was `7cde1faf426cfcf66d3b2911a6235dc32c5d83d4`. PR #181 merged on 2026-09-23 as `941fe34ae806edfe8de34d0ec683e87b3cec4e15`, closing #143. Its [Tests workflow run](https://github.com/Accelerated-Innovation/governed-ai-delivery/actions/runs/35908334514) completed successfully for PR head `7cde1fa`; individual job logs/artifacts were not re-audited. Local main was synchronized and the local feature branch removed after verifying its full tree matched the merge.
- **Limits:** local validation used Python 3.12; the full e2e/toolchain matrix, Python 3.11 CI, and Windows were not run locally. The hosted Tests workflow passed, but its individual jobs/artifacts were not re-audited. Wheel smoke is scoped to the cases above. Source authority is an explicit caller assertion, not authenticated approval. The foundation does not implement public profile schemas/loaders, pack/version graph resolution, discovery, impact-based workflow selection, executable checks, policy-exception enforcement, or authorized write plans; those remain in their owning increments. `ready` is not enforcement evidence or write authority.
- **Next:** start I02 with failing profile/schema and preview tests. The new internal module/model names and capability identifiers are documented in ADR 0001; do not expose a new command or on-disk format without I02 validation and compatibility evidence.

### I02 execution record — 2026-09-23

- **Initial verification identity:** implemented and verified locally on `feat/144-declarative-profiles`, based on `941fe34ae806edfe8de34d0ec683e87b3cec4e15`. The implementation session ended with uncommitted changes; the user subsequently authorized a commit and PR. The I01 merge-status plan update is included.
- **Public contract:** [ADR 0002](decisions/0002-profile-materialization.md) records `govkit profile preview/apply`, strict version-1 profile/resolution schemas, and metadata-only materialization. `profiles.py` owns typed loading, workflow/maintenance declarations and replayable resolution; `profile_store.py` owns fixed-path previews, stale-input/ownership checks and writes; `cmd_profile.py` owns CLI dispatch/reporting. The I01 core and legacy adapter remain unchanged. `jsonschema>=4,<5` is now a required runtime dependency; schemas/examples use the existing governance wheel mapping and live `paths.GOVERNANCE_DIR`.
- **Authority and policy:** profile sources explicitly assert accepted authority. Observations/proposals remain separate generated context; references are preserved without fetching/copying documents. Independent capability combinations, unknown/custom context, workflow permissions, required controls, scoped retain/improve/migrate transitions and accepted exceptions are represented. Missing required context/capabilities and conflicting declarations are unresolved. Records replay from embedded inputs and carry a canonical profile digest; consistency does not authenticate approval or prove installed/executed controls.
- **Maintenance boundary:** sources/channels, intentional pins, compatibility and age constraints, and refresh permission are runtime-validated and preserved. Refresh defaults off and never executes in I02. Every record reports `not-queried`; newer/stale/unavailable cache scenarios leave freshness unknown and do not create a violation or touch a lock. This demonstrates profile-policy behavior, not version ordering, age calculation or the I09 maintenance assessment engine.
- **Test-first red:** added `tests/test_profiles.py`, `tests/test_profile_store.py`, and `tests/test_cmd_profile.py` before production modules; the first run produced **3 collection errors** for missing profile/store modules. The first implemented run had **38 passed, 3 failed**: missing worked examples and two case-sensitive test-message expectations (stale previews were already refused). After examples/expectation corrections, **41 passed**. A follow-up red run produced **45 passed, 3 failed**: credential-bearing source URLs were accepted, contradictory same-scope transitions appeared ready, and paired resolution examples were absent. Fixed the two behavioral gaps and generated replayable examples, then added cache/lock preservation coverage.
- **Final green:** focused profile/store/CLI tests → **51 passed**. `source .venv/bin/activate && ./run_tests -q` → **3831 passed, 2 skipped, 150 deselected** in 28.15 seconds. The skips are the existing non-Copilot applyTo cases; the excluded tier is e2e. An expanded core/legacy/install/marker/upgrade/header run passed **738 tests** before the final three cache scenarios were added. Scoped `ruff check --no-fix` and `git diff --check` passed; only new Python files were formatted.
- **Write-path evidence:** actual CLI dispatch and storage tests establish no writes during preview, version/authority/field rejection, explicit flag conflict errors, protected user/edited metadata, no marker changes, unknown-context behavior, rejection of stale sources/destinations and symlinks, deterministic no-op apply with stable mtimes, and rollback after injected second-write failure. Only the two profile metadata paths are materialized; no capability resources or lock are installed/changed.
- **Built-wheel evidence:** built the final `govkit-0.21.1-py3-none-any.whl` and installed it with runtime dependencies only into a clean temporary venv (jsonschema 4.26.0 and PyYAML 6.0.3). Isolated Python executed outside the checkout; module and schema/example bytes matched the source. All three bundled profiles and paired records passed real CLI preview/apply/replay/idempotency/conflict checks. Actual L4 API/GitHub/python-fastapi installs for Claude Code, Codex and Copilot passed and retained their real markers when profile metadata was applied. **258** frozen legacy selections passed through the installed wheel. The first ad hoc legacy smoke assertion incorrectly looked for options.level; it was corrected to the actual top-level marker level before the final successful run; production marker code was unchanged.
- **CI:** added a profile step to the existing `.github/workflows/test.yml` wheel job. Extracted and executed that exact shell/Python step locally with only the temporary interpreter path substituted: **3 profile examples passed**. This is installer-build CI, not a consumer GitHub/Azure gate-template change. No hosted execution of the new step is claimed.
- **Acceptance mapping:** independent combinations/unknowns/authority/transitions → runtime profile and example tests; stable workflow permissions and mandatory controls → typed rules plus real I01 request resolution; no-write preview and materialization → storage/CLI tests; deterministic valid profile/records → runtime schemas, all six examples, replay and tamper cases; compatibility → expanded/fast suites and real wheel installs; offline maintenance → source/channel/constraint rejection, network guard and three ignored-cache/unchanged-lock scenarios. All eleven #144 items are checked for this configuration scope and integrated through PR #182; #144 is closed.
- **Standards applied:** reused Appendix B's rules retrieved through Qodo. Runtime validators/shared services and typed inputs implement the domain/shared-helper rules; 2287160/2287161/2287159 keep command registration and inward dependencies; 2287157/2287176 preserve live bundled paths and real wheel verification; 2287166/2287173 protect project files and existing marker semantics; 2287168 is supported by runtime validation/replay of every example. ERROR 2297577/2297569/2297588 are supported by isolated explicit fixtures, real production resolver/CLI execution with only I/O failure seams substituted, and programmatic assertions. No external Qodo review submission was retried.
- **Worktree fingerprint:** SHA-256 `2a4036ffc6008ae472e05112aa4d45342054e51c7cac663ed5979c78d022ac01`, computed over compact sorted-key JSON mapping each of the 22 non-plan changed/new delivery paths to its file-content SHA-256. The execution plan is excluded to avoid self-reference.
- **Pre-PR verification:** confirmed the implementation fingerprint matches the tested worktree, the 23 delivery paths contain no unrelated changes, whitespace checks pass, and remote main still points to 941fe34. Only plan delivery metadata changed after validation, so the passing implementation checks were not repeated. No external Qodo submission was retried.
- **Delivery:** at the user's request, committed the implementation and plan as `27871fa7cd77b6d3db5b3061f2f9e38177493d22`, pushed `feat/144-declarative-profiles`, and opened [PR #182](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/182) against main with `Fixes #144`. The plan-link follow-up was f88c595. PR #182 merged on 2026-09-23 as `b7d2f2fb4d21929e1f3b254804c8f3243f8ed244`, closing #144. Its [Tests workflow run](https://github.com/Accelerated-Innovation/governed-ai-delivery/actions/runs/35911892301) completed successfully for PR head f88c595; individual job logs/artifacts were not re-audited.
- **Limits:** local Python 3.12 only; full e2e/toolchain, Python 3.11 and Windows were not run locally; the hosted I02 Tests workflow passed, but individual job logs/artifacts were not re-audited. Accepted references remain caller assertions. Workflow conditions and maintenance/version constraints are declarations for later consumers, not executed routing/assessment. Full scope-overlap/exception enforcement, pack availability/installation, migration and conformance remain in their owning increments. The two-file writer offers per-file atomic replacement and caught-failure rollback, not a concurrent-writer transaction or crash-recovery journal.
- **Next:** start I03's pack descriptor/composition/locking tests. Treat the new schemas and commands as public contracts; preserve runtime rejection, example parity/replay and packaged-resource verification when extending them.

### I03 execution record — 2026-09-23

- **Identity and cleanup:** implemented on `feat/145-capability-packs`, based on merged I02 `b7d2f2fb4d21929e1f3b254804c8f3243f8ed244`. Confirmed PR #182 merged, #144 closed, remote branch deleted and its Tests workflow successful. Fetched/pruned, fast-forwarded local main, verified the former feature tree matched main, and deleted the merged local branch before creating this branch. The implementation session ended with uncommitted changes; the user subsequently requested commit/PR delivery and established that as the standing instruction for future completed increments.
- **Test-first red:** the pre-change extension baseline passed **160 tests**. Added composition/storage tests before production modules; the first run produced **2 collection errors** for absent pack modules. The first graph/profile run reached **49 passed, 1 failed** for the not-yet-added bundled examples. Added the public CLI tests before registration; all **3 failed** because `pack` did not exist. Follow-up failing regressions exposed the running-version check missing during offline use, dependency edges missing from the serialized lock, and a custom pack named `profile` colliding with the synthetic graph root. Each was fixed after reproducing the failure. CLI validation also identified stale local editable package metadata (0.20.0); reinstalling this checkout restored its actual 0.21.1 metadata without changing production version behavior.
- **Contract and design:** [ADR 0003](decisions/0003-capability-pack-installation.md) documents the v1 manifest block, portable lock, neutral native skill installation and independent Python controls. Existing manifests normalize at the loading boundary; level applicability remains legacy provenance. The pure graph validates explicit dependency reasons, versions, minimum GovKit, conflicts/cycles, supported context, duplicate contributions and source/digest pins. Compatible versions of one provider are searched deterministically with backtracking. The synthetic root is namespaced separately from pack IDs. Local/bundled ambiguity requires an explicit selection. Pins constrain selection without enabling capabilities.
- **Ownership and authority:** previews show create/preserve/update/remove/protected operations and owners. Apply requires the accepted target profile, rechecks inputs, stages writes and updates the lock last. Lock replay derives owned destinations from pinned manifests instead of accepting arbitrary serialized paths. User files, edited native skills and edited lock metadata remain protected; symlinks, traversal, drift and stale previews are rejected. Unchanged apply preserves bytes/mtimes; caught write failure rolls back completed changes. Accepted policy controls still need providers after optional pack removal. Examples/defaults remain advisory. No legacy marker, instructions, CI or full exemplar library is installed implicitly.
- **Worked examples:** new `application-governance`, skill-only `gherkin-delivery`, and skill-plus-control `llm-evaluation` packs compose independently. The real `llm-exact-match` executable validates nonempty uniquely identified supplied records and returns pass/failure/invalid status independently of agent/skill loading. Missing native skills do not prevent its control; modified pinned code is refused. Two explicit profile examples demonstrate LLM-without-Gherkin and Gherkin-without-LLM. Existing third-party content remains unchanged.
- **Final green:** four new pack test files → **53 passed**. Final `source .venv/bin/activate && ./run_tests -q` → **3884 passed, 2 skipped, 150 deselected** in 31.58 seconds. The skips remain the non-Copilot applyTo cases; the excluded tier is e2e. An expanded profile/pack/extension/legacy run passed **523 tests** before the final graph-root regression was added. The 258 frozen legacy selections remain covered. Scoped Ruff lint/format checks and `git diff --check` passed.
- **Wheel and CI evidence:** final wheel installed with runtime dependencies only into a fresh temporary environment (Python 3.12.14, packaging 26.3, jsonschema 4.26.0, PyYAML 6.0.3). Isolated Python asserted imports came from that environment. All **7 bundled packs × 3 agents = 21 installs** passed real CLI preview/apply, stable-mtime reapply, native frontmatter/reference checks, relocation and offline verification. Both new profile examples resolved independently. The LLM control passed/faulted appropriately for every agent after removing the native skill directory. Added `tests/wheel_pack_smoke.py` to installer CI, then executed the exact new shell step locally with only its temporary interpreter path substituted. The existing profile wheel step also passed all 3 examples. No hosted run or live coding-agent invocation is claimed.
- **Acceptance mapping:** #145's first 15 criteria are demonstrated locally for this repository-composition scope. The pure graph establishes available/applicable selections; profile policy identifies mandatory controls; lock replay and hashes establish actual installed resources. CLI/storage tests exercise no-write preview, portable local sources, ownership, protected refresh/removal and independent execution. Native placement/resource behavior is verified for all supported agents from the wheel. Legacy compatibility remains covered by unchanged command implementations and tests. #145 and the epic feature checkbox stay open because inventory/approved metadata/candidates/assessment complete in I09.
- **Standards applied:** reused Appendix B's recorded Qodo rules. Shared strict schema loading and byte staging have real profile/pack consumers; typed models separate reads, resolution and writes. The dedicated command registrar, inward imports, live paths, existing wheel mappings, neutral skills and explicit ownership follow the recorded command/payload rules. Isolated fixtures run real resolver/CLI/executable behavior with only I/O failure seams substituted and explicit assertions. No external Qodo review submission was retried.
- **Review and fingerprint:** local review checked authority, no-write/stale-input behavior, dependency-root identity, lock replay, resource ownership and packaged execution. SHA-256 **`cc2f59639ef2df4ee9bc4a0d43686a704ccb5406551b33b1d7af58b70176b5f1`**, computed over compact sorted-key JSON mapping the **43 non-plan changed/new paths** to their file-content SHA-256. This execution plan is excluded to avoid self-reference.
- **Limits:** local Python 3.12 only; the full e2e/toolchain tier, Python 3.11, Windows and live agent sessions were not run. Native placement/reference checks do not prove agent reasoning. Pins/replay establish consistency, not source authenticity or authenticated acceptance. Standalone controls execute explicitly trusted pack code and are not sandboxed. The evaluator consumes supplied outputs; it does not run a model or prove evidence origin/freshness. General evidence protocols are I04, request routing I06, pipeline rendering I07 and maintenance candidates I09. Legacy contract prose keeps its original layout semantics; new-path copies are reference material, not accepted architecture. Per-file atomicity/caught-failure rollback are not concurrent-writer or crash-recovery guarantees.
- **Pre-PR verification:** rechecked all 43 non-plan implementation paths against the recorded tested fingerprint and confirmed whitespace checks passed. Only plan delivery metadata and the user's new standing commit/PR instruction changed after validation; passing implementation checks were not repeated. No external Qodo submission was retried.
- **Delivery:** committed the implementation and updated plan as `c878d495ca1b7aac645acd9616f12fecc39593a7`, pushed `feat/145-capability-packs`, and opened [PR #183](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/183) against main with `Refs #145`. The plan-link follow-up was 9ed7f6a. PR #183 merged on 2026-09-23 as b379a5a150a5c6dfd89a9ad22a985ec61f977fc3. Its [Tests workflow](https://github.com/Accelerated-Innovation/governed-ai-delivery/actions/runs/35915454204) passed for head 9ed7f6a; individual logs/artifacts were not re-audited. #145 remains open for I09.
- **Next:** after PR #183 merges, synchronize/clean up and begin I04 with failing check/evidence tests; commit/create its PR when finished under the standing delivery instruction. Treat schemas, pack commands and storage layout as public contracts from this increment onward.

### I04 execution record — 2026-09-23

- **Identity and cleanup:** implemented on `feat/146-check-evidence-foundation`, based on merged I03 `b379a5a150a5c6dfd89a9ad22a985ec61f977fc3`. Confirmed PR #183 merged, its remote branch deleted, and its Tests workflow successful for head `9ed7f6a`. Fetched/pruned, fast-forwarded main, verified identical former-branch/main trees and removed the squash-merged local branch. #145 remains open for I09; its I03 criteria are integrated.
- **Test-first red:** before edits, **359 legacy doctor/validate/extension/evidence tests passed**. New protocol/adapter tests first produced **2 collection errors** for missing check modules. CLI tests failed before the command existed. Further failing regressions exposed malformed outcomes aborting aggregation, lost accepted-policy provenance, folder-name/accepted-repository identity disagreement, unreadable ADR inventories and a policy directory becoming passes, and legacy internal exceptions exposing payloads. Each behavior was fixed after reproducing its failure. A three-example assertion failed before records were generated; an incorrectly shaped test approval policy was corrected against the existing schema without relaxing production validation.
- **Contract:** [ADR 0004](decisions/0004-check-evidence-foundation.md) records typed check specifications/outcomes/findings/evidence, an explicit registry, sequential isolated execution and strict versioned raw results. Required selection survives missing providers, with accepted policy taking precedence over pack/caller selection metadata. Findings include stable content-derived IDs, reasons, policy, scope and actions. Execution and outcome are separate; unknown/skipped/not-applicable/waived required results never count as passes. Report loading recomputes IDs/totals for inspection, not authenticated gate input.
- **Adapters and compatibility:** `govkit conform` renders the same canonical report as text or JSON. Profile/lock consistency and existing doctor/feature/extension/approval checks use explicit domain seams; legacy commands retain their output and exit behavior. Inspection never migrates legacy markers and validates local schemas offline with runtime dependencies. Doctor silence stays unknown. Predictions are identified as agent assertions. Unreadable inventories, missing schema coverage, exceptions, malformed outcomes and unconfigured controls stay visible while unrelated checks continue. Pinned controls require explicit opt-in and run independently of loading skills, with separate native-resource drift findings.
- **Final green:** **36 new tests** across `test_check_runner.py`, `test_conformance.py` and `test_cmd_conform.py`; the expanded new/legacy run passed **395 tests**. Final `source .venv/bin/activate && ./run_tests -q` → **3920 passed, 2 existing format-specific skips, 150 e2e tests deselected**, in 33.38 seconds. Scoped Ruff lint/format and whitespace checks passed. Filesystem snapshots cover no-write inspection, including old `.govkit` files; test substitutions target external dependencies rather than production behavior.
- **Wheel and worked records:** the final wheel was installed with runtime dependencies only into a fresh Python 3.12.14 environment; isolated imports came from that environment. Three bundled pass/unknown/failure reports validated and replayed. The real CLI demonstrated skipped, executed-pass and executed-fail LLM checks without Gherkin/legacy markers, unchanged target bytes/mtimes during checks, and identical reports for identical explicit local/CI inputs. Added `tests/wheel_check_smoke.py` to installer CI and executed the exact new shell step locally with only its temporary interpreter path substituted. No I04 hosted CI result is claimed yet.
- **Acceptance mapping:** #146 criteria 6–9 (non-pass required evidence, versioned/provenant findings, isolated non-printing checks with compatibility, and real positive/negative controls) are demonstrated locally. Criterion 1 has foundation parity evidence but stays unchecked for its complete change-scoped contract. Criteria 2–5 await workflow/diff/transition integration; all maintenance criteria remain unchecked. #146 and the epic remain open.
- **Scope and limits:** 24 changed paths including this plan; no consumer install was applied to this source repository. Local evidence is Python 3.12; full local e2e/toolchain, Python 3.11, Windows and live provider/agent sessions were not run. Origin labels/digests do not authenticate policy or evidence authors/freshness. Revision/time annotations are explicit inputs; unavailable change/dirty-tree facts remain null. Pack code is trusted and unsandboxed; the evaluator measures supplied outputs without running a model. Concurrent filesystem edits are outside snapshot guarantees. Actual-change routing, authorized waivers, provider enforcement, pipeline generation and maintenance remain later increments. Appendix B's previously loaded Qodo rules were reused; the prior rejected external diff export was not retried and review was local.
- **Delivery:** committed implementation and plan as `78b10691bf00c284875789a0db10374fa73ed34e`, pushed `feat/146-check-evidence-foundation`, and opened [PR #184](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/184) against main with `Refs #146`. This plan-only follow-up records the link and final handoff; implementation checks were not repeated for delivery metadata. #146 remains open. No merge was performed.
- **Next:** after I04 merges, confirm/synchronize/clean up, then implement I05 focused brownfield discovery (#178) test first with documented-service, sparse, unfamiliar-MCP and monorepo fixtures. Preserve the check protocol and accepted-policy/observed-evidence boundary.

### I04 PR #184 review remediation — 2026-09-23

- **Review input:** Qodo CLI 1.0.3, using the `qodo-review-resolver` skill and structured review-session reads. Qodo run `1237405` completed for `78b1069`, with five open findings (three action-required, two remediation-recommended). PR/checkout repository identities matched. PR head `2dd5dcd` changed only this plan's delivery links; `git diff 78b1069..2dd5dcd -- cli tests` was empty. The findings were independently reproduced in the unchanged current code under the user's explicit remediation request; the older review was not described as a completed review of the head. Hosted Tests run [35918505405](https://github.com/Accelerated-Innovation/governed-ai-delivery/actions/runs/35918505405) succeeded for `2dd5dcd`; individual jobs/artifacts were not re-audited.
- **Test first:** the existing approval/conformance/runner/CLI baseline passed **95 tests**. New regression cases produced **17 failures and 6 passes** before production changes. The failures demonstrated external policy/ADR reads, absent record provenance, suppressed inventory errors, lost unreadable-policy diagnostics and invalid pack-execution IDs. A follow-up failing case caught a diagnostic matching the wrong ADR when filenames shared a prefix; source matching now uses the longest complete path prefix.
- **`0de674b3-237f-4362-9af3-6440ab22c595` — external policy satisfies approval:** validate both schema and instance repository containment. Approval/ADR reads reject external targets before opening them; directory symlinks cannot escape inventory scope. Internal file symlinks retain their lexical evidence identity.
- **`7b534132-0906-4316-820e-54199543cc2f` — decision checks omit record evidence:** inject the file-read boundary into existing approval checks and capture evidence from the exact policy/ADR bytes consumed. Every read in-scope ADR has a source, scope, digest, method and limitation. Templates and excluded records do not acquire fabricated evidence.
- **`e41e1e3b-96d4-4bd9-9e3f-a1610d765996` — unreadable decision records can pass:** strict inventory discovery uses explicit metadata calls and directory traversal, propagating permission errors, loops and broken links instead of relying on predicates that suppress filesystem errors. Tests cover every inventory level and individual records.
- **`291735ea-3703-463c-823d-67e21cb177f3` — unreadable policies lose their diagnosis:** capture unavailable evidence without re-reading it for a hash. Keep the source-specific diagnosis and location, mark evidence unverified with no digest, omit exception payloads and retain other records/findings.
- **`f8142342-901f-49bf-bed3-79303de26dad` — non-pack options alter required checks:** require every execution ID to belong to the selected pinned lock before running checks. Built-in/uninstalled IDs are argument errors and cannot promote advisory controls; an invalid mixed batch executes nothing.
- **Verification:** **23 added regressions**; the final expanded approval/conformance/legacy selection passed **336 tests**. Fast suite: **3943 passed, 2 existing skips, 150 e2e tests deselected**. Scoped Ruff lint/format and whitespace checks passed. A fresh runtime-only wheel environment passed the existing report/control smoke, plus real CLI ADR-digest, external-policy-rejection and invalid-pack-ID checks; the final wheel was rebuilt and its smoke rerun after the source-diagnosis refinement. No schema fields changed, and the existing report examples still validate/replay.
- **Delivery/status:** these fixes update the existing PR #184 under the standing commit/push instruction; no new PR or merge. All five findings are addressed in code, with none dismissed or skipped. Qodo's review catalog exposed only `findings`, including after one catalog refresh, so manual `mark-implemented`/`dismiss` writes were unavailable. A fresh Qodo review must re-attribute the pushed fixes; no clean review of the fix commit is claimed here. #146 remains open for its later integrated criteria. Local Python 3.12, snapshot/concurrency and live-provider limitations remain as recorded above.

### I05 execution record — 2026-09-23

- **Identity and cleanup:** implemented on `feat/178-brownfield-discovery`, based on merged I04 `5426abe7ac3929a0d53e93774eacc7de85a078ec`. Confirmed PR #184 merged and [Tests run 35920010148](https://github.com/Accelerated-Innovation/governed-ai-delivery/actions/runs/35920010148) succeeded for final head `ccf0c22`; individual logs/artifacts were not re-audited. Fetched/pruned, synchronized main, verified identical trees and removed the merged local branch. Removed only five known I04 temporary build/wheel artifacts; preserved `.venv` and unrelated local state. No new Qodo review status is inferred from merge.
- **Test-first red:** the existing profile/materialization/setup baseline passed **62 tests**. The first discovery tests failed collection because the new module did not exist; four real CLI tests failed before command registration. Later failing regressions exposed changed reference selection being misreported as file deletion, explicit manifest references losing component boundaries, an old single-file marker aborting unrelated discovery, omitted policy-only maintenance findings, and a baseline claiming installer readiness without an accepted profile. The four-example assertion failed before fixtures were added. One test's guessed skill destination was corrected against the shipped pack manifest without changing installer behavior.
- **Contract:** [ADR 0005](decisions/0005-brownfield-discovery.md) separates bounded collection, scoped proposals/rediscovery, accepted profiles and protected installation. `govkit discover` is offline/read-only; it does not run application code or checks, migrate markers, fetch policy, refactor source, accept a baseline or rewrite architecture. Source/digest/confidence/scope observations and explicit incomplete coverage feed a versioned report. Observed imports/frameworks/architecture phrases are narrow indicators, never accepted policy. Python MCP does not imply FastAPI. Accepted project sources take precedence, and optional architecture questions do not block independent useful capabilities.
- **Composition and repeat review:** explicit accepted profiles delegate metadata/resource operations to the I02/I03 preview modules; the existing apply commands retain stale-input/edit protection and idempotence. Scoped retain/improve/migrate contracts, current/target rules, existing exceptions and exit-verification references remain intact. Baseline comparison surfaces changed dependency/framework, component, model/tool, reference, test and CI evidence at the same CLI version. Unchanged evidence does not repeat setup; pending decisions are preserved rather than accepted. Changed/incomplete coverage cannot prove deletion. `maintenance_outcome()` supplies I04-compatible findings without a conformance pass or a policy-violation inference.
- **Final green:** **39 new tests** in `test_discovery.py` and `test_cmd_discover.py`; focused discovery/profile/pack/check integration passed **130 tests**. `source .venv/bin/activate && ./run_tests -q` → **3982 passed, 2 existing format-specific skips, 150 e2e tests deselected**, in 37.13 seconds. Scoped non-rewriting Ruff inspection, changed-file formatting and whitespace checks passed. Snapshot assertions cover byte/mtime preservation, source documents, applications and old markers. Network/process substitutes target external dependencies, not the implementation under test.
- **Wheel/CI:** a fresh Python 3.12.14 environment installed the built wheel with runtime dependencies only. Four bundled repositories (documented service, sparse repo, unfamiliar MCP server and monorepo) validate/report through the real CLI. Documented service and monorepo adoption preserve original files and install only selected evaluation resources; repeated apply is idempotent. Same-version model usage changes produce a pending capability recommendation. `tests/wheel_discovery_smoke.py` passes, as does the exact new installer CI shell step with only its temporary interpreter path substituted. Consumer GitHub/Azure templates and agent payloads are unchanged. No hosted I05 CI result is claimed yet.
- **Acceptance:** twelve #178 criteria are locally demonstrated. Its gradual-transition criterion remains unchecked for actual-change exception/violation classification, owned by I07; the fixture does demonstrate declarations and verification/exit references. #178 and epic #142 remain open. I05's bounded exit criteria are met; I06 is next after review/merge. #146 remains open for I07/I09; this increment contributes a typed observation adapter, not integrated maintenance or a gate.
- **Limits:** stable local snapshots and narrow syntactic heuristics, not exhaustive/semantic architecture inference. Local source references only; URLs, symlinks and fragments are explicit unavailable inputs. Explicit accepted profile/installer inputs are read by the existing loaders outside the scan budgets. Baseline identity and digest consistency do not authenticate its author. Actual Git-diff checks, transition execution, release/resource assessment and remote reporting remain later increments. Local evidence covers Python 3.12; full e2e/toolchain, Python 3.11, Windows and live agent/provider sessions were not run. Appendix B rules were reused, and the previously rejected external diff export was not retried.
- **Delivery:** committed implementation and plan as `09a1de3ff3628403b0041bc954fbfc09b1cfc16c`, pushed `feat/178-brownfield-discovery`, and opened [PR #185](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/185) against main with `Refs #178`. This plan-only follow-up records delivery and handoff; unchanged implementation checks were not repeated. No merge or consumer install was performed. The change spans 18 paths including this plan.

### I05 PR #185 review remediation — 2026-09-23

- **Review input:** `qodo-review-resolver` skill, Qodo CLI 1.0.3, structured review run `1238179` completed at `09a1de3`. Three open findings: two action-required, one recommended. The current PR head `fe670f8` differs only in plan delivery metadata; `git diff 09a1de3..HEAD -- cli tests governance` is empty. Findings were independently reproduced in unchanged current code; the older run is not claimed as an exact-head review. Checkout origin and provider repository identity match. [Tests run 35925719448](https://github.com/Accelerated-Innovation/governed-ai-delivery/actions/runs/35925719448) succeeded for `fe670f8`; individual job logs/artifacts were not re-audited.
- **Test first:** the existing discovery/CLI baseline passed **39 tests**. New tests produced **12 failures and 1 pass** before production edits, exercising real report/CLI/pack paths and a lazy reference-input boundary.
- **`c59e54c2-d88a-459b-8225-f9b75926ff0e` — false removal claims:** require both baseline and current coverage to be complete, with matching limits/references, before emitting removal. A baseline limited by an unrelated oversized file cannot prove deletion on a later complete scan; the absent source remains unavailable.
- **`e77956f2-3de9-466d-9124-ea0b2f9f326f` — pack conflicts abort discovery:** isolate `PackError` alongside profile/filesystem failures in the installation-preview boundary. Six real CLI cases cover malformed/inconsistent locks, missing pinned resources, symlink destinations and conflicting parent/destination types. Evidence, accepted profile and focused installation diagnostics survive; targets stay unchanged.
- **`f1d10fde-dcd0-44ae-8747-695fe4b217ec` — unbounded references:** stream caller and accepted-profile references into bounded collection before materializing/sorting; cap retained distinct sources at `max_files` and iteration at `max_entries` plus one overflow probe. Duplicate-heavy streams cannot bypass the budget. Record `reference-limit` and only the retained references; never present truncated coverage as complete. Accepted policy is preserved unchanged.
- **Workflow update:** future PR creation now requires Qodo local review with session context under the user's explicit standing instruction. This existing PR uses its structured review findings. No new PR or merge is intended.
- **Verification:** **13 additional regressions**, with the expanded discovery/CLI/profile-store/pack-store/check selection passing **109 tests**. Final fast suite: **3995 passed, 2 existing format-specific skips, 150 e2e deselected**, in 32.10 seconds. Scoped Ruff lint/format and whitespace checks passed. A fresh runtime-only Python 3.12 wheel passed all four example/adoption scenarios plus real CLI incomplete-baseline, malformed-lock and reference-overflow regressions. Existing schemas remain unchanged.
- **Delivery/status:** fixes are committed/pushed to existing PR #185 under the standing instruction; no new PR or merge. All three findings were reproduced and addressed; none dismissed or skipped. The authenticated Qodo catalog exposes only review reads, so manual `mark-implemented`/`dismiss` writes are unavailable. Re-review must verify/re-attribute the pushed fixes; no clean exact-head Qodo review is claimed. #178 remains open for I07's integrated transition criterion. The same local Python/platform, snapshot and explicit-profile-loader limitations apply.

### Decision log

| Date | Decision | Basis |
|---|---|---|
| 2026-09-23 | Use this file as execution source of truth | Explicit user request |
| 2026-09-23 | Use a test-first process for every implementation increment | Explicit user request; record failing tests before implementation and passing evidence afterward |
| 2026-09-23 | Run Qodo local review with context before future PR creation | Explicit user instruction; record the actual review result and handle verified bugs test first |
| 2026-09-23 | Commit, push and create a PR whenever an increment is finished and verified | Explicit standing user instruction; no additional commit/PR prompt required; merging remains separate |
| 2026-09-23 | Separate bounded brownfield observations from accepted profiles and reuse protected installer previews | I05 tests and [ADR 0005](decisions/0005-brownfield-discovery.md); explicit baselines, scoped review and no new write path |
| 2026-09-23 | Add a shared check/evidence protocol and explicit `govkit conform` report with conservative legacy adapters | I04 tests and [ADR 0004](decisions/0004-check-evidence-foundation.md); required unknowns cannot pass, pack execution is explicit, raw reports are not authenticated gate input |
| 2026-09-23 | Extend existing manifests with a versioned pack contract, pin declared resources and render native skills from one source | I03 tests and [ADR 0003](decisions/0003-capability-pack-installation.md); offline replay, explicit local overrides and independently executable controls |
| 2026-09-23 | Expose explicit profile preview/apply for two-file metadata materialization; retain legacy command behavior | I02 tests and [ADR 0002](decisions/0002-profile-materialization.md); profile configuration is not capability installation |
| 2026-09-23 | Validate public profiles and records with bundled JSON Schemas at runtime | I02 dependency promotion and wheel evidence; reject unsupported versions/fields/authority and replay generated records |
| 2026-09-23 | Keep the legacy facade and ordered manifest selection behind a pure requirements core | I01 characterization and [ADR 0001](decisions/0001-resolution-boundaries.md); no public CLI or installer semantics change |
| 2026-09-23 | Treat plan readiness as consistency only; retain accepted policy and request requirements separately | #143 trust boundary; requirement selection is not execution evidence or write authorization |
| 2026-09-23 | Use GitHub's event base SHA and Azure Repos' fetched PR target ref for I00 | Provider-specific inputs; no origin/main assumption; fetch/diff failure must be visible |
| 2026-09-23 | Capabilities and per-request workflows replace levels in the new model | Agreed product direction; legacy semantics retained for migration |
| 2026-09-23 | Discovery and focused confirmation precede brownfield writes | Agreed adoption approach |
| 2026-09-23 | Packs remain delivery units; skills are their main interaction surface | Updated #145 |
| 2026-09-23 | Maintenance recommendations require independent dimensions and evidence | Updated #144–149 and #178 |
| 2026-09-23 | Keep physical removal of legacy inputs for a later release | Compatibility period and migration evidence required |

## Appendix A. Acceptance contract captured from the issues

Captured from the live issue list on 2026-09-23. These are requirements, not claims of completion. Each feature spans the increments mapped in Section 3; do not close an issue after only its first increment. Keep these checkboxes and the execution ledger consistent with recorded evidence. For #151, use I00's explicit transport/approval cases because the issue has no checkbox acceptance list.

### Feature #143

Source: [[Feature 1] Capability-based resolution foundation and legacy adapter](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/143).

- [x] Representative existing agent × level × type × CI × stack configurations preserve their artifact selections and supported behavior through the adapter.
- [x] The new domain model resolves without a maturity-level field; legacy level handling stays inside compatibility code/provenance.
- [x] Repository configuration and per-request requirements are separate typed inputs with independently inspectable outputs.
- [x] Each selected capability, artifact, and check carries its applicability reason and authority/source.
- [x] Identical explicit inputs produce identical serialized plans; ambiguous or conflicting inputs yield structured unresolved decisions.
- [x] The core has no writes, network access, printing, or process exits.
- [x] Existing tests and focused characterization tests pass; downstream consumers do not import command modules.
- [x] The ADR documents trust boundaries, dependency direction, and migration seams.

Evidence: [I01 execution record](#i01-execution-record--2026-09-23); integrated through PR #181. This does not claim a published release or completed epic.

### Feature #144

Source: [[Feature 2] Declarative capabilities, architecture decisions, and team policy](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/144).

- [x] New profiles require no maturity level and can express independent capability combinations.
- [x] A repository can permit a qualifying small-change workflow and a full Gherkin workflow without profile edits between requests.
- [x] Unknown repository/stack characteristics can be represented without accepting a framework default; relevant required decisions remain explicit.
- [x] Observations cannot silently become accepted policy; existing authoritative documents can be referenced without duplication.
- [x] Scoped retain/improve/migrate decisions can coexist; recording a target architecture does not activate it everywhere.
- [x] Mandatory policy controls remain required regardless of a request's preferred workflow.
- [x] Preview has no target writes and distinguishes accepted decisions, proposals, and unknowns.
- [x] Profiles and resolution records are schema-valid, versioned, and deterministic.
- [x] Invalid/conflicting choices produce actionable errors; legacy marker, flags, upgrades, and edit protection remain covered.

- [x] Maintenance policy can express approved sources, channels, pins/compatibility constraints, and freshness limits without making online lookup mandatory or changing the project lock during assessment.
- [x] A newer release alone does not produce a policy violation; missing/stale release information is represented explicitly rather than treated as current.

Evidence: [I02 execution record](#i02-execution-record--2026-09-23); configuration acceptance integrated through PR #182; this does not claim execution of the later workflow/maintenance engines.

### Feature #145

Source: [[Feature 3] Composable capability packs, dependency resolution, and locking](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/145).

- [x] The package contract supports both a skill-only pack and a pack containing skills, configuration/resources, and executable controls.
- [x] Skills are available through each supported agent's appropriate native mechanism from one authoritative package source; required resources resolve correctly.
- [x] A pack's required controls run through local/CI tooling without an agent session or loaded skill; agent self-report alone cannot satisfy enforcement.
- [x] Resolution is deterministic and side-effect free; cycles/conflicts fail before copying.
- [x] Independent combinations include LLM evaluation with application governance without mandatory Gherkin artifacts, and Gherkin delivery without LLM capabilities.
- [x] Every required dependency has an explicit rationale; the new resolver does not infer dependencies from a maturity label.
- [x] All shipped packs resolve; `govkit_min_version`, compatibility, versions, and digests are enforced.
- [x] Available, installed, applicable, and policy-required states remain distinct. Selecting fewer optional skills/packs cannot remove mandatory controls.
- [x] Brownfield adoption reuses existing accepted sources and installs only necessary integrations/resources; customization of the full exemplar library is not required.
- [x] Exemplars do not become authoritative through installation, and project-owned decisions/overrides remain distinct from shared pack content.
- [x] Pinned resources resolve on a clean developer/CI environment after explicit setup, support offline request resolution, and fail clearly if required content is missing or mismatched.
- [x] Preview performs no target writes and shows instruction/CI changes and ownership; authorized application is idempotent and preserves local edits.
- [x] Proposed removals expose affected dependencies/controls and cannot silently weaken policy.
- [x] Existing extension behavior remains covered through compatibility; no mandatory new registry or silent layout migration is introduced.
- [x] Worked examples demonstrate the LLM evaluation pack and a skill-only pack across installation, invocation, and applicable independent checks.

- [ ] Version inventory distinguishes the running CLI, repository installation, selected/locked versions, and actual resource digests; a matching marker version cannot hide missing or modified resources.
- [ ] Release metadata records approved source/channel, as-of/retrieval time, and lookup status; offline, stale, and failed lookups cannot be presented as proof of latest-version freshness.
- [ ] Candidate selection respects version ordering, channels, compatibility, dependency constraints, and pins; a newer incompatible release is reported with its exclusion reason.
- [ ] Assessment and metadata refresh do not install packages, change locks, overwrite customizations, or transmit repository content. Candidate previews identify affected resources and controls.

Evidence: [I03 execution record](#i03-execution-record--2026-09-23), demonstrated locally and delivered in [PR #183](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/183), merged as b379a5a. These checks cover repository pack composition and native placement; live agent behavior, request routing, authenticated evidence and release inventory/candidates are not claimed. #145 remains open for I09.

### Feature #178

Source: [[Feature 8] Brownfield discovery and focused governance setup](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/178).

- [x] Discovery works on an ungoverned repository and writes no target files.
- [x] An existing repository with usable architecture/ADR/test/CI sources can adopt a selected capability without rewriting those sources or completing universal calibration.
- [x] Every proposed rule is traceable to an accepted source or a clearly marked decision awaiting confirmation.
- [x] Unrecognized stacks, including a representative Python MCP-server fixture, retain explicit unknowns instead of installing FastAPI assumptions as accepted architecture.
- [x] Retain/improve/migrate choices can be scoped to different components; installation does not refactor application code.
- [ ] A gradual-transition fixture distinguishes existing exceptions from new violations and states how the transition will be verified.
- [x] Unresolved relevant decisions block dependent work only; unrelated hypothetical cleanup does not prevent first useful work.
- [x] Proposed operations are reviewable; authorized writes respect edit protection and are idempotent.
- [x] Repeated discovery reviews only stale/newly relevant decisions and does not repeat the entire setup ceremony.
- [x] Examples cover a documented conventional service, a sparsely documented repo, an unfamiliar MCP server, and a monorepo with conflicting conventions.

- [x] Repeat discovery detects representative repository/architecture/capability changes and supplies evidence-backed, scoped maintenance findings without modifying accepted policy.
- [x] A current-version repository with changed governance needs receives a focused review/capability recommendation; unchanged relevant evidence does not repeat the setup ceremony.
- [x] Incomplete or conflicting change evidence remains explicit, and a changed observation is not automatically treated as a violation or accepted replacement architecture.

Evidence: [I05 execution record](#i05-execution-record--2026-09-23). Twelve criteria are demonstrated locally; the transition fixture preserves scopes, existing exceptions and verification/exit references, but actual-change classification/enforcement remains I07. #178 stays open.

### Feature #179

Source: [[Feature 9] Per-request workflow selection and proportional evidence](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/179).

- [ ] One unchanged project profile supports a qualifying defect, small enhancement, and full feature request with different applicable steps/artifacts.
- [ ] A small enhancement inside accepted boundaries completes planning without a mandatory five-artifact feature package.
- [ ] Application governance plus LLM development/evaluation works without mandatory Gherkin; Gherkin delivery works without LLM capabilities.
- [ ] A small-looking security, public-contract, data, or architectural change still receives the applicable controls and decision requirements.
- [ ] Existing accepted contracts/NFRs/evidence can be referenced; new requirements are made explicit rather than inferred away.
- [ ] Normalized inputs resolve deterministically with inspectable reasons; ambiguity is visible and relevant mandatory requirements cannot be skipped.
- [ ] A developer override or agent-authored record cannot waive team policy; widened actual scope invalidates/revises the prior plan.
- [ ] Plans have versioned provenance and a documented conformance/CI consumption contract.
- [ ] No network installation, broad repository reconfiguration, or external ticket write occurs as a side effect of resolving a request.
- [ ] Worked examples cover a defect, bounded enhancement, behavior-preserving refactor, MCP tool change, LLM evaluation change, full Gherkin feature, and architecture migration.
- [ ] Guidance invokes only skills actually shipped/available and verified for the selected agent.

### Feature #146

Source: [[Feature 4] Policy-aware conformance for repositories and individual changes](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/146).

- [ ] Equivalent repository, policy, change, and evidence inputs yield equivalent local/CI findings for checks runnable in both environments.
- [ ] A qualifying small enhancement is evaluated without requiring the full feature package; a policy-required Gherkin workflow still enforces its artifacts.
- [ ] An LLM-related change executes its applicable evaluation checks regardless of workflow size.
- [ ] A request label, modified plan, or path filter cannot waive mandatory controls; actual diff expansion triggers re-evaluation.
- [ ] Existing violations/exceptions and newly introduced violations are distinguishable under scoped transition policy.
- [x] Missing, unreadable, unconfigured, unknown, or skipped required evidence never becomes a silent pass.
- [x] Findings/results validate against versioned schemas, preserve provenance, and use stable identifiers.
- [x] Checks do not print/exit internally; compatibility and independent failure reporting are covered.
- [x] Representative controls include a demonstrated failing case as well as a passing case.

- [ ] The maintenance assessment distinguishes release availability, installed-resource synchronization, repository fit, and CI integration health; it permits simultaneous findings instead of a misleading single current/outdated flag.
- [ ] A same-version installation with a missing/drifted managed resource recommends refresh/reconciliation; a current installation whose repo adds LLM usage can recommend capability review without falsely demanding a CLI upgrade.
- [ ] Compatible updates, incompatible newer releases, intentional pins, customized resources, offline/stale metadata, and failed lookups are covered by representative cases with evidence-backed reasons.
- [ ] Each recommendation names its action, affected controls/customizations, prerequisites, evidence and uncertainty; any required/blocking status traces to accepted policy.
- [ ] Output identifies the assessed repository/profile/resolution, time and release-metadata source/as-of status, and does not label unavailable freshness information as current.
- [ ] Assessment leaves code, profile, locks, installed resources, and CI unchanged, and can produce partial useful results when an integration is unavailable.

Evidence: [I04 execution record](#i04-execution-record--2026-09-23) demonstrates the four foundation criteria locally, delivered in [PR #184](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/184). Full change-scoped conformance and maintenance remain unimplemented; #146 stays open.

### Feature #147

Source: [[Feature 5] Capability- and policy-driven pipeline contracts](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/147).

- [ ] Equivalent profiles/capabilities/policies yield equivalent provider-neutral gate sets.
- [ ] Different request workflows in one repository select applicable checks without a pipeline rewrite.
- [ ] Required security, architecture, evaluation, and approval controls cannot be bypassed by a workflow label or path-filter omission.
- [ ] Both renderers cover the same intended gate IDs/policy; unavoidable platform differences are explicit and tested.
- [ ] Generation is deterministic, preview performs no writes, and existing workflows are protected.
- [ ] Integrations pin compatible versions and expose missing/inactive/unconfigured controls.
- [ ] Check mode detects missing/drifted generated integrations.
- [ ] Contract/golden tests include positive and negative controls plus the supported small-change and LLM combinations.

- [ ] A current CLI with stale pipeline pins or missing/drifted generated gates produces an actionable integration finding; static workflow presence alone is not reported as executed/enforced.
- [ ] Local and CI maintenance assessments agree for the same explicit inputs; provider evidence gaps are visible and report publication causes no automatic upgrade or workflow rewrite.
- [ ] A selected upgrade's integration preview identifies affected gates and configuration changes while preserving existing workflows until the proposed changes are authorized.

### Feature #148

Source: [[Feature 6] Capability and control posture reporting](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/148).

- [ ] Exports validate against a versioned schema and distinguish configured, applicable, executed, unknown, waived, and not-applicable states.
- [ ] Reports include relevant capability, evaluation, exception, architecture-transition, and CI coverage facts without requiring maturity labels.
- [ ] JSON is deterministic within its documented run-identity exceptions and can be aggregated without parsing logs.
- [ ] Unknown/skipped controls cannot count as passes; aggregation denominators are documented.
- [ ] Privacy guarantees are documented and covered: no developer identity, request/prompt text, ticket content, source code, secrets, or behavioral telemetry is collected; no automatic network transmission occurs.
- [ ] Example aggregation demonstrates capability coverage, version freshness, drift, and actual evaluation execution.
- [ ] A distinct pilot protocol evaluates usefulness/effort and includes explicit uncertainty; installed/conformant is not presented as proof of developer value.

- [ ] Human-readable and JSON maintenance reports expose the same canonical findings/actions and distinguish available updates, required upgrades, resource refreshes, governance reviews, and CI repairs.
- [ ] Each report includes assessment/repository identity, metadata source/as-of/lookup status, compatible candidates or exclusion reasons, affected customizations, and proposed next actions within existing privacy rules.
- [ ] Aggregation documents explicit denominators, overlapping categories, freshness, and unknown coverage; intentional compliant pins are not misreported as failed compliance.
- [ ] Example reports cover a current healthy repo, an available compatible update, installed-resource drift at the same version, changed repo needs at current versions, an incompatible newer release, and unavailable/stale metadata.

### Feature #149

Source: [[Feature 7] Safe legacy migration, level retirement, and GovKit self-hosting](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/149).

- [ ] Representative L3/L4/L5 installations map to explicit capabilities and requirements with no silent loss of configured controls.
- [ ] Active enforcement is distinguished from installed/inactive controls; unresolved gaps are visible and cannot be reported as successful enforcement parity.
- [ ] Customized contracts, local extensions, agent guidance, and pipelines are preserved by default.
- [ ] Preview performs no target writes; ambiguous decisions are explicit and scoped.
- [ ] Authorized migration is deterministic/idempotent with documented rollback.
- [ ] Migrated repositories can use the new per-request workflow model under accepted policy without broadening agent authority.
- [ ] Legacy commands remain covered through the compatibility period; retirement names a release boundary and warning period.
- [ ] GovKit resolves its own profile, executes conformance, and exercises pipeline/reporting contracts without the full consumer bundle.
- [ ] Migration guidance demonstrates ordinary brownfield adoption separately from architecture migration.

- [ ] Upgrade/migration previews consume canonical maintenance findings and name the selected compatible target, impacted resources/controls, protected customizations, and any separate review or repair needed.
- [ ] Stale proposals are detected before writes; completion checks report remaining findings and do not infer resolution from a version-marker update.
- [ ] Documentation and examples distinguish a CLI/package update from a repository resource refresh and preserve the existing authorization, idempotency, and rollback guarantees.

### Epic #142

Source: [[Epic] Declarative, composable GovKit governance](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/142).

- [ ] A documented existing service adopts selected governance using its own accepted sources, with a minimal proposed diff and no mandatory full calibration.
- [ ] An unfamiliar MCP-server repository preserves unknowns and requests focused decisions instead of adopting unrelated API-framework defaults as policy.
- [ ] One unchanged project profile supports a defect, bounded enhancement, behavior-preserving refactor, and full Gherkin feature with proportionate steps.
- [ ] LLM development/evaluations operate with application governance without mandatory Gherkin; spec-driven delivery operates without LLM capabilities.
- [ ] A small security, data, public-contract, ownership, or architecture change receives the applicable additional controls regardless of its task label.
- [ ] A scoped architecture transition distinguishes current rules, target rules, existing exceptions, and verification. Installation itself does not migrate application code.
- [ ] Local and CI conformance agree where both can run the same checks; missing/inactive/unknown controls do not produce false confidence.
- [ ] Legacy L3/L4/L5 installs migrate without silent loss of configured requirements or customized content, with active enforcement reported separately.
- [ ] GovKit consumes the resulting model without installing all consumer documents/rules.
- [ ] Pilot evidence separates setup from recurring effort and compares similar work across familiar/unfamiliar repos. Conformance counts are not used as a proxy for developer value.

- [ ] Maintenance scenarios distinguish compatible release availability, intentional pins, resource drift at the same version, governance-fit changes at current versions, and stale/unavailable release metadata. Reports identify evidence, assessment/source freshness, affected customizations, and the appropriate action; authorized changes are checked afterward.

## Appendix B. Retrieved implementation standards

Retrieved through Qodo on 2026-09-23 with qodo-get-rules 1.1.4, scoped to /Accelerated-Innovation/governed-ai-delivery/. References below are the returned rule IDs; no external rule URLs were supplied. They constrain later implementation. Retrieval does not establish code compliance, and no implementation tests were run by the planning task.

| Rule ID | Severity | Returned rule name | Application to this work |
|---|---|---|---|
| 2287173 | WARNING | Enforce distinct overwrite behavior per file category in apply/upgrade commands | Characterize agent-config overwrite, governed-contract write-once apply/refresh on upgrade, and never-overwrite existing project artifacts; exercise existing/new paths for both commands. Preserve edit protection and the new project's explicitly protected customizations as qualified below. |
| 2287166 | WARNING | apply/upgrade must not modify user-authored files | Restrict writes/deletes/moves to known managed paths/entries or explicitly authorized generated operations. Discovered project paths do not become arbitrary write targets; preserve user-authored files and fail safely outside ownership. |
| 2287160 | WARNING | Isolate each CLI subcommand in its own module with a standard register(subparsers) entrypoint | Give each public subcommand a dedicated module and register(subparsers), add its subparser, and bind the handler with set_defaults(func=...). Keep dispatch out of domain logic. |
| 2287157 | WARNING | CLI modules must use attribute access on paths module instead of importing constants | Read paths attributes through the module at call time. No direct constant imports or cached module-level aliases that defeat monkeypatching. |
| 2287161 | WARNING | Register each CLI command module in govkit._REGISTRARS | Register each exposed command in cli/govkit.py's _REGISTRARS using the existing pattern. |
| 2287171 | WARNING | Persist apply command options to .govkit/marker.json with validated type | On the legacy apply path, validate supported type/level/CI inputs and persist the effective options deterministically in the existing marker representation. See the explicit new-model qualification below. |
| 2287176 | WARNING | Configure pyproject.toml `force-include` for new bundled asset directories | Include newly bundled asset directories in the wheel build configuration as appropriate and verify their installed paths from a real wheel. |
| 2287159 | WARNING | CLI command modules must not import other CLI command modules | Command modules consume shared/domain code, not other command handlers; helper modules must not hide public-command behavior. The registration dispatcher remains the intended wiring point. |
| 2297683 | WARNING | Consolidate duplicated if/case patterns into a shared strategy or table | Replace repeated identical condition-dispatch patterns with one shared strategy/table in the owning domain. |
| 2287158 | WARNING | cli/paths.py must not import from other cli modules | Keep cli/paths.py free of static or dynamic imports of other internal CLI modules. |
| 2297684 | RECOMMENDATION | Co-locate functions that consistently operate on the same data | Where multiple functions repeatedly operate on the same domain data, consider co-locating them; apply only where it improves the touched design. |
| 2287167 | WARNING | Map extensions directory to cli/extension_packs in pyproject.toml | Preserve extensions/ -> cli/extension_packs/ packaging; do not collide with cli/extensions.py. |
| 2297681 | WARNING | Replace constant-dispatching if/switch with data-driven dispatch | Use data-driven registration/dispatch for extensible constant-based selection where new cases would otherwise require repeated branches. |
| 2297668 | WARNING | Consolidate duplicated helper functions into a single shared helper | Consolidate duplicated transformations/helpers in the owning shared/domain module instead of copying behavior across commands. |
| 2297679 | WARNING | Do not introduce abstractions without evidence of representation pressure | Justify new abstractions with real consumers, repeated data or duplicated selection/check behavior; avoid speculative layers. |
| 2297678 | WARNING | Keep comprehensions simple; extract complex logic into named helpers | Keep comprehensions readable; move nested decisions and complex transformations into named helpers. |
| 2297666 | WARNING | Avoid deep method chaining through objects (Law of Demeter) | Avoid reaching through chains of collaborators; use appropriate delegation. Fluent self-returning builder APIs are not the target of this rule. |
| 2297661 | WARNING | Replace primitives carrying domain meaning with named types | Represent meaningful domain identities/results with named types rather than unexplained strings, tuples or dictionaries. |
| 2297670 | WARNING | Extract repeated validation/parsing logic into a method on the validated type | Centralize repeated validation/parsing with the validated type or its owning domain loader. |
| 2297664 | WARNING | Group co-occurring variables into a struct or value object | Group sets of three or more repeatedly co-occurring values into an appropriate typed value object. |
| 2287179 | WARNING | Keep AI agent code consistent with referenced architecture docs | Keep changed architecture documents and all skills/rules referring to their paths, interfaces or assumptions aligned; document a deliberate unchanged consumer if relevant. |
| 2287165 | WARNING | Keep agent skill and governance definitions in sync across all agent directories | Add, modify or remove equivalent governance/skill semantics across Claude Code, Codex and Copilot in the same change. |
| 2297577 | ERROR | Tests must not depend on execution order, shared mutable state, hidden fixtures, or environmental assumptions | Each test uses explicit isolated setup/fixtures; no ordering, shared mutable state, hidden setup or uncontrolled path/environment/network assumptions. |
| 2287168 | WARNING | Ensure example payloads validate against their declared JSON Schemas | Validate every changed starter/example against its declared schema, including required properties, types, enums, ranges/patterns and additional-property rules. |
| 2297569 | ERROR | Test seams must wrap dependencies, not production behavior under test | Substitute external dependencies in tests, not the production behavior being verified; the real production path under test must execute. |
| 2287169 | WARNING | Synchronize CI gate templates between providers and README | Keep corresponding GitHub/Azure gate checks and thresholds aligned and document every mapping and intentional provider difference in ci/README.md. |
| 2297614 | WARNING | Tests must not be added solely to increase code coverage percentages | Add tests for meaningful behavioral invariants, not merely line-coverage percentages or trivial implementation details. |
| 2287162 | WARNING | Skill SKILL.md frontmatter must be identical across all agent directories | Keep SKILL.md name and description fields byte-identical across all three agent variants, with no missing variant. |
| 2287174 | WARNING | Include SHA-256 hash in govkit editable header | Compute editable-header SHA-256 from the final body, excluding the header, and emit the current deterministic parseable format consistently. Preserve compatibility with legacy header readers. |
| 2297609 | WARNING | Prefer narrow deterministic unit tests over broad integration or end-to-end tests when they provide equivalent confidence | Use the narrowest deterministic test that provides equal confidence; retain broader execution tests only when they catch failures a narrower test cannot. |
| 2297588 | ERROR | Every test must contain explicit assertions that produce an unambiguous pass/fail result | Every test must have explicit programmatic assertions producing an unambiguous pass/fail result. |
| 2297672 | WARNING | Prefer standard library functions over custom reimplementations | Prefer equivalent standard-library behavior over custom reimplementation when it fits the actual requirement. |

### Scope qualifications and explicit decisions

- Rule 2287171 describes legacy maturity/type options. Apply it to compatibility behavior; it does not require levels in new profiles. The user's explicit capability-based direction governs the new model. Preserve the actual marker nesting/schema from code and tests rather than inventing top-level keys from a generalized rule description.
- Rule 2287173's general overwrite categories remain subject to existing hash/edit protection and the explicit customization guarantees in this plan. Do not interpret "overwrite on upgrade" as authorization to destroy edited or user-owned content. For the new path, implement the reviewed ownership/operation contract rather than broad unconditional overwrites.
- Rule 2287174 illustrates a header spelling; preserve the repository's tested emitted format while ensuring the body digest is correct. Do not rename a working header field merely to match an illustrative example.
- The named-type and refactoring rules apply to touched code and concrete repeated behavior. They do not authorize repository-wide cleanup or a speculative object framework. Co-location rule 2297684 is a recommendation.
- This is an execution plan, not a change to shipped architecture contracts. Payload references remain unchanged until their owning implementation increment; preserve legacy/new-mode distinctions when updating them.
- The three ERROR rules (2297577, 2297569, 2297588) apply to all new tests. This plan requires compliance and proposes no exceptions. Any future material conflict must be resolved under the applicable instructions rather than silently weakened.


### I06 implementation evidence — 2026-09-23

- Added structured local request/scope/context/plan schemas, pure additive workflow selection, read-only capture/replay, and `govkit request template/plan` with concise and explainable output. Four workflow lanes preserve compact bounded evidence, existing defect obligations, sensitive controls and independent LLM evaluation. Accepted policy requirements can escalate delivery; unknowns cannot silently qualify small work.
- Application Governance pack 1.1.0 ships agent-neutral request normalization/planning guidance. Native paths are exposed only after current profile/lock/resource verification; selected checks use I04 `CheckSpec` and observed sources use `Evidence`. Confirmation and local snapshots are not authenticated approval or executed evidence.
- Test-first evidence: initial collection failed because the resolver did not exist. Subsequent regressions failed before implementation for native guidance, CLI, policy-triggered full-workflow closure, full contract coverage, unrelated-reference blocking, I04 adapters, duplicate-source digest bypass and the existing substantial-feature selector. A later audit also reproduced a missing applicable target-architecture reference being treated as nonblocking, then required the transition current/target/exception sources. Seven worked examples and clean-wheel smoke cover all three native agents.
- Final local validation: **33 new request tests; 4,028 fast-suite passes, 2 existing Copilot-format skips, 150 e2e deselected** (35.76s). Scoped Ruff check/format and diff whitespace pass. Rebuilt runtime-only clean wheel passes seven examples across three agents, replay, supplied scope expansion, verified native guidance and read-only preservation. The toolchain tier and hosted CI were not run locally; CI remains pending.
- Qodo local review: CLI 1.0.3 authenticated via the existing host keychain. After automatic approval review initially rejected external export, the user explicitly approved sending this I06 diff and issue/plan context. The context reference format was corrected after local validation rejected strings. The actual deep review submitted 127,237 bytes including all 20 untracked files, then failed with backend `repo_not_connected`: the authenticated workspace cannot clone `Accelerated-Innovation/governed-ai-delivery`. No findings or clean verdict were returned. Do not retry until its Qodo Git integration is connected/reconnected. The PR records the unavailable review; no Qodo configuration was changed.
- Remaining boundary: supplied scope observations can add obligations/revise identity, but I07 must derive actual changed scope and enforce trusted conformance. #179's combined override/actual-scope acceptance criterion stays open until that integration; no automatic issue closure is requested.

- Delivery: implementation `5ff34d77cf73651583a6d1bf16bf558d6832e6c1` pushed on `feat/179-request-workflows`; [PR #186](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/186) opened with the Qodo limitation and verification evidence. #179 has ten locally demonstrated criteria checked and remains open for I07 actual-scope enforcement; epic #142 records the handoff. Hosted CI is pending, not claimed passed.


### PR #186 Qodo review remediation — 2026-09-23

- Qodo structured review run `1238528` completed for implementation `5ff34d7`; the then-current head `aa37299` differed only in this plan. All affected production/test files were unchanged. Reproduced each reported bug against the current checkout; no exact-head clean review is inferred from the older session.
- `f260808a-d4d9-44dc-b810-82d1131c8d03` (action required, Reliability): install the new skill as `govkit-request-planning`, preserving an existing unowned `request-planning` skill. Three regression cases cover native agent layouts and original user bytes/mtime.
- `1693f17c-c758-4a29-826c-ccb28b0cae71` (recommended, Reliability): share verification and its exact lock snapshot; remove the unverified second read before advertising guidance. Compare the verified lock profile digest with the profile captured by planning. Filesystem-boundary tests reproduce a different internally valid lock on the second read and a profile/lock replacement during capture. Observations are not filesystem transactions or approval evidence.
- `9eeef9aa-9a57-4f41-8cdf-47f8694b821c` (recommended, Correctness): allow the plan and every check to retain the union of 64 declared and 256 observed paths (up to 320). Boundary regressions exercise 256, 257 and 320 total paths, retained auth controls, identity reassessment, replay and no writes. The input limits stay unchanged.
- Test first: **7 failing regressions + 1 passing boundary control** before fixes; all **8 pass** afterward. Workflow/pack focused run: **61 passed**. Full fast suite: **4,036 passed, 2 existing Copilot-format skips, 150 e2e deselected** (40.34s). Scoped Ruff check/format and diff whitespace pass. A freshly built wheel in a clean runtime-only virtualenv passes seven examples across three agents plus user-skill collision, maximum scope/replay, resource-drift rejection and no-write checks.
- Prior hosted [Tests run 35928908847](https://github.com/Accelerated-Innovation/governed-ai-delivery/actions/runs/35928908847) succeeded for `aa37299`; individual logs/artifacts were not re-audited. The remediation's new CI/review is pending.
- All three findings are addressed in code, none skipped or dismissed. After one catalog refresh, this Qodo workspace exposes only structured findings reads, not mark-implemented/dismiss. Do not substitute forge comments for outcome writes or claim Qodo closed these findings before its returned attribution confirms that. #179 remains open for I07 actual-scope enforcement.


### I07 execution record — 2026-09-23

- **Integration and cleanup:** confirmed PR #186 merged as `b938a3b515e44cc73acb9dbe4b6bbe530cd824a8`; final-head Tests run `35929565253` succeeded for `9325749`. Fetched/pruned, fast-forwarded main, verified identical trees and deleted the merged local branch. Removed exactly eight known I06 temporary artifacts and preserved `.venv`. Started `feat/146-request-conformance` from merged main. The existing workflow/check baseline passed **75 tests**.
- **Test first:** added regression and pilot tests before their implementation. Observed red cases included missing actual-change/CLI integration, exception scope leakage, configuration changing between capture and planning, unsupported contract scope, duplicate execution after timeout, report identity tampering, executable-mode identity loss, a second unverified lock read, repeated argv rejection, and command execution after an invalid policy capture. Seven bundled pilot tests initially failed before their harness/fixtures existed. Defect eligibility/actual red-green, unclassified expansion, stale/tampered plans, unedited mandatory controls, unsafe Git inputs, missing artifacts/evaluation, expiry and unknown approvals are covered. Fixture-only mistakes were corrected without relaxing expected control outcomes.
- **Implementation:** `govkit conform --request ... --base ... --policy-target ...` captures bounded real Git changes, uses a separate accepted policy/resource checkout, reruns I06 planning and composes I04 required checks. Optional accepted `policy.conformance` adds literal impact rules, artifact references, explicit command providers and scoped literal architecture constraints. Invalid/changing accepted policy withholds command execution. Actual scope cannot be narrowed by a label, prior record or path filter. Git/policy/reference recapture rejects observed changes during checks. Pack execution uses the exact verified lock snapshot and executes against the change target.
- **Evidence and transitions:** versioned change-results embed/replay existing workflow/check contracts and bind Git/profile/lock/plan identities. Artifacts reuse accepted local references; presence is distinguished from semantic acceptance. Defects reuse bundled eligibility and require explicit baseline-fail/current-pass command execution in temporary isolation. Required LLM evaluation stays independent of workflow size. Current constraints include unedited files; target rules follow transition scope/applicability. Existing bounded dated exceptions cannot excuse added occurrences or escape their current-contract scope. Unknown expiry/coverage and platform-only approval remain unknown.
- **Pilot/runtime evidence:** seven shipped requests (defect, enhancement, refactor, MCP, LLM, feature, architecture) run against an isolated ungoverned Git repo with a separate policy checkout. Each demonstrates passing measurements and real failing behavior, unchanged inspected bytes/mtimes, replay and identical explicit local/CI JSON. Architecture's measurements pass while approval remains unknown. `tests/wheel_change_smoke.py` is included in installer CI. A fresh runtime-only Python 3.12 wheel environment passed the seven pilots and the existing workflow/check smokes; the final wheel was rebuilt and the new pilot smoke rerun after the final policy/schema fixes.
- **Final validation:** **39 new tests; 4,075 passed, 2 existing format-specific skips, 150 e2e tests deselected** in the fast suite (57.98 seconds). Scoped Ruff lint/format and whitespace checks pass. The initial isolated build was blocked by sandbox networking; the authorized build fetched declared dependencies and succeeded. No full local toolchain/e2e, Python 3.11, Windows, live team/agent/provider or hosted I07 CI result is claimed.
- **Limits and review:** Git observations are bounded and non-transactional; ignored untracked files and unsupported file kinds do not become verified evidence. Commands/packs are explicit, trusted and unsandboxed. Literal checks are not semantic architecture/dependency analysis; artifact presence is not approval. Trusted source/base/intent selection is the caller's boundary, not authenticated by local paths or hashes. Temporary defect baselines contain regular-file bytes, not Git metadata/dependencies/executable modes. Migration, consolidated maintenance and provider enforcement remain I08–I10. Appendix B's loaded coding rules were reused. Qodo CLI remains 1.0.3; the previously reported `repo_not_connected` blocker was not retried without reconnection confirmation. No I07 local findings or clean verdict are claimed.
- **Status:** all I07 exit evidence is locally demonstrated. #146's first five criteria, #178's transition criterion and #179's actual-scope criterion are now checked with linked evidence; #178/#179 remain open until this PR merges, #146 until I09. Implementation `9e40330` is committed and pushed in [PR #187](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/187). #142/#146/#178/#179 status bodies are updated; the PR closes #178/#179 only on merge. This plan-only follow-up records delivery metadata, without repeating implementation tests. No merge was performed. After integration, I08 is next.


### Qodo reconnection verification — 2026-09-24

The user reported reconnection. Qodo CLI 1.0.3 authenticated successfully through the existing host keychain; the sandbox-only login failure was not a genuine logout. Catalog refresh exposed 49 tools. A GitHub repository search for `governed-ai-delivery` returned an empty, untruncated result. A direct read of five public README lines from main returned `MT-WORKSPACE-NO-REPOS`, with upstream `WORKSPACE_HAS_NO_AUTHORIZED_REPOS` and HTTP 403. This confirms the authenticated workspace still lacks repository authorization; it does not establish that the portal reconnection failed in a different workspace. No local diff was submitted and no review result is claimed. The runtime's passive skill-update notice was left for explicit future maintenance. This plan-only update preserves the blocker with its current diagnostic; implementation tests were not repeated.


### PR #187 Qodo review remediation — 2026-09-24

- **Review provenance:** Qodo's structured review service works independently of the local repository integration that the user is pursuing with support. CLI 1.0.3 returned completed review run `1238902`, covering `9e40330b23a4a6a83f42cd879e50908d9cedfc34`, with nine pending findings (seven action-required, two recommended). The pre-fix head `feb8e89` differed only in this plan; all affected code was unchanged. Findings were independently reproduced against that checkout. This is not a claim of an exact-head clean review. Prior-head [Tests run 35977032985](https://github.com/Accelerated-Innovation/governed-ai-delivery/actions/runs/35977032985) succeeded for `feb8e89`; individual job logs/artifacts were not re-audited.
- **Defect evidence:** fixed `2b4a24f7-f2e8-4ad3-b9c1-30d7efec6a51` and `3b0ccfbf-8423-4867-98fa-83b1ce8f5f1e`. Current declared regression-test bytes now run against both isolated snapshots, with executable modes preserved and the same temporary path rebuilt between runs. Real-current and isolated-current passes are prerequisites for interpreting a baseline failure as red. Missing/obsolete base tests, absent Git metadata/ignored dependencies and lost execute bits no longer manufacture a passing defect verdict. The guide supersedes the earlier I07 baseline limitation above; bounded snapshots and configured command exit codes still do not prove arbitrary environment equivalence or distinguish every infrastructure failure.
- **Architecture:** fixed `3ee65046-765f-450d-9089-0b4cc98864be`. Each overlapping transition is measured independently and can use only its own exceptions. A shared top-level current contract is measured within its applicable transition contexts. Both transition orders retain the expired exception failure. `c39e4327-5d25-4628-999c-9cfb7aa4453a` (valid exceptions reported failed) **was not reproduced**: both the existing regression and an explicit shared-top-level-contract case pass before and after remediation. Keep that finding open for reviewer reconciliation; it was not dismissed or claimed as a reproduced bug.
- **Git observations:** fixed `b2a3f502-29e9-432b-a50b-5de66fd57337` and `e76a8022-2785-46dc-9b86-b43a186f21d3`. Sparse/skip-worktree and conflicted indexes fail closed without invented deletions. Index object IDs, modes and flags bind report identity and are recaptured for stability. Base-to-index deltas remain in actual scope even when working-tree bytes are restored; a differing staged version makes scope unverified until the caller reconciles it. Added/deleted/mode-only staged deltas and index-only mutations during execution are covered.
- **Input boundaries:** fixed `f712476a-ae2b-4c18-a926-8fccc3fde03f`, `59027747-8757-44a0-b8a9-f4c50e16c97a` and `9939ef1c-14ff-41dc-bb72-2f68322c7262`. Neither resolved checkout may contain the other. Pack arguments require a configured, required and explicitly selected pack. Timezone-bearing RFC 3339 timestamps are validated before commands; valid offset/lowercase forms normalize, while naive/date-only/space-separated/invalid-offset inputs are rejected. Directory separation remains an input guard, not an execution sandbox.
- **Test first and verification:** existing focused baseline **118 passed**. Initial review cases produced **16 failures and three passing controls** after correcting an exit-status mistake in the executable-mode test. A later invalid-offset boundary produced one further failure before its fix; four additional staged/index boundary controls pass. **24 new review regressions** now pass. The full fast suite passed **4,098 tests, two existing Copilot-format skips, 150 e2e deselected** (72.63s); after the final timestamp bound, all **63 focused tests** passed (39.86s). Scoped Ruff lint/format and whitespace checks pass. The final wheel was rebuilt in isolation and installed in a fresh runtime-only Python 3.12 environment; all seven actual-change pass/fail pilots, replay, no-write checks and local/CI parity pass. No local full-toolchain/e2e, Python 3.11, Windows or hosted fix-head result is claimed.
- **Delivery/status:** this remediation belongs to existing [PR #187](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/187); no new PR or merge is required. Eight verified findings are fixed; one has contrary regression evidence and remains undismissed. Qodo now exposes status-write tools, but prefer automatic attribution from the pushed fixes over manually clearing merge gates. Re-review and fix-head CI remain pending at this commit. #178/#179 stay open until merge, #146 stays open through I09, and #142 remains open. I08 remains next after PR #187 merges. No further local-review integration retry was made.
