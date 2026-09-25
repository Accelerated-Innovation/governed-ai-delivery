# Declarative release readiness

The release candidate is **not complete**. Protected-caller deployment evidence,
consenting-team pilot observations and an announced legacy compatibility boundary
remain open. This record maps evidence to the
[implementation plan](declarative-governance-implementation-plan.md#10-release-candidate-definition-of-done);
it does not change release scope, approve publication or start a deprecation clock.

## Verified baseline

PR [#207](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/207)
merged as `6bc40fc4ecc1481c84eb263d386dccd9c87eaea7`, tree-identical to its final
head `b086bf56456e621621dad758faa5ea85475cae85`.
All six final-head checks passed in
[Tests run 36186637989](https://github.com/Accelerated-Innovation/governed-ai-delivery/actions/runs/36186637989):
Python 3.11/3.12 fast suites, the e2e/toolchain tier, the Linux wheel job and both
Windows deep-path wheel jobs. This verifies the source build labeled `0.21.1`;
it does not establish that a published package with that version contains these changes.
New commits require their own applicable checks before release.

Qodo's completed run `1267555` reviews implementation
`23354bb6a2baa9688b0acc5b873ca6684796a697`. Its one documentation finding now has
attribution `implemented` after clarification `b086bf5`; this is not a completed
review of the final head. Local pre-PR review retains the recorded repository
authorization blocker under the support/no-retry handoff.

PR #205's intermittent defect-pilot comparison failure remains unexplained.
PR #206 fixes the separately reproduced inherited-`CI` test gap and preserves
exact report and file-integrity assertions with better diagnostics. Its successful
CI run and the prior macOS/Linux repetitions do not prove the original flake fixed.
Any recurrence needs the report diff or changed-file diagnostic, exact commit,
interpreter and run reference; do not weaken evidence hashes or hide it with a retry.

## Release checklist evidence

“Verified” below means the stated automated/local scope, not live adoption or
provider authentication. The implementation plan owns the checkboxes.

| Plan criterion | Evidence and current limit |
|---|---|
| I00–I13 exit criteria | Open: the [execution ledger](declarative-governance-implementation-plan.md#11-execution-ledger-and-handoff) records delivered increments; I10 external enforcement and I13 retirement/pilot inputs are blocked on the records below. |
| Included feature acceptance reconciled and satisfied | Open: [#147](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/147), [#149](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/149) and epic [#142](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/142) retain their unchecked criteria. |
| Legacy compatibility and customization preservation | Verified for frozen selections and representative real L3/L4/L5 installs: [migration tests](../tests/test_migration.py), [wheel migration pilot](../tests/wheel_migration_smoke.py), historical native-lock replay and [migration/rollback guidance](../docs/LEGACY_MIGRATION.md). Unsupported legacy inputs require reconciliation. |
| Independent capability/workflow combinations across agents | Verified by [workflow tests](../tests/test_workflows.py), [pack tests](../tests/test_capability_packs.py), [three-agent pack wheel pilot](../tests/wheel_pack_smoke.py) and [request wheel pilot](../tests/wheel_workflow_smoke.py). This is fixture coverage, not a claim about every custom pack combination. |
| Useful brownfield setup without full calibration | Automated adoption/source-preservation scenarios pass in [discovery tests](../tests/test_discovery.py) and [onboarding tests](../tests/test_capability_onboarding.py); usefulness in actual familiar/unfamiliar repositories still needs consenting-team observations. |
| Independent controls and actual-diff bypass prevention | The [actual-change tests](../tests/test_change_conformance.py) cover required controls, sensitive/out-of-scope changes and real failing evaluations. Deployment/path-filter/reviewer enforcement remains open in #147. |
| Four-dimensional maintenance with honest freshness | Verified by [maintenance tests](../tests/test_maintenance.py), [inventory tests](../tests/test_maintenance_inventory.py), [freshness regressions](../tests/test_migration_freshness.py) and [runtime-only maintenance pilot](../tests/wheel_maintenance_assessment_smoke.py). Unavailable provider facts remain unknown. |
| Provider limits, provenance and reporting privacy | Verified by [provider evidence tests](../tests/test_pipeline_evidence.py), [posture tests](../tests/test_posture.py), [change posture tests](../tests/test_change_posture.py) and [aggregation tests](../tests/test_posture_aggregate.py). Imported exports are not authenticated evidence. |
| Clean wheel and required CI/toolchain checks | Verified for the baseline/run above. Windows coverage is the bounded deep-path install/entrypoint/pack-loading scenario; generated-provider writes require supported POSIX filesystem operations and are not certified on Windows. |
| Pilot findings, migration/rollback and deprecation records | Migration/rollback guidance and verified reported defects are recorded. Actual adoption observations and warning/removal policy remain open; the [pilot protocol](../docs/ADOPTION_PILOT.md) is not collected evidence. |
| Real shipped commands and skill references | Verified by [tutorial inventory tests](../tests/test_onboarding_inventory.py), [executable onboarding tests](../tests/test_capability_onboarding.py), [native wheel checks](../tests/wheel_native_skills_smoke.py) and the current documentation reconciliation. These checks do not validate every arbitrary prose claim. |
| Reviewable release candidate | Open until the preceding incomplete criteria have evidence or an explicit recorded scope decision. Merging and publication require their own authorization. |

## Inputs that close the remaining work

| Input owner | Required record | Acceptance it supports |
|---|---|---|
| Repository/platform maintainer | Chosen GitHub/Azure consumer, protected caller and policy revision, accepted request/base/head identity, pinned runtime and pack inputs, actual run references, required-status/reviewer settings, and trigger/path coverage. Include passing and failing cases showing required security, architecture, evaluation and approval controls cannot be omitted by a label or path filter. Preserve unsupported events and unauthenticated observations as unknown. Follow [provider evidence](../docs/PROVIDER_EVIDENCE.md). | #147's remaining enforcement criterion; relevant #142 scenarios. |
| Consenting pilot team | Team-reviewed aggregate observations for the applicable existing-service/MCP/LLM and workflow scenarios, with comparison method, setup versus recurring effort, useful/noisy findings, missing responses and uncertainty. Follow the [voluntary protocol](../docs/ADOPTION_PILOT.md); synthetic fixtures and review counts do not substitute for this record. | #142 adoption/usefulness acceptance and I13 feedback. |
| Release maintainer | Warning-start release, minimum warning period, earliest removal release, announcement reference, supported legacy inputs during that period, and reviewed migration/rollback evidence. Keep support until the announced conditions are met; later deletion is a separate change. | #149's remaining compatibility criterion and I13 retirement policy. |

No pilot participants, consumer repository or release boundary are selected by
this document. Use links or appropriately restricted evidence references rather
than copying credentials, source, prompts, tickets or individual work records here.
A caller-supplied all-true provider JSON does not close the enforcement criterion.

## Scope and next action

The next implementation needs the maintainer to provide the legacy warning/removal
policy or identify an authorized consumer repository for provider/pilot validation.
That input has been requested. Continue focused fixes for verified defects and
refresh this evidence record when new inputs arrive. Keep the original parity flake
visible. Once external records are available, review them against the exact remaining criteria and update the
plan and issues together; never infer acceptance from an issue or PR being closed.

The adjacent Langfuse/evidence-authoring issues and undefined FeaturePeers work
are not silently added to this release. Their scope can be selected explicitly,
and FeaturePeers needs a definition before architecture or a pack is proposed.
