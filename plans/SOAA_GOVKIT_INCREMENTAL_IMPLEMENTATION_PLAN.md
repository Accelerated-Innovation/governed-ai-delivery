# SOAA and GovKit Phase A incremental implementation plan

**Status:** Proposed plan, not started. Writing this plan implements none of it.
**Prepared:** 2026-10-19.
**Baseline inspected:** GovKit 0.22.0 at commit `0ec4568`. The working tree also
contains the uncommitted manifest-validation fix in `cli/extensions.py`,
`tests/test_extensions.py`, `tests/test_conformance.py` and `CHANGELOG.md`, and
the untracked proposal documents below.
**Sources:** [lightening plan](SOAA_EXTENSION_LIGHTENING_PLAN.md) (revised
proposal), [architecture and code review](SOAA_ARCHITECTURE_AND_GOVKIT_REVIEW.md),
[original draft](archive/SOAA_EXTENSION_LIGHTENING_PLAN_2026-10-17.md).
**Scope:** Phase A only. Deliver the experiment-aware development workflow, the
refined SOAA extension and an installable, verified package. Phase B, the
Value Builder pilot, starts after handoff and is not a prerequisite.

Line numbers below are from the inspected baseline. Verify them before
editing; they move.

## 1. How to use this plan

Each increment is a reviewable change with its own tests, verification commands
and completion evidence. Execute increments in dependency order (§7). Use test
first for every behavior change and defect: write the failing test, record the
red run, then implement. Record each increment in the ledger (§14) with the
commit, test counts and remaining limits. Run the Qodo local review before
each PR (CLAUDE.md, *Delivery review*). Follow the user's standing
commit/push/PR instruction. Merging and releasing need separate authorization.

Claim boundary for all increments:

- **Report validation:** the schema, identity, coverage, applicability and
  internal consistency of supplied records. This is what GovKit checks in
  Phase A.
- **Observed execution:** requires a trusted runner binding target and cases to
  collected evidence. Experiment records and uploaded results never supply it
  by themselves.
- **Formal SOAA conformance:** requires the released normative profile and the
  verified 206-assertion catalog. Nothing in Phase A claims it.

Phase A fixture results are **synthetic**. Every fixture labels them
`evidence_class: synthetic-fixture`. They test GovKit's tooling behavior, not
any application's runtime.

## 2. Baseline and preserved work

