# Assess maintenance and review the next operation

`govkit maintain assess` combines four independent dimensions in one read-only
record. Several findings can coexist: a compatible update, a customized skill,
new LLM usage and an unverified CI integration require different actions.

```sh
govkit maintain assess --target /work/service --json > /work/assessment.json
```

Keep records outside the target. Use `--as-of` with a timezone-aware timestamp to
reproduce a comparison. The default is the current UTC time. A successful command
means a valid assessment was produced; it is not a conformance gate or approval.
No network request, pack/check execution, policy acceptance or project write occurs.
The existing `inventory` command remains available for the underlying version and
resource facts. Explicit release-cache refresh is a separate operation described in
[maintenance inventory](MAINTENANCE_INVENTORY.md).

| Dimension | Input and interpretation | Typical next action |
|---|---|---|
| Releases | Approved local metadata, compatibility, pins, runtime/dependency facts and freshness | Review a compatible CLI/pack update, inspect metadata or reconcile version policy |
| Resources | Recorded lock ownership and actual bounded file digests | Refresh missing resources, reconcile customizations or inspect unverified ownership |
| Repository fit | Existing discovery outcomes, accepted references and an explicit last-reviewed discovery baseline | Review capability setup or a scoped architecture/policy decision |
| CI | Identity-bound canonical check results for accepted CI requirements | Inspect or repair missing, failed, inactive, drifted or unverified integration evidence |

The `checks.results` entries preserve the four states separately. A passing
dimension describes only its measured scope. There is no single current/outdated
decision. An intentionally compatible pin does not require an upgrade, and unknown
release freshness alone does not prove a policy failure. An unverified pack lock
cannot establish a required version violation or make an arbitrary recorded file
policy-required. Verifying the selected installation itself remains required by
the accepted capabilities. Known running-CLI or verified-pack version violations
trace to the accepted maintenance constraints.

Every recommendation has a stable ID, action, affected scope/resources/controls,
evidence, uncertainty, urgency, prerequisites, customization impact and owning
preview operation. Required status names its accepted policy source. Discovery
signals remain advisory: importing an LLM library can suggest `llm-evaluation`
review but cannot select it or change architecture. Pack controls that cannot yet
be replayed remain uncertain; the existing pack preview identifies the concrete
affected controls when a candidate can be loaded.

## Compare with explicit evidence

```sh
govkit discover --target /work/service --json > /work/reviewed-discovery.json
# Review this baseline before using it for later comparisons.
govkit maintain assess --target /work/service \
  --metadata /work/releases.json \
  --baseline /work/reviewed-discovery.json \
  --ci-report /work/ci-check-results.json \
  --as-of 2026-09-24T12:00:00Z --json > /work/assessment.json
```

Only use a discovery baseline you explicitly reviewed. Unchanged complete evidence
does not repeat setup decisions; incomplete evidence remains unresolved. A baseline
is an observation, not an authenticated approval. Invalid/unavailable repository
discovery leaves the other dimensions useful. Malformed supplied provider documents
are rejected; an absent provider or canonical unknown/error result stays unknown.

CI input uses the existing `check-results` contract and replay validator. Assessment
consumes accepted required check IDs beginning `ci:` and the legacy migration
obligation `migration:ci-enforcement`. An accepted GitHub/Azure integration also
requires `ci:integration`. When an accepted profile specifies neither, this
dimension is not applicable; an absent profile leaves requirements unknown.

A provider record must include the repository scope `.` (additional narrower scopes
are allowed) and match repository ID,
complete Git revision/dirty-tree identity, profile, resolution and lock digests.
Its `identity.observed_at` must be at or before assessment time and within accepted
`maintenance.assessment_max_age_hours`. Missing age policy, times, Git coverage,
matching identity or required results yields unknown. A record cannot waive an
accepted requirement by setting its own `required` flag false. Required checks
remain required when they pass. Canonical pass/fail/unknown/skipped outcomes are
reused; workflow presence is never substituted for execution.

These checks establish consistency, not provider authenticity. The caller must
choose trusted evidence. [Provider admission and evidence](PROVIDER_EVIDENCE.md)
compare explicit provider exports and generated configuration, feed the same
assessment, and preview a selected upgrade's integration changes. The caller
collects those exports; this command does not contact GitHub/Azure or infer
active enforcement from workflow files. Synthetic provider fixtures in the pilots
demonstrate both passing and failing paths, not live platform enforcement.