| Item | State | Treatment |
|---|---|---|
| Manifest-validation fix (review C1–C3) | Uncommitted: `cli/extensions.py` uses `parse_document` and `validate_document(…, "extension-manifest")`; 18 regression tests; CHANGELOG `[Unreleased] ### Fixed` | Preserve byte-for-byte; land first as Increment 0 |
| Proposal documents | Untracked `plans/SOAA_*.md`, `plans/archive/` | Commit with this plan as documentation |
| Recorded verification | Review §8: 5,239 passed / 2 skipped / 150 deselected fast tier; e2e and installed-wheel not run | Re-run focused + fast tier in Increment 0; e2e and wheel smoke before handoff (Increment 11) |
| Deprecation boundary (#149) | Level-based install deprecated from 1.0.0, supported throughout 1.x; feature scaffolding is still marker-only (#220) | Phase A must support **both** the legacy L5 feature-folder workflow and the declarative profile/pack/request path |

## 3. Repository analysis by capability

### 3.1 Request planning (declarative)

- **Exists, reuse.**
  - `cli/workflows.py` `resolve_workflow` is pure and its routing is additive.
    `_route` (≈202–216) chooses among four workflows. Selection is a
    fixed-point loop over policy rules (`known_selectors` ≈320–334), and
    readiness is blocked by any blocking decision.
  - Artifacts are assigned per workflow (≈445–473). The `architecture` workflow
    includes `architecture-decision`, the only decision link today.
  - The plan carries `identity` digests and `reassessment` (≈505–517).
  - `cli/workflow_store.py` `_context` (≈48–140) snapshots accepted references
    with digests and raises `changed-reference` on a declared-digest mismatch.
  - Replay is deterministic: any output difference for the same embedded inputs
    is rejected (≈165–187).
- **Missing.** There is no experiment, uncertainty or hypothesis concept, and
  no structured decision link. `reassessment.reasons` is one generic string,
  and nothing records evidence time.
- **Must change.**
  - `governance/schemas/workflow-request.schema.json` gets a new reference kind.
    The kind must also be added to the embedded enums in
    `workflow-plan.schema.json` and to the plan copy inside
    `change-results.schema.json`.
  - `cli/workflows.py`: escalation and the new artifact.
  - The `application-governance` request-planning skill.
  - An eighth example, plus `tests/test_workflows.py`,
    `tests/wheel_workflow_smoke.py` and `docs/REQUEST_WORKFLOWS.md`.
- **Discrepancy.** None with the proposal. Replay constrains how the change
  can be made: **output for every existing input must stay byte-identical**, or
  saved plans fail replay.

### 3.2 Architecture preflight

- **Exists, reuse.**
  - Skill `agents/*/skills/backend/govkit-architecture-preflight/SKILL.md`, byte-identical
    across the three agents (§2.6 extension discovery at L72–88; §15 topology at
    L187–204).
  - GenAI preflight `govkit-genai-preflight` (section 6 at L78–80 already
    triggers on agents and skills).
  - Templates `governance/backend/templates/{architecture_preflight,l5-architecture-preflight}.md`.
  - UI template `governance/ui/templates/architecture_preflight.md`.
- **Missing.** No machine-readable outcome, and no "experiment required"
  outcome. `govkit validate` never parses a preflight status: it checks only
  existence and the L5 `## 10.`–`## 14.` headings (`cli/validate.py`
  `check_l5_preflight_sections` ≈631). "Blocked" is enforced only by prose.
- **Discrepancy.** The status vocabulary differs between files:
  - The L4 template has "Approved for planning / Blocked pending ADR / Blocked
    pending clarification".
  - The L5 §16 has "Approved for planning | Blocked pending resolution".
  - GenAI preflight has "`Approved for planning`, `Requires ADR`, or `Blocked
    pending resolution`".
  - The UI template has "Draft | Approved | Blocked (ADR Required)".

### 3.3 Implementation planning

- **Exists, reuse.**
  - Skills `govkit-spec-planning`, `govkit-implementation-plan` and the UI variants.
  - Templates `plan.md` and `l5-plan.md`. Their fenced `evaluation_prediction` YAML
    block is already parsed by `check_plan_eval_prediction` (`cli/validate.py`
    ≈399). This is the precedent for a machine-readable block inside a
    Markdown artifact.
- **Missing.** Planning skills do not gate on preflight status; backend
  `govkit-spec-planning` does not read the preflight at all. There are no
  experiment increments, no reassessment step and no completion recheck. No
  feature-completion or reassessment skill exists.

### 3.4 Experiments, reassessment and evidence invalidation

- **Exists, reuse.**
  - Digest-based staleness: `change_conformance` `change:plan` (≈413–441)
    returns `stale-or-expanded-plan`.
  - Freshness: `pipeline_evidence._fresh` and `release_metadata.timestamp`.
  - Expiry semantics: transition `PolicyException.expires_at`. A missing
    observation time is UNKNOWN, as in
    `test_exception_without_observed_time_never_passes_expiry`.
  - `spec_closure.content_digest` and `spec_diff.voided_by` (which names
    `evidence_lineage`).
- **Missing.** Every experiment concept is missing: record, hypothesis,
  criteria, results, decision link, dependency-bound invalidation and evidence
  class.

### 3.5 Extension discovery and routing

- **Exists, reuse.**
  - Legacy discovery: `cli/extensions.py` `discover_extensions` and
    `validate_extension`.
  - Declarative install: `.govkit/packs/<id>/<digest>/` plus `.govkit/pack-lock.json`
    (`cli/pack_store.py`), with `verified_lock_document`.
  - `cli/maintenance_inventory.py` observes lock-owned files.
  - `skill_context.yaml` `extensions` facts.
- **Missing.**
  - No reader resolves resources from `.govkit/packs` for agents,
    preflight or validate.
  - Nothing detects a mixed legacy plus declarative install.
  - The SOAA pack snapshot omits its README and declares no checks.
- **Discrepancies, all confirmed:**
  - The six L5 backend entry files gate SOAA reading on `multi_agent: true`.
    The files are `claude-md/l5-backend-{api,cli}.md` L28,
    `agents-md/l5-backend-{api,cli}.md` L28 and
    `copilot-instructions/l5-backend-api.md` L31 /
    `l5-backend-cli.md` L25.
  - GenAI preflight hard-codes `extensions/llm-application/...` paths (L12–34).
  - The §2.6 wording parses "`capabilities`, `applies_to` per manifest", but those
    fields sit under `contract_sets[]`.

### 3.6 Check, evidence and conformance

- **Exists, reuse.**
  - `check_models.State` (PASS/FAIL/WARN/UNKNOWN/SKIPPED/NOT_APPLICABLE/WAIVED).
  - `check_runner.normalize`: PASS requires `executed` plus `local-check` or
    `tool-execution` origin.
  - Required non-pass states block `exit_code`.
  - Accepted `policy.required_checks` make a check required.
  - `change_conformance._artifact_check` (≈209) checks presence and bytes with
    origin `local-check` and an explicit limitation.
  - Pack checks are opt-in, with the evidence digest computed over
    exit code, stdout, stderr and arguments.
- **Missing.** No experiment-evidence check. The pack-check digest does not
  cover the bytes of a results file passed as an argument; a check script must
  print its input digest for the digest to bind it.
- **Adjacent, out of scope (record only):**
  - `migration.py` ≈389 counts `WAIVED` and `NOT_APPLICABLE` as no longer
    remaining.
  - ADR 0019 still reads "Proposed" although PR #219 merged.
  - `change-results.schema.json` embeds a copy of `workflow-plan`, and no test
    asserts their parity. Increment 6 adds that test because it edits both.

### 3.7 SOAA extension content

- **Exists, reuse.**
  - Five contract sets and 32 capability tokens.
  - Nine contracts plus `AGENT_RUNTIME_STACK.md` (`authority: defaults`).
  - Topic-based loading in the README.
  - `agent_guidance` for preflight, plan and validation.
  - `tests/test_skill_oriented_agent_architecture.py`, which asserts IDs, paths,
    phrases and neutrality.
- **Missing.**
  - An applicability matrix with an omission rule.
  - A single-agent path.
  - The separation between the LLM, SOAA and topology layers.
  - Experiment patterns.
  - A local case catalog.
  - A writer-map example.
  - A bounded record of source discrepancies (review S1, S2).
- **Discrepancy.** The core contract says "must assign all eighteen SOAA logical
  roles" and preflight "must map each role". Proposal D2 asks for a system-level
  map with per-feature deltas.

### 3.8 Packaging, CI and parity

- **Exists, reuse.**
  - `pyproject.toml` force-include maps `extensions` to `cli/ext` (Windows path
    budget of 116 UTF-16 units, `tests/test_wheel_windows_paths.py`).
  - The `wheel-smoke` job runs `tests/wheel_*_smoke.py` with `python -I` in a
    runtime-only venv.
  - Parity is enforced by `tests/test_agent_skills.py`,
    `tests/test_planning_skills_contract.py`, `tests/test_skill_names.py`,
    `tests/test_instruction_surface.py` and `PARITY_TEST.md` (13 skills × 3).
- **CI facts.**
  - Backend API/CLI consumer CI never runs `govkit validate`; only
    `data-common-gate.yml` and `ui-nextjs-quality-gate.yml` do. `data-common-gate`
    installs `govkit~=0.22.0` (precedent for a pinned install).
  - `quality-gate.yml` validates every `features/*/eval_criteria.yaml` with
    `check-jsonschema`.
  - `multi-agent-gate.yml` detects `multi_agent: true` by grep.

## 4. Discrepancy and defect register

| ID | Kind | Finding (verified) | Increment |
|---|---|---|---|
| R1 | **Defect, new** | `governance/backend/schemas/eval_criteria.schema.json` has `additionalProperties: false` and no `multi_agent`/`multi_agent_evaluation`. Uncommenting the starter's documented `multi_agent: true` fails jsonschema ("'multi_agent' was unexpected"). Consumer `quality-gate.yml` validates every feature with this schema, so the documented multi-agent route breaks CI. `tests/test_validate.py` multi-agent tests pass only because no schema is installed in their temp tree | 1 |
| R2 | **Defect, new** | `cli/skill_context.py` `_extension_facts` (≈154–170) reads top-level `manifest.get("capabilities")`; tokens live under `contract_sets[]`, so `extensions[].capabilities` is always `[]` | 1 |
| R3 | Drift | `features/starter_{backend,cli}_l5/architecture_preflight.md` lack §15 and number Final Status as §15 (template: §16) | 1 |
| R4 | Stale names | `cli/cmd_init.py` L139–143 prints `/architecture-preflight`, `/genai-preflight`, `/spec-planning`; `l5-architecture-preflight.md` L228 `/multi-agent-design`; `features/starter_data/{plan.md L4, architecture_preflight.md L3}` | 1 |
| R5 | Gap | No machine-readable preflight outcome; validate never reads status; vocabulary inconsistent (§3.2) | 2–5 |
| R6 | Gap | Planning skills do not gate on preflight outcome; no reassessment/completion step | 4 |
| R7 | Routing | SOAA reading conditioned on `multi_agent: true` in six L5 entry files; GenAI section 6 trigger is broader (proposal D7, review 3.6) | 8 |
| R8 | Discovery | Declarative resources invisible to preflight/agents; README omitted from SOAA pack snapshot; no mixed-copy detection (proposal D5, review P4) | 7, 9 |
| R9 | Evidence | Pack-check evidence digest does not cover result-file bytes | 10 (script prints input digest) |
| R10 | Docs | CLAUDE.md and `scripts/README.md` say starters omit `plan.md`/`architecture_preflight.md`; every starter ships both | 11 |
| R11 | Source | Metadata key spelling/profile ID (S1), instruction hierarchy, missing explicit prohibited-access term (S2), decision mapping | 9 (bounded) |
| R12 | Proposal vs code | Proposal says CI multi-agent topology "detects `multi_agent: true`" — confirmed; it also implies the declaration is usable today — it is not schema-valid (R1) | 1 |

## 5. Separating LLM, SOAA and multi-agent applicability

These are three independent layers. A feature may need any combination of them.
A single agent that uses governed runtime skills needs SOAA without topology.

| Layer | Applies when the feature… | Guidance | Machine-checked signal today | Phase A change |
|---|---|---|---|---|
| LLM application | calls language models | `llm-application` contracts; `eval_criteria.yaml` `mode: llm`; request `impacts.llm` → `llm-evaluation` capability | `mode: llm` (validate L5, eval-gate); `impacts.llm` (request plan) | Keep. Instructions find contracts in either install root (I8) |
| SOAA | uses governed runtime skills, an adaptive agent loop, or their control boundaries, **including one agent with fixed skills** | SOAA contracts + applicability record in the preflight | None (no flag); declarative selection by capability token (e.g. `governed-agent-runtime`) | Behavior-based instruction trigger (I8); applicability block in preflight via SOAA template (I9); opt-in extension check (I10). **No new eval_criteria flag** |
| Multi-agent topology | coordinates multiple agents through delegation, handoff or adaptive parallel work | `agent_topology.md`, `govkit-multi-agent-design` | `multi_agent: true` (validate topology checks, both `multi-agent-gate.yml`) | Make the declaration schema-valid (I1); trigger unchanged; must never become inapplicable silently |

Value Builder illustrates the separation. Its 2–3 discovery skills do not make it multi-agent. If its
runtime calls models and governed skills, the LLM and SOAA layers apply; topology
applies only if its actual runtime coordinates multiple agents.

## 6. Key design decisions

Each decision is resolved from repository evidence. ADR 0020 (Increment 2)
records KD-1 to KD-8; KD-9 to KD-13 are recorded in their increments.

- **KD-1 — One optional experiment record per feature.**
  - The record is `features/<feature>/experiments.yaml`, validated by schema
    `experiment-set` v1 (`governance/schemas/experiment-set.schema.json`).
  - It is not added to `L4_REQUIRED_ARTIFACTS`. It is required only when a
    preflight outcome or request references it.
  - Ordinary changes inside established boundaries create no record.
  - A single file keeps validation and review simple. Experiment IDs
    (`EXP-001`…) are unique within the file.
- **KD-2 — Machine-readable preflight outcome as a fenced YAML block.**
  - `architecture_preflight.md` gains a fenced `preflight_outcome:` block,
    following the `evaluation_prediction` precedent in `plan.md`. It is
    validated by schema `preflight-outcome` v1.
  - Status values are `approved-for-planning`, `experiment-required`,
    `adr-required` and `blocked`. Human-readable status lines stay.
  - **If the block is absent and no record exists, validate emits nothing new.**
    Existing features therefore keep byte-identical output.
- **KD-3 — One pure assessor, two adapters, no new command or skill.**
  - `cli/experiments.py` is pure. It parses, assesses and reports findings,
    and takes digests and the clock as injected inputs.
  - `cli/experiment_store.py` performs bounded, contained, no-symlink reads.
  - Two existing surfaces consume it: `govkit validate` (legacy feature
    folders) and `change_conformance` (declarative). Existing skills gain the
    workflow steps; no new skill is added, so `PARITY_TEST.md` is unchanged.
    The only CLI additions are flags on existing commands: `validate --only
    experiments` and `extension list --installed`.
- **KD-4 — Finding classes map to existing states.**

  | Finding class | Examples | `govkit validate` | Change conformance |
  |---|---|---|---|
  | error | schema or ID violations, `status-contradiction`, `adopt-after-failure`, `stale-reliance`, evidence digest mismatch | FAIL | FAIL |
  | outstanding | `experiment-required` not yet reassessed, experiment planned or running, failed without a decision, inconclusive | WARN (FAIL with `--strict`) | UNKNOWN |
  | unknown | unverifiable digest (missing, oversized or symlinked file), expiry set but no observation time | WARN (FAIL with `--strict`) | UNKNOWN |

  No state in this mapping ever produces PASS for missing, stale, failed or
  outstanding evidence.
- **KD-5 — Invalidation by recorded dependency digests.**
  - Each experiment lists `depends_on` entries. The kinds are requirement,
    skill, policy, interface, runtime, implementation and catalog, each with a
    `path` and a `sha256:` digest.
  - A result also binds:
    - `criteria_digest`, over the acceptance criteria at result time;
    - `inputs_digest`, over `depends_on` at result time;
    - an optional `expires_after_days`.
  - Any mismatch makes the experiment **stale**. File-level digests are
    conservative: any edit invalidates. Scenario-level digests via
    `spec_closure` are a deferred refinement.
  - The rule is offline and git-independent.
  - Re-pinning digests without re-running the experiment is detectable as
    `inputs-changed-after-result`, but deliberate forgery is not. The
    limitation text says so.
- **KD-6 — Evidence class is explicit.**
  - Each experiment declares `required_evidence_class`: `application` or
    `synthetic-fixture`. Each result declares the class it actually has.
  - `application` satisfies either requirement. `synthetic-fixture` satisfies
    only `synthetic-fixture`.
  - Rendered output always shows the class.
- **KD-7 — Decisions cannot weaken requirements.**
  - Decision outcomes are `adopt`, `revise-design`, `reject-approach`,
    `narrow-supported-behavior` and `rerun`.
  - `adopt` requires the derived state `passed`.
  - `narrow-supported-behavior` requires a `requirement_change` reference to an
    accepted requirement change. Because changed requirement files are recorded
    dependencies, the experiment then goes stale and needs reassessment.
  - The schema has no waiver field. A preflight may rely only on passed, fresh,
    adopted experiments, each bound by `result_digest`. Reliance may cross
    features: a preflight may name another feature's record path, which is how
    evidence is reused.
- **KD-8 — Declarative linkage reuses references and artifacts.**
  - The request gains a new reference kind, `experiment`.
  - When an experiment reference is present:
    - the plan adds artifact `experiment-record`;
    - the plan escalates `defect` and `bounded` to `full-feature`, with a
      non-blocking decision `experiment-escalated`;
    - change conformance's existing `artifact:<id>` path validates the
      records semantically.
  - The `architecture-preflight` artifact check honors a declared outcome
    block. No new check prefix and no new policy engine are introduced.
  - Plans and reports for existing inputs stay byte-identical.
- **KD-9 — One read-only view of installed extensions.**
  - `cli/extension_inventory.py` merges legacy `extensions/*/manifest.yaml`
    with lock-verified `.govkit/packs/<id>/<digest>/manifest.yaml`.
  - It reports repo-relative contract paths, the source and verification
    status, and conflicts.
  - It feeds `govkit extension list --installed`, `skill_context.yaml` and the
    `legacy:extensions` check. It never migrates or deletes anything.
  - Request-plan guidance is unchanged, so plan identity is unaffected.
- **KD-10 — SOAA 0.2.0 keeps its identities.**
  - Pack ID, the five contract-set IDs, the 32 capability tokens, the nine
    contract paths, `implementation_profiles` and `multi_agent: true` are
    preserved.
  - An explicit `capability_pack` block declares the README (advisory), new
    advisory docs, template, catalog and an opt-in check (`required: false`).
    A test keeps `provides` equal to the pack ID plus every contract-set token.
  - New guidance is advisory, not new contract sets.
  - Compatibility: a profile pinning version `0.1.0` resolves to
    `unavailable-pin` after upgrade. This is documented under CHANGELOG
    *Changed*. No bundled example pins SOAA.
- **KD-11 — SOAA routing stays behavior-based; topology keeps `multi_agent`.**
  - Phase A adds no SOAA flag to `eval_criteria.yaml`.
  - The machine-readable SOAA applicability lives in the SOAA template's
    `soaa_applicability:` block inside the preflight. Only the extension's
    opt-in check reads it.
- **KD-12 — Payload parity.**
  - Every agent payload edit lands for claude-code, codex and copilot together,
    with byte-identical shared blocks. Agent-specific invocation prefixes
    (`/`, `$`) are the only differences.
  - Agent-neutral pack skills stay single-sourced under `extensions/`.
- **KD-13 — Versioning and release.**
  - Changes land under `[Unreleased]`, with SOAA bumped to 0.2.0 and
    `application-governance` to 1.2.0 (its skill text changes).
  - The release number and publication are the user's decision at handoff.
    The recommendation is 0.23.0, delivered as a locally built wheel for the
    pilot.

## 7. Increment overview and dependencies

| # | Increment | Maps to | Depends on | Can run in parallel with |
|---|---|---|---|---|
| 0 | Land the preserved manifest-validation fix | A0 | — | — |
| 1 | Routing and context compatibility defects | A3 | 0 | 2 |
| 2 | Experiment record and preflight-outcome contract | A1 | 0 | 1 |
| 3 | Validator, installed schemas and consumer CI | A1/A4 | 2 | 7 |
| 4 | Backend/CLI/data agent payload for the development loop | A1 | 3 | 6, 7 |
| 5 | UI preflight outcome alignment (deferrable, see U2) | A1 | 4 | 6–10 |
| 6 | Declarative request planning and change conformance | A1/A4 | 2 | 3, 4, 7 |
| 7 | Installed extension inventory and mixed-copy detection | A3 | 1 | 2–6 |
| 8 | Routing alignment in agent payload | A3 | 4, 7 | 6 |
| 9 | SOAA extension 0.2.0 refinement | A2 | 4, 7, 8 | 6 |
| 10 | SOAA applicability coverage check | A4 | 2, 9 | 6 |
| 11 | Installed-package acceptance and pilot handoff | A5 | 3, 4, 6–10 (and 5 if U2 requires) | — |

```
0 ─┬─ 1 ── 7 ──┐
   │           ├─ 8 ── 9 ── 10 ─┐
   └─ 2 ─┬─ 3 ── 4 ──┘           ├─ 11
         │         └─ 5 (opt) ───┤
         └─ 6 ───────────────────┘
```

## 8. Increments

### Increment 0 — Land the preserved manifest-validation fix (A0)

1. **Outcome.** Malformed legacy extension manifests can no longer receive a
   structural PASS. Duplicate YAML keys and aliases are rejected, and a
   malformed `description` produces a warning instead of a crash. This is
   already implemented in the working tree.
2. **Scope / exclusions.**
   - Scope: commit the existing four-file change unchanged. Commit the proposal
     docs, archive and this plan as documentation.
   - Exclusions: no further code; no atomic `extension add` gate; no worker
     integration.
3. **Files.**
   - Code and tests: `cli/extensions.py`, `tests/test_extensions.py`,
     `tests/test_conformance.py`, `CHANGELOG.md`.
   - Documentation: `plans/SOAA_EXTENSION_LIGHTENING_PLAN.md`,
     `plans/SOAA_ARCHITECTURE_AND_GOVKIT_REVIEW.md`, `plans/archive/`, this file.
4. **Design / compatibility.**
   - Previously tolerated malformed manifests now report issues. All seven
     bundled packs validate cleanly (verified by `validate_extension` returning
     `[]`).
   - Warn-versus-strict policy is unchanged.
5. **Steps.**
   1. Review `git diff`.
   2. Run the focused tests and the fast tier.
   3. Run scoped Ruff on `cli/extensions.py` only.
   4. Create a branch, then commit:
      - `fix(extensions): validate legacy manifests with the shared schema`;
      - `docs(plan): add SOAA Phase A plan, review and archived draft`.
   5. Run the Qodo review; open a PR per the standing instruction.
6. **Tests.** The existing 18 regressions are recorded red before the fix in
   review §8, plus `test_malformed_extension_manifest_cannot_report_pass`.
7. **Verify.**
   ```bash
   pytest tests/test_extensions.py tests/test_conformance.py tests/test_cmd_extension.py \
     tests/test_skill_oriented_agent_architecture.py tests/test_llm_application.py \
     tests/test_capability_packs.py -q
   ruff check cli/extensions.py && ruff format --check cli/extensions.py
   ./run_tests -q
   ```
8. **Completion evidence.** Commit SHAs, focused/fast counts in the ledger, and
   the Qodo result recorded.
9. **Dependencies / decisions.** None. Whether this lands as its own PR is the
   user's standing instruction; a separate PR is recommended.

### Increment 1 — Routing and context compatibility defects (A3, partial)

1. **Outcome.**
   - A feature that follows the documented multi-agent route passes consumer
     schema validation.
   - `.govkit/skill_context.yaml` lists real extension capability tokens.
   - Init output and templates name installed skills.
   - L5 starters match the governed template structure.
2. **Scope / exclusions.**
   - Scope: R1–R4 only.
   - Exclusions: no trigger-semantics change (Increment 8); no new
     declarations beyond those the starter already documents.
3. **Files.**
   - `governance/backend/schemas/eval_criteria.schema.json`: add
     `multi_agent` (boolean) and `multi_agent_evaluation`.
     - `multi_agent_evaluation` is an object requiring `topology_validated` and
       `system_prompt_governed` (booleans), with optional
       `cross_agent_coherence` and `orchestrator_routing_accuracy`. Each optional
       entry is `{score: integer 1–5 | null, evidence: string}`.
     - `additionalProperties: false` throughout.
     - Add an `if/then` rule: `multi_agent_evaluation` requires
       `multi_agent: true`.
     - Align field names with `governance/schemas/evaluation_prediction.schema.json`
       L103–123 and with the starter comment in
       `features/starter_backend_l5/eval_criteria.yaml` L85–98.
   - `cli/skill_context.py` `_extension_facts`: flatten
     `contract_sets[].capabilities` in manifest order, deduplicated. Leave the
     other fields unchanged.
   - `cli/cmd_init.py` L139–143: use the installed `govkit-` names. Use the
     agent-specific invocation if the marker identifies the agent; otherwise
     use neutral wording ("the `govkit-architecture-preflight` skill").
   - Neutral `govkit-` skill names in:
     - `governance/backend/templates/l5-architecture-preflight.md` L228;
     - `features/starter_data/plan.md` L4;
     - `features/starter_data/architecture_preflight.md` L3.
   - `features/starter_backend_l5/architecture_preflight.md` and
     `features/starter_cli_l5/architecture_preflight.md`: add §15 (topology,
     with the "Not applicable — multi_agent not declared" default) and renumber
     Final Status to §16 with the template's lines.
   - Tests:
     - `tests/test_schemas.py`;
     - the existing skill-context test module (locate with
       `grep -ln _extension_facts tests/`);
     - `tests/test_agent_skills.py`, which gets a starter/template heading
       mirror like the existing `starter_data` test at ≈L182;
     - `tests/test_instruction_surface.py`, or a new
       `tests/test_skill_name_references.py`;
     - any test asserting `cmd_init` output (locate with
       `grep -ln "architecture-preflight" tests/`).
4. **Design / compatibility.**
   - The schema change is additive: every previously valid instance stays valid.
   - The `skill_context` field changes from always-empty to populated, and
     downstream skills only read it.
   - Starters change only new `govkit init` copies; starters are excluded from
     validate.
   - Init output text changes, so update its assertions.
5. **Steps (test first).**
   1. Write failing tests for R1–R4 and record the red run.
   2. Fix the schema.
   3. Fix `skill_context`.
   4. Fix the names.
   5. Align the starters.
   6. Add CHANGELOG `### Fixed` entries.
6. **Tests.**
   - **Positive:**
     - The L5 starter with its multi-agent block programmatically uncommented
       validates.
     - Both existing starters still validate.
     - The SOAA manifest yields exactly its 32 tokens in contract-set order.
   - **Negative:**
     - `multi_agent: "yes"` is rejected.
     - `multi_agent_evaluation` without `multi_agent: true` is rejected.
     - An unknown key under `multi_agent_evaluation` is rejected.
     - An unknown top-level key is still rejected.
     - `llm-evaluation` (no contract sets) yields `[]`.
     - A malformed manifest is still skipped.
     - No governed template or starter contains an unprefixed
       `/architecture-preflight`, `/genai-preflight`, `/spec-planning` or
       `/multi-agent-design`.
     - The L5 starter `## N.` heading sequence equals the template's.
7. **Verify.**
   ```bash
   pytest tests/test_schemas.py tests/test_validate.py -k "eval_criteria or multi_agent or MultiAgent" -q
   pytest tests/test_agent_skills.py tests/test_instruction_surface.py tests/test_govkit.py -q
   pytest -k parity -q
   ruff check cli/skill_context.py cli/cmd_init.py && ruff format cli/skill_context.py cli/cmd_init.py
   ```
8. **Completion evidence.** Red/green runs for each defect; schema validation
   of the uncommented starter; CHANGELOG entries.
9. **Dependencies / decisions.** Depends on Increment 0. No open decisions.

### Increment 2 — Experiment record and preflight-outcome contract (A1 core)

1. **Outcome.** A versioned record expresses:
   - the material uncertainty, hypothesis, affected decisions and protected
     requirements;
   - scope, permitted effects, conditions, oracle and acceptance criteria;
   - limits and dependencies;
   - results, evidence class and decision.

   A pure assessor derives each experiment's effective state and whether a
   preflight outcome's reliance on experiments is current. This is a library
   and contract only; no user-facing command changes.
2. **Scope / exclusions.**
   - Scope: schemas, pure module, bounded I/O adapter, examples, ADR and
     contract documentation.
   - Exclusions: validate, conformance and payload integration; scenario-level
     digests; execution of experiments.
3. **New files.**
   - `governance/schemas/experiment-set.schema.json`
   - `governance/schemas/preflight-outcome.schema.json`
   - `cli/experiments.py` (pure)
   - `cli/experiment_store.py` (I/O)
   - `governance/examples/experiments/` (README plus fixtures):
     - `established-boundary` (S1)
     - `experiment-required`
     - `failed-then-revised`
     - `passed-and-relied-upon`
     - `stale-after-requirement-change`
     - `synthetic-insufficient-class`
   - `tests/test_experiments.py`
   - `tests/test_experiment_store.py`
   - `plans/decisions/0020-architecture-experiments.md` (Proposed; accepted on
     merge, matching repository ADR practice)
   - `docs/ARCHITECTURE_EXPERIMENTS.md` (contract and claim boundary; the
     usage guide is completed in Increment 11)
4. **Design.**

   Record shape (`kind: experiment-set`, `schema_version: 1`,
   `additionalProperties: false` throughout):

   ```yaml
   schema_version: 1
   kind: experiment-set
   feature: discovery-skill-selection
   experiments:
     - id: EXP-001                      # ^EXP-[0-9]{3,}$, unique
       title: Single-agent discovery skill selection
       uncertainty: Can trusted code admit, select and fence 3 skills without model-owned authority?
       hypothesis: Admission before ranking plus null choice keeps activation controls intact.
       decisions_affected:              # kind: preflight-section | adr | contract | plan-increment
         - {kind: preflight-section, reference: features/discovery-skill-selection/architecture_preflight.md}
       requirements:                    # accepted requirements that must remain intact
         - {path: features/discovery-skill-selection/acceptance.feature, digest: "sha256:…"}
       scope:
         paths: [src/runtime/selection]
         permitted_effects: none        # none | local-reversible | fixture-external
         excluded: [real external mutation]
       conditions: [deterministic fixture catalog, model adapter mocked]
       oracle: deterministic-test       # deterministic-test | evaluation | measurement | review
       required_evidence_class: application   # application | synthetic-fixture
       acceptance_criteria:
         - {id: AC-1, statement: Revoked release is never activated, threshold: "0 activations in 50 cases", refs: [GK-SOAA-04]}
       limits: {budget: "2 days", stop_when: [authority counterexample], expires_after_days: 60}
       depends_on:                      # kind: requirement|skill|policy|interface|runtime|implementation|catalog
         - {kind: skill, path: skills/discovery-interview/SKILL.md, digest: "sha256:…"}
       status: passed                   # planned|running|passed|failed|inconclusive|withdrawn
       result:
         observed_at: "2026-11-02T10:00:00Z"
         revision: 3f2c…               # optional git SHA
         evidence_class: application
         criteria_digest: "sha256:…"
         inputs_digest: "sha256:…"
         criteria:
           - {id: AC-1, outcome: pass, evidence: [{path: build/eval/ac1.json, digest: "sha256:…", producer: test-run}]}
         summary: …
         limitations: [single fixture catalog]
       decision: {outcome: adopt, reference: adr/0003-skill-admission.md, recorded_at: "2026-11-02T12:00:00Z"}
   ```

   Preflight outcome block, inside `architecture_preflight.md`:

   ```yaml
   preflight_outcome:
     status: experiment-required        # approved-for-planning | experiment-required | adr-required | blocked
     reason: Untested selection boundary for three discovery skills
     experiments: [EXP-001]             # required, non-empty iff experiment-required
     relies_on:                         # for approved-for-planning supported by experiments
       - {experiment: EXP-001, record: features/x/experiments.yaml, result_digest: "sha256:…"}
   ```

   **Assessor API.**
   - `parse_experiment_set(doc)` and `parse_preflight_outcome(markdown)`. Exactly
     one block is allowed; it is parsed with the strict `parse_document`, so
     duplicate keys and aliases are rejected.
   - `assess(outcome, sets, *, read_digest, now)` returns an
     `ExperimentAssessment(findings, experiments, outcome)` with the properties
     `invalid`, `outstanding` and `ready_for_completion`.
   - Each finding carries a code, a class (error, outstanding or unknown), the
     experiment, a message and a location.

   **Derived states.** `passed` holds only when all of the following are true:

   | Condition | Finding if it fails |
   |---|---|
   | Every criterion has exactly one result, and each result is `pass` | `missing-criterion-result`, `unknown-criterion`, `duplicate-criterion-result` |
   | Evidence files exist and match their digests | `missing-evidence`, `evidence-digest-mismatch` |
   | The evidence class is sufficient | `insufficient-evidence-class` |
   | `criteria_digest` matches the current criteria | `criteria-changed-after-result` |
   | `inputs_digest` matches the current `depends_on` | `inputs-changed-after-result` |
   | Every dependency digest matches | `stale-dependency`, naming the kind and path |
   | The result has not expired | `expired`, or `expiry-unverifiable` (unknown) when the clock is absent |

   Other derived states:
   - A declared state that differs from the derived state is an error
     (`status-contradiction`).
   - Failed, inconclusive or stale states without a decision are `outstanding`.
   - `adopt` on a non-passed experiment is `adopt-after-failure`.
   - `narrow-supported-behavior` without `requirement_change` is an error.
   - Each `relies_on` entry must be passed, fresh and adopted, and its
     `result_digest` must match. A mismatch is `stale-reliance`, an error.
   - `experiment-required` with listed IDs is `outstanding`.
   - An unknown listed ID is `unknown-experiment`.

   **Digests and bounds.**
   - `result_digest` is computed over `canonical_json(result)`. Digests use the
     form `sha256:<hex>` and reuse `schema_validation.content_digest` and
     `canonical_json`.
   - Bounds: at most 64 experiments, 64 criteria, 64 dependencies and 64
     evidence entries per criterion.
   - Each hashed file is limited to 8 MiB; a larger file is unverifiable, so
     its finding class is unknown.
   - Paths must be literal and repo-relative: no globs, no `..`, no absolute
     paths and no symlink traversal. Reuse the containment semantics of
     `pack_loading.contained_file` / `workflow_store._source_refs`.
5. **Compatibility.** New files only; no existing behavior changes.
6. **Steps (test first).**
   1. Draft ADR 0020 covering KD-1 to KD-8 and the limits.
   2. Write the schemas and example fixtures.
   3. Write failing tests.
   4. Implement `cli/experiments.py`, then `cli/experiment_store.py`.
   5. Write the contract section of `docs/ARCHITECTURE_EXPERIMENTS.md`.
7. **Tests.** All tests are synthetic tooling tests.
   - **Schema:**
     - Valid examples pass.
     - Unknown keys, a bad ID pattern, duplicate experiment IDs, an absolute or
       `..` path, a glob and over-limit arrays are each rejected.
   - **Assessor** (one negative test per finding code, plus parametrized
     dependency kinds):
     - `established-boundary` produces no findings.
     - `experiment-required` is outstanding.
     - Failed plus `adopt` is an error.
     - Failed plus `revise-design`, followed by a passed EXP-002 and
       `relies_on` EXP-002, is ready.
     - Editing the acceptance file after the result makes the experiment stale,
       and `relies_on` then produces `stale-reliance`.
     - A synthetic result with the application requirement is not passed.
     - Expiry with no clock is unknown.
     - Re-pinning `depends_on` without re-running produces
       `inputs-changed-after-result`.
   - **Determinism:** identical inputs produce identical outputs.
   - **Store:**
     - No writes occur (snapshot before and after).
     - A symlinked evidence path is unverifiable.
     - An oversized file is unverifiable.
     - A missing record yields a clear finding, not an exception.
     - `relies_on` can read a record in another feature.
   - **Examples:** every bundled example produces the expected derived states,
     listed in an expectations table in the test.
8. **Verify.**
   ```bash
   pytest tests/test_experiments.py tests/test_experiment_store.py tests/test_schemas.py -q
   ruff check cli/experiments.py cli/experiment_store.py && ruff format cli/experiments.py cli/experiment_store.py
   ```
9. **Completion evidence.** Every finding code is covered by a red/green
   negative test; the examples replay; ADR 0020 is in *Proposed* state.
   **Decision:** none open. Scenario-level requirement digests are deferred
   (§13).

### Increment 3 — Validator, installed schemas and consumer CI (A1/A4)

1. **Outcome.**
   - `govkit validate` reports the preflight outcome and experiment evidence for
     features that declare them. Errors and stale reliance FAIL; outstanding or
     unknown evidence WARNs, or FAILs with `--strict`.
   - Features declaring neither see no new output.
   - New schemas install into consumer projects.
   - The GitHub and Azure quality gates enforce errors when records or outcome
     blocks exist.
2. **Scope / exclusions.**
   - Scope: CLI, manifests and CI templates.
   - Exclusions: agent prose (Increment 4), UI variants (Increment 5) and the
     declarative path (Increment 6).
3. **Files.**
   - `cli/validate.py`:
     - add `check_architecture_experiments(feature_dir, *, strict, now)` and
       register it in `_build_checks` for L4 and L5, for every project type;
     - render each finding as one result line;
     - when neither a block nor a record exists, return no results.
   - `cli/cmd_validate.py`: add `--only experiments`, which runs only these
     checks across features, with the same exit semantics. `--strict` now also
     promotes outstanding and unknown experiment findings.
   - `agents/{claude-code,codex,copilot}/manifest.json`: add
     `governance/schemas/experiment-set.schema.json` and
     `preflight-outcome.schema.json` to the governed lists for api/cli at L4
     and L5 and for data at L4. Follow the existing
     `governance/schemas/fix_record.schema.json` entries.
   - `ci/github/quality-gate.yml` and `ci/azure/quality-gate.yml`: add job/stage
     **Architecture experiment evidence**.
     1. Detect non-starter `features/*/experiments.yaml`, or a
        `preflight_outcome:` line in a non-starter
        `features/*/architecture_preflight.md`.
     2. If none is found, print the skip reason and exit 0.
     3. Otherwise run `python -m pip install govkit~=<release>` and then
        `govkit validate --target . --only experiments`. Follow the
        `data-common-gate.yml` pattern.
   - `ci/README.md`: add a section on the gate, strict mode for feature
     completion, and the pin update on release.
   - Tests:
     - `tests/test_validate.py`: new `TestArchitectureExperimentValidation`.
     - `tests/test_govkit.py`: schemas installed per variant, for all three
       agents.
     - The existing CI composition and pin tests
       (`tests/test_ci_gate_composition.py`,
       `tests/test_ci_govkit_dependency.py`).
4. **Design / compatibility.**
   - Output for features without the new artifacts must be byte-identical.
     Verify this with a golden captured from the baseline before the change.
   - `--strict` gains a new promotion that applies only to new artifacts.
   - The CI job is new and skips itself when the artifacts are absent.
   - Its pin must match the release that contains `--only` (U3). Until
     release, `test_ci_govkit_dependency.py` governs the pin form.
   - The CI job is **non-strict** on PRs, so experimentation PRs are not
     blocked by outstanding work while errors and stale reliance still fail.
     Feature completion uses `govkit validate --strict`, as documented in the
     skills (Increment 4).
5. **Steps (test first).**
   1. Capture the validate-output golden for the existing L4/L5 fixtures.
   2. Write failing validator and manifest tests.
   3. Implement the check, the flag and the manifests.
   4. Write the CI templates for both providers.
   5. Update `ci/README.md`.
6. **Tests.** All use synthetic records.
   - Features with neither artifact match the golden.
   - `approved-for-planning` with no experiments passes.
   - `experiment-required` with a planned experiment WARNs, and `--strict` makes
     it FAIL with exit 1.
   - A malformed block FAILs.
   - Two blocks FAIL.
   - A stale `relies_on`, after editing `acceptance.feature`, FAILs with
     "reassessment required".
   - A record present without a block WARNs.
   - A synthetic result against an application requirement is not passed.
   - `starter_*` is skipped.
   - `--only experiments` ignores unrelated failing checks: a feature missing
     Gherkin still exits 0.
   - The CI templates for both providers carry the identical detection
     expression, skip path and pin form.
   - Every relevant manifest variant installs both schemas, for all three
     agents.
   - A real `cmd_apply` at L5 api, followed by a feature with records, makes
     validate read the installed schemas (fast tier, following
     `tests/test_llm_application.py:224`).
7. **Verify.**
   ```bash
   pytest tests/test_validate.py -k "Experiment or experiment" -q
   pytest tests/test_govkit.py tests/test_schemas.py tests/test_ci_gate_composition.py tests/test_ci_govkit_dependency.py -q
   pytest -k parity -q
   ruff check cli/validate.py cli/cmd_validate.py && ruff format cli/validate.py cli/cmd_validate.py
   ./run_tests -q
   ```
8. **Completion evidence.** The golden is unchanged; the negative cases are red
   then green; the CI templates for both providers are reviewed side by side;
   the fast tier is green.
9. **Dependencies / decisions.** Depends on Increment 2. The CI pin follows U3.

### Increment 4 — Backend/CLI/data agent payload for the development loop (A1)

1. **Outcome.** In all three hosts, coding agents follow requirements →
   preflight → experiment (only when needed) → implementation → evaluation →
   reassessment → completion.
   - Established boundaries take the short path.
   - Material untested assumptions yield `experiment-required` with bounded
     records.
   - Known violations still require an ADR or a narrower experiment.
   - Completion re-checks every accepted requirement and control.
2. **Scope / exclusions.**
   - Scope: backend api/cli (L4 and L5) and data.
   - Exclusions: UI (Increment 5); SOAA-specific content (Increment 9); routing
     triggers (Increment 8).
3. **Files.**
   - `governance/backend/templates/architecture_preflight.md`:
     - add `## 8.5 Architecture Uncertainty and Experiments`, an assumptions
       table with the columns *assumption | basis (accepted contract / ADR /
       fresh experiment / untested) | material? | action*;
     - in §9, add the "Experiment required" final-status option and the
       `preflight_outcome` block.
   - `governance/backend/templates/l5-architecture-preflight.md`: the same §8.5,
     with the block in §16. **No renumbering**, so the validate regexes for §10–§14 still match.
   - `governance/backend/templates/plan.md` and `l5-plan.md`:
     - *Experiment increments* guidance: experiments come first and touch only
       the experiment's permitted scope and effects;
     - a *Reassessment and completion* section covering `relies_on`, re-runs
       after material changes, and the re-check of all requirements and
       controls.
   - New `governance/backend/templates/experiments.yaml` (governed template,
     installed by the existing `governance/backend/templates/` entry).
   - Starters `features/starter_{backend,backend_l5,cli,cli_l5,data}/architecture_preflight.md`
     get §8.5 plus a block whose `status` is the placeholder
     `<approved-for-planning|experiment-required|adr-required|blocked>`. The
     placeholder is invalid on purpose, so an uncompleted copy FAILs validate,
     consistent with `nfrs.md` TBD handling.
   - Skills, for each of the three agents:
     - `backend/govkit-architecture-preflight`: new §6.5 *Uncertainty
       classification and outcome*, and output of the block.
     - `backend/govkit-genai-preflight`: unified status vocabulary including
       `experiment-required`; model-behavior uncertainty may require an
       evaluation experiment.
     - `backend/govkit-spec-planning`: read the outcome; while
       `experiment-required`, plan only experiment increments; never contradict
       the preflight's ADR decision.
     - `backend/govkit-implementation-plan`: experiment increments,
       reassessment, and completion via `govkit validate --strict`.
   - Rules, for each agent: `rules/generic/spec-compliance.md`. Completion
     requires a non-blocked, non-experiment-required outcome and no stale
     reliance.
   - Entry docs for L4/L5 api/cli and data, for each agent (`claude-md`,
     `agents-md`, `copilot-instructions`): add the lifecycle steps *Experiment
     (only if preflight says experiment-required)* and *Reassess*.
   - Tests:
     - `tests/test_agent_skills.py`: new byte-identical parity blocks.
     - `tests/test_planning_skills_contract.py`: behavior-contract block.
     - `tests/test_instruction_surface.py`.
     - `tests/test_artifact_contract_consistency.py`: the five-artifact
       contract is unchanged, and `experiments.yaml` is optional.
     - `tests/test_adr_contract_consistency.py`.
     - Starter mirror tests.
4. **Compatibility.**
   - Agent config is always overwritten on upgrade.
   - Governed templates are rewritten on upgrade, with user edits protected by
     the header hash.
   - Existing feature preflights are untouched and validate unchanged
     (Increment 3 golden).
   - The skill count is unchanged, so `PARITY_TEST.md` is unchanged.
5. **Steps (test first).**
   1. Write failing parity and content tests for each new block.
   2. Edit the templates, then the starters.
   3. Edit the skills, rules and entry docs for all three agents in one change.
6. **Tests.**
   - The §6.5 and plan-skill blocks are byte-identical across agents, with only
     invocation prefixes normalized.
   - Every skill reference resolves to an installed skill, per
     `test_instruction_surface`.
   - The starter preflight headings mirror the template's.
   - The placeholder status fails validate with the guidance message.
   - **Negative:**
     - Template prose may not instruct adopting a failed experiment, waiving a
       requirement, or labeling an untested design "aligned" to start a
       prototype. Implement this as phrase checks on prohibited wording.
     - A real L5 api apply for each agent installs the updated skills and the
       `experiments.yaml` template.
7. **Verify.**
   ```bash
   pytest tests/test_agent_skills.py tests/test_planning_skills_contract.py tests/test_instruction_surface.py \
     tests/test_artifact_contract_consistency.py tests/test_adr_contract_consistency.py tests/test_skill_names.py -q
   pytest -k parity -q
   pytest tests/test_govkit.py tests/test_maturity_model.py tests/test_validate.py -q
   ```
8. **Completion evidence.** A three-way agent diff showing only the expected
   prefixes; parity green; an apply for each agent shows the new content.
9. **Dependencies / decisions.** Depends on Increment 3. No open decisions.

### Increment 5 — UI preflight outcome alignment (A1, deferrable)

1. **Outcome.** React, Angular and Next.js features use the same outcome
   vocabulary, block and experiment workflow.
2. **Scope.**
   - Scope:
     - `governance/ui/templates/{architecture_preflight,plan}.md`;
     - `features/starter_ui*`;
     - the `govkit-ui-architecture-preflight`, `govkit-ui-spec-planning` and
       `govkit-ui-implementation-plan` skills, for each agent;
     - the UI entry docs;
     - the UI manifest governed schema entries.

     `ui-nextjs-quality-gate.yml` already runs validate, so no template change
     is needed beyond confirming its pin.
   - Exclusions: none beyond UI.
3. **Compatibility.** Map "Approved" to `approved-for-planning` and
   "Blocked (ADR Required)" to `adr-required` in prose. Existing UI preflights
   without a block are unaffected.
4. **Tests.** Mirror Increment 4 for UI: parity, starter mirror,
   `--only experiments` on a UI fixture, and the D016 database boundary
   unchanged.
5. **Verify.**
   ```bash
   pytest tests/test_agent_skills.py tests/test_planning_skills_contract.py tests/test_validate.py -k "ui or UI" -q
   pytest -k parity -q
   ```
6. **Completion evidence.** Parity green; a UI apply for each agent.
7. **Decision.** This increment is required before handoff only if the pilot
   feature is a UI project (U2). Otherwise record it as deferred in the ledger.

### Increment 6 — Declarative request planning and change conformance (A1/A4)

1. **Outcome.**
   - A request can link experiment records.
   - The plan leaves the short path (bounded or defect becomes full-feature) and
     requires `artifact:experiment-record`.
   - Actual-change conformance FAILs inconsistent or stale-relied-upon evidence
     and withholds PASS (UNKNOWN) for outstanding experiments.
   - `artifact:architecture-preflight` honors a declared outcome block.
   - Every existing request, plan and report is byte-identical.
2. **Scope / exclusions.**
   - Exclusions: no new impact key; no new check prefix; no change to guidance
     composition; no automatic execution of experiments.
3. **Files.**
   - Schemas:
     - `governance/schemas/workflow-request.schema.json`: add reference kind
       `experiment`.
     - `governance/schemas/workflow-plan.schema.json`: the embedded request and
       reference enums.
     - `governance/schemas/change-results.schema.json`: the embedded plan copy.
   - `cli/workflows.py`:
     - when any `experiment` reference exists, escalate `defect`/`bounded` to
       `full-feature` with the non-blocking decision `experiment-escalated`
       (never lowering `architecture`);
     - add the artifact `experiment-record` with reason *Validate referenced
       experiment records; never self-approve*.
   - `cli/workflow_store.py`: reuse the accepted-reference snapshot unchanged.
     Confirm `proposed`/`observed` authority handling matches the existing
     reference kinds.
   - `cli/change_conformance.py` `_artifact_check`:
     - `experiment-record` loads the referenced records through
       `experiment_store`, with `observed_at` as `now`, and maps findings per
       KD-4.
     - `architecture-preflight` additionally parses an outcome block when
       present. `experiment-required` is UNKNOWN and `blocked` is FAIL; an
       absent block behaves as before.
     - Evidence origin is `local-check`, with the limitation *Validates
       experiment records and their bound digests; does not authenticate
       execution or results*.
   - `cli/posture_change.py`: verify that no enumerations block the new
     artifact ID, with a test.
   - `extensions/application-governance/skills/govkit-request-planning/SKILL.md`
     (single agent-neutral source): add guidance for experiment references.
     Bump the manifest version to 1.2.0.
   - Examples and docs:
     - `governance/examples/workflows/requests/experiment.json` (eighth
       example), plus a fixture record in the consumer example.
     - `governance/examples/change-conformance/` (README and consumer).
     - `docs/REQUEST_WORKFLOWS.md`, `docs/CHANGE_CONFORMANCE.md`.
     - CLAUDE.md: "seven examples" becomes "eight".
   - Tests:
     - `tests/test_workflows.py` (expected stems: eight).
     - `tests/wheel_workflow_smoke.py`, `tests/wheel_change_smoke.py`.
     - `tests/test_change_conformance.py`, `tests/test_change_posture.py`.
     - New `tests/test_workflow_schema_parity.py`: the `change-results` plan
       equals `workflow-plan`, ignoring `$schema` and `title`.
     - Native-skill lock goldens under `tests/fixtures/` if the
       `application-governance` digest is pinned there (refresh deliberately,
       with a reviewed diff).
4. **Design / compatibility.**
   - The enum addition is additive.
   - The resolver output for inputs without `experiment` references is unchanged:
     - `resolver_version` stays 1;
     - the seven existing example plans are replayed and compared against a
       golden;
     - a saved plan from the baseline is replayed through the new code.
   - Changes to `experiments.yaml` change the plan evidence digest. With
     `--previous`, `change:plan` then reports `stale-or-expanded-plan`. This is
     intended: material change triggers reassessment.
   - Request references to records should omit `digest`. A declared digest
     makes every record edit a blocking `changed-reference`. Document this.
   - The `application-governance` version bump changes its digest, so profiles
     pinning 1.1.2 need a pin update. No bundled example pins it.
5. **Steps (test first).**
   1. Capture goldens for the seven plans and the change-conformance
      reports.
   2. Write the failing parity and negative tests.
   3. Make the schema changes.
   4. Change the resolver.
   5. Change the conformance mapping.
   6. Update the skill, examples, docs and smokes.
6. **Tests.**
   - **Positive:** the experiment example routes full-feature, is ready, and
     includes `artifact:experiment-record`. A passed, fresh, relied-upon record
     with a configured preflight PASSes that artifact, with a limitation.
   - **Negative:**
     - A bounded or defect preference plus an experiment reference never
       produces the short path.
     - A missing record file FAILs.
     - A stale dependency or `stale-reliance` FAILs.
     - An outstanding experiment is UNKNOWN and the exit code is 1.
     - A preflight with `experiment-required` is UNKNOWN.
     - A `blocked` preflight FAILs.
     - A tampered saved report cannot flip the artifact state
       (`parse_change_report` binding).
     - An unknown reference kind is still rejected.
     - A `waive_checks` field is still rejected.
     - Replay of the old plans is byte-identical.
     - The `change-results` copy equals `workflow-plan`.
     - Posture projection preserves the new required artifact.
7. **Verify.**
   ```bash
   pytest tests/test_workflows.py tests/test_workflow_review_regressions.py tests/test_change_conformance.py \
     tests/test_change_review_regressions.py tests/test_change_posture.py tests/test_cmd_conform.py \
     tests/test_workflow_schema_parity.py tests/test_capability_packs.py -q
   ruff check cli/workflows.py cli/change_conformance.py && ruff format cli/workflows.py cli/change_conformance.py
   ./run_tests -q
   ```
   Run the wheel smokes (`wheel_workflow_smoke.py`, `wheel_change_smoke.py`)
   with the procedure in §10.
8. **Completion evidence.** The goldens are unchanged; the new negative tests
   are red then green; the schema-parity test is green; both wheel smokes pass.
9. **Dependencies / decisions.** Depends on Increment 2. No open decisions.

### Increment 7 — Installed extension inventory and mixed-copy detection (A3)

1. **Outcome.** `govkit extension list --installed --target . [--json]` lists
   installed extension contract sets and resources from legacy and lock-verified
   declarative installs, with repo-relative paths, verification status and
   conflicts. Skill context and the `legacy:extensions` check use the same view.
2. **Scope / exclusions.**
   - Read-only.
   - Exclusions: no migration, deletion or deduplication; no request-plan
     guidance change.
3. **Files.**
   - New `cli/extension_inventory.py`. Its inward dependencies are `extensions`,
     `pack_store.verified_lock_document`, `pack_loading` and `paths`.
   - `cli/cmd_extension.py`: add `--installed`, `--target` and `--json` to
     `list`. Bundled listing remains the default.
   - New `governance/schemas/extension-inventory.schema.json` for the JSON
     output.
   - `cli/skill_context.py`: `extensions` facts gain the additive `root`,
     `source`, `status` and `conflicts` fields.
   - `cli/check_adapters.py` `extension_check`: a warning finding for conflicts.
     The check remains `required=False`.
   - `docs/CAPABILITY_PACKS.md`.
   - Tests: new `tests/test_extension_inventory.py`;
     `tests/test_cmd_extension.py`; the skill-context tests;
     `tests/test_conformance.py`.
4. **Design.**
   - Statuses:
     - `legacy`, with `validate_extension` findings attached;
     - `declarative-verified`;
     - `declarative-unverified`: the lock fails, and resources are reported
       but marked unusable.
   - Conflict kinds:
     - `legacy-and-declarative` (same ID in both roots);
     - `version-mismatch`;
     - `orphan-pack-directory` (pack directory not in the lock).
   - Resource paths are prefixed with the root. Order is deterministic.
   - **Compatibility:** the bundled listing is unchanged; `skill_context` fields
     are additive; the `legacy:extensions` state can move from PASS to WARN
     only for mixed installs.
5. **Steps (test first).**
   1. Build fixtures with a legacy-only install, a declarative-only install, a
      mixed install, a tampered lock and an orphan directory.
   2. Write the failing tests.
   3. Implement the inventory, then the command, then the consumers.
6. **Tests.**
   - A markerless declarative install lists SOAA contract paths under
     `.govkit/packs/…`.
   - A legacy install lists `extensions/…` paths.
   - A mixed install reports `legacy-and-declarative`.
   - A tampered lock is `declarative-unverified`, with no usable resources.
   - An orphan directory is reported.
   - `--json` validates against the schema.
   - The read-only snapshot is unchanged.
   - Malformed legacy manifests carry the Increment 0 diagnostics.
7. **Verify.**
   ```bash
   pytest tests/test_extension_inventory.py tests/test_cmd_extension.py tests/test_conformance.py tests/test_pack_store.py -q
   ruff check cli/extension_inventory.py cli/cmd_extension.py cli/skill_context.py cli/check_adapters.py
   ruff format cli/extension_inventory.py cli/cmd_extension.py cli/skill_context.py cli/check_adapters.py
   ```
8. **Completion evidence.** All five fixture topologies are covered; the
   read-only snapshot is unchanged.
9. **Dependencies / decisions.** Depends on Increment 1, whose `skill_context`
   fix this builds on. No open decisions.

### Increment 8 — Routing alignment in agent payload (A3)

1. **Outcome.** The three layers in §5 route independently in all three hosts.
   - SOAA guidance loads for one agent using governed runtime skills.
   - Topology stays tied to `multi_agent: true`.
   - LLM contracts load for model use.
   - Instructions find resources in either install root.
2. **Scope / exclusions.**
   - Exclusions: no new flag; topology enforcement in validate and CI is
     unchanged.
3. **Files.**
   - L5 entry docs, for each agent (`claude-md`, `agents-md`,
     `copilot-instructions`) and both `l5-backend-{api,cli}.md` variants
     (six files): replace the `multi_agent` condition on SOAA reading with the
     behavior trigger. Keep lifecycle step 0 for multi-agent topology.
   - `agents/*/skills/backend/govkit-genai-preflight/SKILL.md`:
     - locate `llm-application` and SOAA through
       `govkit extension list --installed`, or by scanning both roots;
     - keep section 6;
     - state the three layers explicitly.
   - `agents/*/skills/backend/govkit-multi-agent-design/SKILL.md` and the
     multi-agent rule sources (claude `rules/backend/multi-agent.md`, the codex
     `services/graphs/AGENTS.md` source, copilot `multi-agent.instructions.md`):
     use the installed-root wording.
   - §2.6 of `govkit-architecture-preflight` and `govkit-ui-architecture-preflight`
     (six byte-identical copies):
     - scan `extensions/*/manifest.yaml` and `.govkit/packs/*/*/manifest.yaml`;
     - prefer the verified CLI listing;
     - correct the field wording to `contract_sets[].capabilities` and
       `applies_to`;
     - halt on reported conflicts.
   - `governance/backend/templates/l5-architecture-preflight.md` §15: retitle
     *Agent Architecture*.
     - Item 15a, SOAA applicability, applies with one or more agents when
       governed runtime skills or an adaptive loop exist.
     - Item 15b, topology, applies only when `multi_agent: true`.
     - Keep the number 15 and the existing checklist items.
   - The L5 starters' §15.
   - The `features/starter_backend_l5/eval_criteria.yaml` header comment:
     installed-root wording for the contract path.
   - Tests:
     - New `tests/test_agent_routing.py`.
     - Update `tests/test_agent_skills.py` for §2.6 parity and required tokens:
       add `.govkit/packs`.
     - `tests/test_instruction_surface.py`.
     - The existing `TestMultiAgentValidation` cases.
4. **Compatibility.**
   - Topology checks are unchanged in validate and in both `multi-agent-gate.yml`
     files.
   - A feature that previously declared `multi_agent: true` still gets
     topology plus SOAA.
   - Features without the flag now get SOAA guidance when the behavior applies.
     That is additive guidance, not an enforcement change.
5. **Steps (test first).**
   1. Write the routing tests.
   2. Edit all agents' files in one change.
   3. Run the parity and surface tests.
6. **Tests.**
   - No L5 entry file conditions SOAA reading on `multi_agent`.
   - Every L5 entry file conditions topology on `multi_agent: true`.
   - LLM contract reading is conditioned on model use.
   - The text is identical across agents after prefix normalization.
   - No skill or rule hard-codes an `extensions/llm-application/docs` or
     `extensions/skill-oriented-agent-architecture/docs` path without the
     declarative alternative.
   - Validate:
     - a feature without `multi_agent` has topology not applicable;
     - with the flag, a missing `agent_topology.md` still FAILs;
     - with an **SOAA-only** declaration and no flag, topology is never
       silently required or passed. This is the negative case from review 3.6.
7. **Verify.**
   ```bash
   pytest tests/test_agent_routing.py tests/test_agent_skills.py tests/test_instruction_surface.py -q
   pytest tests/test_validate.py -k "MultiAgent or multi_agent" -q
   pytest -k parity -q
   ```
8. **Completion evidence.** A three-way diff of the six entry files; routing
   tests green.
9. **Dependencies / decisions.** Depends on Increments 4 (same files) and 7
   (listing command). No open decisions.

### Increment 9 — SOAA extension 0.2.0 refinement (A2)

1. **Outcome.** A team can apply SOAA proportionally:
   - a single agent with 2–3 fixed or model-selected skills has a clear,
     usable path;
   - the controls follow capabilities and consequences, not a maturity ladder;
   - omissions need verified evidence;
   - experiment patterns plug into the GovKit loop;
   - the extension's README and guidance are discoverable from declarative
     installs.
2. **Scope / exclusions.**
   - Exclusions: no contract-set ID, token or path changes; no new contract sets;
     no `agent_skills_rung`; no formal conformance mapping to the 206
     assertions; no runtime code.
3. **Files** (under `extensions/skill-oriented-agent-architecture/`; keep each
   new wheel member within the 116-unit path budget).
   - `manifest.yaml`:
     - `version: 0.2.0`;
     - an explicit `capability_pack` block, with:
       - `provides`: the pack ID plus all 32 tokens;
       - `resources`: the nine contracts (`contract`),
         `AGENT_RUNTIME_STACK.md` (`defaults`), `README.md` (`advisory`), the
         new docs (`advisory`), the template (`example`) and the catalog
         (`reference`);
       - `agents`: all three;
       - `checks`: added in Increment 10;
     - a `templates:` entry;
     - revised `agent_guidance` covering applicability, experiment-required and
       the three layers;
     - `govkit_min_version` per U3. Verify editable-install (`dev`) resolution.
   - `README.md`:
     - a *Start here* section for the single-agent path;
     - the three layers;
     - when preflight should say experiment-required;
     - the claim boundary (§1);
     - legacy and declarative install snippets.
   - New `docs/backend/architecture/SOAA_APPLICABILITY.md` (advisory): the D1
     matrix, the omission rule, unknown-is-unresolved, and the system-level
     writer and role map with per-feature deltas.
   - New `docs/backend/architecture/SOAA_EXPERIMENTS.md` (advisory):
     - the E1–E5 patterns and stopping conditions;
     - Value Builder discovery as an illustrative, unverified example;
     - mapping to `experiments.yaml` fields.
   - New `catalog/gk-soaa-cases.yaml`, an advisory catalog that is not
     normative SOAA. It holds GK-SOAA-01..16 plus the conditional cases, each
     with `applies_when` condition IDs from the D1 rows.
   - New `templates/preflight-soaa.md`: an applicability table plus a fenced
     `soaa_applicability:` block and writer-map rows.
   - Minimal, conservative edits to the existing contracts:
     - `SKILL_ORIENTED_AGENT_ARCHITECTURE.md`: roles are mapped once at system
       level, with per-feature changed rows. The applicability decision is
       added to the required preflight decisions. Minimum verification is
       selected by applicability, and omissions need evidence. Keep "Eighteen".
     - `SKILL_SELECTION_AND_ACTIVATION_CONTRACT.md` *Binding modes*:
       - fixed binding keeps admission, compatibility and revocation;
       - a model choosing from a fixed menu is selection, which keeps null
         selection.
     - `AUTHORITY_AND_APPROVAL_CONTRACT.md`: subtract prohibited access
       explicitly (review S2). The change is stricter, labeled as
       guide-aligned, and comes with an overlap example.
     - Add an instruction-precedence mapping note recording the discrepancy;
       no enforcement change.
     - `SKILL_CONTRACT.md`: record the dotted-key/profile-ID discrepancy (S1).
       Do **not** rename keys. Mark the compatibility claim blocked pending
       source.
     - Each contract's *Source alignment* section lists any open discrepancy.
   - Tests: `tests/test_skill_oriented_agent_architecture.py`.
4. **Compatibility.**
   - IDs, tokens, paths and existing phrases are preserved; all existing
     assertions stay.
   - The digest changes, and profiles pinning `0.1.0` need a pin update
     (CHANGELOG *Changed*).
   - Legacy `extension add` copies the whole folder, so new files appear for
     legacy installs too.
5. **Steps (test first).**
   1. Write failing tests:
      - `provides` parity;
      - the README declared and present in `load_pack`;
      - version 0.2.0;
      - new docs exist and are not contract sets;
      - the catalog is well-formed;
      - the single-agent path exists;
      - no rung vocabulary;
      - the prohibited-access term is present;
      - neutrality holds for the new docs.
   2. Edit the manifest, then the docs, then the contracts.
6. **Tests.**
   - **Kept:** the existing ID, path, phrase and neutrality assertions.
   - **New:**
     - `capability_pack.provides` equals the pack ID plus every token, and
       drift fails.
     - `load_pack` includes README, template and catalog with the declared
       kinds.
     - The catalog has 16 unique base IDs, every `applies_when` resolves to a
       known condition, and unknown condition IDs fail.
     - The README has a single-agent section and explicitly states that
       `multi_agent` is only for topology.
     - The negative test passes: no `agent_skills_rung`, `rung` or `maturity
       ladder` wording.
     - The new docs name no products from the neutrality list.
     - `tests/wheel_pack_smoke.py` still lists seven IDs and installs SOAA for
       each agent.
     - The Windows path-budget test passes.
7. **Verify.**
   ```bash
   pytest tests/test_skill_oriented_agent_architecture.py tests/test_extensions.py tests/test_capability_packs.py \
     tests/test_pack_store.py tests/test_cmd_extension.py tests/test_wheel_windows_paths.py -q
   ```
8. **Completion evidence.** A load-pack summary showing the README and new
   resources; the reconciliation register in the contracts; all tests green.
9. **Dependencies / decisions.** Depends on Increments 4, 7 and 8. **U1** (guide
   access) affects only exact wording of the S1/S2 notes; without it, keep the
   conservative stricter edits and the blocked-claim labels.

### Increment 10 — SOAA applicability coverage check (A4)

1. **Outcome.** An opt-in pinned pack check validates a feature's
   `soaa_applicability` block and reports whether a claimed set of local
   GK-SOAA cases is covered by passed experiment criteria.
   - Omissions require a reason, verified absent/disabled-interface evidence,
     an owner and a change trigger.
   - Unknown applicability never satisfies the check.
   - The check is optional until accepted policy lists it in
     `policy.required_checks`.
2. **Scope / exclusions.**
   - Exclusions:
     - no formal SOAA claim;
     - no execution of application tests;
     - no core engine changes;
     - experiment validity remains the core assessor's job, and a combined
       claim needs both checks.
3. **Files.**
   - New `extensions/skill-oriented-agent-architecture/checks/applicability.py`.
     It is a standalone script run with `python -I`, it may import `cli.*`
     from the installed GovKit, and its arguments are `--preflight`,
     `--experiments`, `--catalog` and `--cases`.
   - The `capability_pack.checks` entry
     `{id: soaa-applicability, path: checks/applicability.py, required: false}`.
   - The README and `SOAA_EXPERIMENTS.md` usage sections.
   - New `tests/test_soaa_applicability_check.py`.
   - `tests/wheel_pack_smoke.py`.
4. **Design.**
   - Exit codes:
     - 0: the block is valid and every claimed case is applicable or common
       and covered by a passed criterion `refs` with a sufficient evidence
       class;
     - 1: not satisfied;
     - 2: invalid input.
   - Stdout is canonical JSON containing the SHA-256 of every input file, the
     covered and uncovered cases, and the limitations. `pack_check` digests
     stdout, so the evidence binds the result-file bytes (R9) without changing
     the engine.
   - **Compatibility:** opt-in with `required: false`; legacy installs can run
     the script directly.
5. **Steps (test first).**
   1. Write failing tests over synthetic fixtures.
   2. Write the script.
   3. Add the manifest entry.
   4. Exercise it through `govkit pack check` and
      `govkit conform --execute-pack-check`.
6. **Tests.**
   - **Negative:**
     - An `unknown` condition exits 1.
     - N/A missing interface evidence, owner or trigger exits 1.
     - A cited case that is declared N/A exits 1.
     - An unknown or duplicate case ID exits 2.
     - A case covered only by a failed or synthetic-insufficient criterion
       exits 1.
     - A changed results file changes the stdout digest.
     - Through conformance:
       - when not executed, it is SKIPPED and does not satisfy a
         policy-required check;
       - with `required: false` and absent from policy, the check is advisory.
   - **Positive:**
     - A single-agent fixed-skill fixture (Value Builder-shaped, synthetic)
       covers GK-SOAA-01..09 with the remaining cases justified N/A.
7. **Verify.**
   ```bash
   pytest tests/test_soaa_applicability_check.py tests/test_pack_check.py tests/test_conformance.py -q
   ruff check extensions/skill-oriented-agent-architecture/checks/applicability.py
   ruff format extensions/skill-oriented-agent-architecture/checks/applicability.py
   ```
8. **Completion evidence.** Red/green runs for the negative cases; the
   conformance output shows advisory versus policy-required behavior.
9. **Dependencies / decisions.** Depends on Increments 2 and 9. No open decisions.

### Increment 11 — Installed-package acceptance and pilot handoff (A5)

1. **Outcome.** A wheel installed into a clean, runtime-only environment
   demonstrates the complete development loop for all six Phase A scenarios
   (§9). It covers both the legacy L5 api route and the declarative route, for
   all three agents, using synthetic results only. The user receives
   installation and pilot-start instructions.
2. **Scope / exclusions.**
   - Exclusions: publishing, tagging and merging (separate authorization); any
     Value Builder code.
3. **Files.**
   - New `tests/wheel_experiment_smoke.py`. It follows the pattern of the
     existing smokes:
     - `Path(module.__file__).is_relative_to(sys.prefix)`;
     - the CLI is run via `sys.executable -I -m cli.govkit`;
     - snapshots prove reads have no side effects;
     - each scenario prints `synthetic-fixture`.
   - `.github/workflows/test.yml`, `wheel-smoke` job: add one step.
   - `tests/test_change_pilot_environment.py`: import the new smoke if the
     pattern requires it.
   - Docs:
     - `docs/ARCHITECTURE_EXPERIMENTS.md`: complete the usage guide and the
       *Starting a consuming-project pilot* section.
     - `docs/CHANGE_CONFORMANCE.md` and `docs/CAPABILITY_PACKS.md`
       cross-links.
     - `CHANGELOG.md` `[Unreleased]`.
     - CLAUDE.md: a new *Architecture experiments* section, plus the R10
       correction about starters.
     - `scripts/README.md` (R10).
   - ADR 0020: final review.
4. **Steps.**
   1. Write the smoke script against the built wheel.
   2. Run the full local verification (§10).
   3. Update the docs and CHANGELOG.
   4. Run the Qodo review.
   5. Hand off with the evidence.
5. **Tests.** The smoke covers the six scenarios:
   - For each of the three agents: legacy `apply --level 5 --type api`, then
     `extension add` of `llm-application` and SOAA, then `init`, then the
     experiments lifecycle via `validate`.
   - Declarative: `profile apply` with the SOAA capability, `pack apply`,
     `extension list --installed`, `request plan` with the experiment example,
     and `conform --request` on a synthetic Git repository (as in
     `wheel_change_smoke.py`).
   - The `soaa-applicability` pack check.
   - The Windows path budget.
6. **Verify.** See §10 for the full command list.
7. **Completion evidence.**
   - Wheel filename and SHA-256.
   - Smoke output for every scenario, agent and route.
   - `./full_test` counts and skips (expected: Codex nested-AGENTS skip only).
   - The existing wheel smokes are green.
   - The Qodo result.
   - The ledger is updated.
8. **Dependencies / decisions.** Depends on all prior increments (Increment 5
   per U2). **U3**: release number, publication, and the CI pin.

## 9. Phase A acceptance scenarios and where each is proven

| Scenario | Legacy (validate) | Declarative (plan/conform) | Installed wheel |
|---|---|---|---|
| S1 Within an established boundary, no unnecessary experiment | I3: no outcome or record gives golden-identical output; `approved-for-planning` without experiments passes | I6: existing seven plans byte-identical; bounded route unchanged | I11 |
| S2 Material uncertainty produces a bounded experiment with criteria and permitted effects | I2/I3: `experiment-required` is outstanding (WARN; strict FAIL); schema requires criteria, scope and effects | I6: escalation to full-feature; `artifact:experiment-record` UNKNOWN | I11 |
| S3 Failed experiment returns to design with requirements intact; revision retested | I2/I3: `adopt-after-failure` FAIL; `revise-design` then EXP-002 passed and relied upon passes; requirement digests unchanged | I6: same through `artifact:experiment-record` | I11 |
| S4 A pass supports only its observed scope; completion rechecks everything | I3: other validate checks still FAIL independently; synthetic class cannot satisfy an application requirement | I6: `project:tests`, reviews and the architecture checks remain required; the experiment artifact alone cannot make the report pass | I11 |
| S5 Changed requirement, skill, policy or implementation invalidates evidence and forces reassessment | I2/I3: `stale-dependency` and `stale-reliance` FAIL for each kind | I6: `change:plan` stale; `artifact:experiment-record` FAIL | I11 |
| S6 LLM, single-agent SOAA and multi-agent topology route independently | I1 schema; I8 routing tests; topology unchanged | Capability tokens per layer; `llm-evaluation` independent of the SOAA pack | I11 (both extensions plus a topology fixture) |

## 10. Verification standards and commands

- **Per increment:** focused tests, `pytest -k parity -q` for any payload change,
  and scoped Ruff on the changed Python files only. `fix = true` rewrites files,
  so never run Ruff over a whole directory.
- **Before each PR:** `./run_tests -q` (fast tier) and the Qodo local review.
- **Packaging, resources or agent payload:** also the wheel procedure:
  ```bash
  rm -rf dist && python -m build --wheel
  python tests/wheel_windows_smoke.py dist/*.whl
  python -m venv /tmp/gk-wheel && /tmp/gk-wheel/bin/pip install dist/govkit-*.whl
  cd /tmp && for s in pack workflow change check experiment; do
    /tmp/gk-wheel/bin/python -I "$OLDPWD/tests/wheel_${s}_smoke.py" || exit 1; done
  ```
- **Before handoff (Increment 11):** `./full_test`, which needs the e2e toolchains
  or runs in CI. Run every `tests/wheel_*_smoke.py` listed in `test.yml`, and
  the source self-hosting smoke per `plans/SOURCE_SELF_HOSTING.md`.
- **Evidence to record for each increment:**
  - the red run (failing test names);
  - green counts, with skips explained;
  - the wheel SHA where applicable;
  - the commit;
  - limits that remain.

  A green local suite is not live CI activation, protected enforcement, or
  runtime proof.

## 11. Starting the consuming-project pilot (Phase B handoff)

This section is completed in Increment 11 with exact versions. The intended
procedure:

1. **Install the package.** From the handoff, either a local wheel or a
   published release (U3):
   `python -m pip install /path/to/govkit-<version>-py3-none-any.whl`, then
   `govkit --help`.
2. **Legacy feature-folder route**, recommended because feature scaffolding is
   marker-only (#220):
   ```bash
   govkit apply --agent <claude-code|codex|copilot> --target . --level 5 --type api --ci <github|azure> --stack <stack>
   govkit extension add llm-application --target .                     # if the runtime calls models
   govkit extension add skill-oriented-agent-architecture --target .
   govkit extension list --installed --target .                        # verify; resolve any conflict first
   govkit init <discovery-feature> --target . --level 5
   ```
   **Declarative alternative:** an accepted profile selecting the SOAA and LLM
   capability tokens, then `govkit profile apply`, `govkit pack apply` and
   `govkit request plan`. Feature scaffolding still comes from `govkit init`.
3. **First slice.**
   1. Choose one discovery task and representative skill, and write its
      acceptance criteria.
   2. Run architecture preflight. Fill in the SOAA applicability block from
      `templates/preflight-soaa.md`.
   3. When material uncertainty exists, set `experiment-required` and record
      EXP-001 (E1/E1b) with `required_evidence_class: application`.
   4. Implement, record the results, reassess, and complete with
      `govkit validate --target . --strict`. Optionally run the
      `soaa-applicability` check.
4. **Collect at start.** Gather these facts (lightening plan §3):
   - the repository and revision;
   - the accountable owner;
   - the task and its acceptance criteria;
   - the actual skills and how they are selected (person, workflow or model);
   - data, tenant and effect boundaries;
   - credentials;
   - the runtime, skill, dependency and test-adapter pins;
   - the baseline effort, latency, cost and recovery burden.
5. **Feedback.** File findings as GovKit issues against the workflow, the SOAA
   extension or the application. Phase A evidence remains synthetic. The
   pilot's records carry `evidence_class: application` and are first-party, not
   independent.

## 12. Material unknowns requiring outside input

| ID | Unknown | Resolution (2026-10-19, user) |
|---|---|---|
| U1 | Access to the SOAA v0.2 guide and normative corpus | The Architecture Guide v0.2 (publication revision 1.0) was supplied in conversation; the user will point to the SOAA folder for further sources. Its text confirms Ch. 16 subtracts `ProhibitedAccess(s)` (S2) and Ch. 30 uses dotted `soaa.*` keys with profile `urn:soaa:agent-skills:1` (S1). Its Appendix G precedence and Appendix E conformance model apply. The full TRACE catalog is still not reproduced, so exact assertion mapping stays out of scope |
| U2 | Value Builder's project type | Backend API project. Its UI is a separate client that reaches everything through the API. SOAA and llm-application (api/cli) apply; Increment 5 stays deferred and is not needed before handoff |
| U3 | Release identity | 0.23.0. The new consumer gate pins `govkit~=0.23.0`. Publication still needs separate authorization |

The user declined an additional CI step that enforces SOAA from the
preflight's applicability block (2026-10-19). Increment 10 remains an opt-in
check, and no SOAA-specific CI gate is planned.

Every other design question is resolved in §6.

## 13. Out of scope and follow-ups

- Scenario-level requirement digests via `spec_closure`, to reduce
  over-invalidation.
- An accepted-policy maximum evidence age for experiments (a profile field
  beside `maintenance.assessment_max_age_hours`).
- Integration of the isolated worker for untrusted runtime scripts (ADR 0019
  roadmap). Phase A never routes application experiments through pack-check
  execution.
- Declarative discovery of the `llm-application` README.
- Generic result-file digest binding in `pack_check`.
- `migration.py` `WAIVED` handling, and ADR 0019 status text.
- Machine-readable SOAA routing beyond the extension block, revisited after
  Phase B evidence. Any new field must ship with schema, templates,
  preflight, CLI/CI and parity in one change.

## 14. Execution ledger

| Increment | Status | Evidence / commit / PR | Next action or blocker |
|---|---|---|---|
| 0 Preserved fix | in review | PR #226 (`f106a83`): branch tests 318 passed; combined fast tier 5,261 passed / 2 skipped; Qodo local review blocked (CLI not installed) | Merge by the user |
| 1 Routing/context defects | in progress | R1 and R2 in PR #227 (`a158094`, `9f2ee38`), each red-then-green; combined fast tier 5,261 passed / 2 skipped; Qodo local review blocked (CLI not installed) | Merge by the user; R3 (L5 starter §15/§16) and R4 (stale skill names) remain |
| 2 Experiment contract | not started | — | After 0 (parallel with 1) |
| 3 Validator/schemas/CI | not started | — | After 2 |
| 4 Backend/data payload | not started | — | After 3 |
| 5 UI alignment | deferred | U2: Value Builder is an API project; its UI is a client | Not required for handoff |
| 6 Declarative integration | not started | — | After 2 |
| 7 Extension inventory | not started | — | After 1 |
| 8 Routing alignment | not started | — | After 4 and 7 |
| 9 SOAA 0.2.0 | not started | — | After 4, 7, 8; U1 affects wording only |
| 10 Applicability check | not started | — | After 9 |
| 11 Wheel acceptance/handoff | not started | — | After all; U3 |

**Current handoff:** Increment 0 is in review as #226, and Increment 1's
R1/R2 fixes are in review as #227; the user performs the merges. Next: the rest
of Increment 1 (R3, R4) and Increment 2 (experiment contract), which can
proceed in parallel. Install or connect the Qodo CLI so later PRs can run the
required local review.

## Decision log

| Date | Decision | Basis |
|---|---|---|
| 2026-10-19 | Experiment record is an optional per-feature file; preflight outcome is a fenced YAML block | `evaluation_prediction` precedent; proposal D6 "extend existing artifacts first" |
| 2026-10-19 | No new skill and no new command; flags on `validate` and `extension list` only | Proposal D6; `PARITY_TEST.md` cost; CLAUDE.md layering |
| 2026-10-19 | Existing validate output and request plans/reports remain byte-identical | Deterministic replay (`workflow_store`); consumer CI stability |
| 2026-10-19 | SOAA trigger becomes behavior-based; `multi_agent` stays the topology trigger; no eval_criteria SOAA flag | Proposal D7, review 3.6; R1 schema defect |
| 2026-10-19 | SOAA 0.2.0 keeps identities and adds an explicit `capability_pack` with README and advisory resources | Proposal D5; review P4; `_legacy_contract` omits README |
| 2026-10-19 | SOAA applicability coverage is an opt-in extension check, not a core engine | Proposal D1 "no second policy engine"; ADR 0004 state semantics |
| 2026-10-19 | Release 0.23.0; Value Builder treated as an API project; Increment 5 deferred; no SOAA-specific CI gate | User decisions U2, U3 and the declined CI step |
| 2026-10-19 | `multi_agent_evaluation` scores in eval_criteria may be null (placeholders), unlike the plan's `evaluation_prediction` | The starter documents `score: null` / `evidence: ""` until evaluation runs |