## Preview and verify separately

Choose a recommendation ID from JSON or human-readable output:

```sh
govkit maintain preview --target /work/service \
  --assessment /work/assessment.json --recommendation maintenance:RECOMMENDATION_ID \
  --pack-source /work/reviewed-candidate --json
```

The command re-observes the inventory and discovery, rejects stale or inconsistent
records, and reevaluates release/CI freshness at the preview time. Use `--as-of`
only to request an explicit reproducible time. A pack upgrade composes the existing
protected pack preview from the supplied local snapshot and other locked packs.
It names the compatible target, resources, controls and protected customizations.
A CLI upgrade points to the existing package manager. Other recommendations show
the owning review/setup/repair workflow and its prerequisites with `ready: false`;
they are not executable changes or generated CI repair patches. For a selected
CLI/pack upgrade, use the separate
[integration preview](PROVIDER_EVIDENCE.md#preview-the-selected-upgrades-integration)
to inspect affected gates, settings and follow-up validation without writing workflows.

Apply reviewed pack/profile/migration operations through their existing commands.
An assessment, a digest and `ready` do not independently authorize writes. Then
verify against the earlier record:

```sh
govkit maintain verify --target /work/service \
  --assessment /work/assessment.json --json > /work/verification.json
```

Verification returns a fresh assessment and `resolved`, `remaining`, `unverified`
and `new` recommendation IDs. Disappearance alone does not mean resolution: the
affected dimension must pass under the same accepted profile and repository
identity. Otherwise the old finding is unverified. A marker update cannot resolve
missing resources. A real resource repair can resolve its findings while capability
review and CI uncertainty remain. This is conservative: one unresolved finding in
a dimension can leave other disappeared findings unverified.

Verification reuses the saved evidence by default. Supply `--metadata`, `--ci-report`
or `--baseline` to replace the corresponding snapshots with explicitly reviewed
current inputs. For example, a repaired integration needs a new matching provider
report to demonstrate its pass; replaying its prior failure cannot verify repair.

`govkit migrate preview` includes this canonical assessment automatically. Supply
`--assessment /work/assessment.json` to bind an explicitly timed baseline/provider
snapshot. Use that same option for the separately authorized `migrate apply`.
Stale inputs are rejected before writes. Preview and apply also reevaluate release
and CI freshness against the current clock. An expired record must be regenerated;
the reviewed digest stays stable while the same evidence remains valid. Application
reruns both the existing
conformance inspection and maintenance assessment, retaining unknown CI evidence
and treating findings affected by changed accepted policy as unverified. If old
metadata/baseline inputs no longer apply, fresh offline assessment exposes the gaps.
Post-operation verification always uses the current time, including this fallback.
Idempotence, original-content preservation and rollback remain unchanged.

## Record and observation limits

`maintenance-assessment.schema.json` versions the record. It embeds inventory,
discovery, canonical check results, explicit input snapshots and comparison digests.
New assessments and their inventories use version 2 to bind observation-budget
provenance. The identity's `observation_digest` covers the effective limits and
accepted-source identity; a changed source requires reassessment. Saved version-1
records continue to replay without rewritten identities or digests. Older readers
reject version-2 records.
Replay binds saved metadata to the effective approved-source records and recomputes
release candidates before validating derived checks/recommendations. Missing candidate
sources and inconsistent saved inputs are validation errors. Explicit new inputs to
`verify` are allowed. Hashes do not authenticate sources. Built-in observations
record references/digests rather than
repository source-file bodies. Supplied check-report text and policy metadata are
retained, so choose appropriate provider inputs. Nothing is uploaded automatically.

Inventory/discovery retain their existing read/coverage limits. Saved assessments
have a 16 MiB read/output limit; metadata, CI and discovery input files retain the
2 MiB CLI input bound. Symlink/resource coverage, ignored untracked Git files and
concurrent writers remain limitations. Input recapture detects observed changes
during assessment but is not a filesystem transaction. Keep targets quiescent.

The [offline maintenance example](../governance/examples/maintenance) and
`tests/wheel_maintenance_assessment_smoke.py` demonstrate all three agents,
simultaneous findings, local/CLI equality, synthetic CI pass/fail, protected
candidate previews and actual post-repair verification from a runtime-only wheel.
