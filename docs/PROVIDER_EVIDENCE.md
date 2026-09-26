# Provider admission and maintenance evidence

GovKit checks native PR context before execution and translates explicitly supplied
provider observations into the existing maintenance assessment. It does not choose
credentials, fetch PRs or branch rules, configure required checks, or authenticate
a JSON file. A protected caller must collect and accept the inputs independently
of the inspected code. Existing entry points without admission settings continue
to work; they cannot establish admitted provider enforcement through this adapter.

## Admit a PR run

Evidence collection recaptures Git using the assessment checkout's current accepted
budget and compares its source identity with the runtime record. Imported limits
cannot enlarge current policy. Historical version-1 runtime records can match only
the default budget with matching accepted source bytes; a policy change requires
fresh conformance and evidence. Imported success remains unauthenticated.

Add `admission` to the accepted pipeline settings, then review and generate a new
entry point through the [existing protected workflow](PIPELINE_GENERATION.md):

```json
{
  "schema_version": 1,
  "govkit_version": "0.21.1",
  "execute_checks": ["project:tests"],
  "admission": {
    "provider": "github",
    "repository": "example/service",
    "target_ref": "refs/heads/main",
    "allow_forks": false
  }
}
```

For Azure, select `azure` and the target repository's ID. Both renderers add the
same inputs: `provider_event` (absolute JSON path), `policy_revision` (full pinned
policy commit SHA), `request_digest` (SHA-256 of accepted request bytes), and
optional `change_output` (new JSON artifact outside both checkouts). Set
`observed_at` explicitly when producing evidence for maintenance. The runtime
reads accepted request bytes once for execution. Missing, unsupported or
inconsistent admission inputs fail before project checks run. Full commit IDs are normalized to lowercase; uppercase
hexadecimal input is accepted for both supported Git object formats.

Before using the accepted observation budget, admission reads only the profile
and referenced conformance source (each at most 64 KiB). Their bytes and regular
file modes must match the pinned policy commit, HEAD must match that revision,
and the parsed profile must match the pipeline profile pin. It then inspects both
complete checkouts with that same budget. Dirty, missing, substituted or changed
bootstrap sources withhold execution; expanded budgets cannot relax their own
source validation. The source binding is checked again before commands and at
final stability assessment. Caller pins remain assertions, not authentication.

| Provider | Explicit event record | Admission |
|---|---|---|
| GitHub | `event_name: pull_request`, `payload` containing the native webhook payload | Open, nondraft PR; opened/reopened/synchronize/ready_for_review/edited action; exact target repository and branch; source head and base SHA |
| Azure | `event_name: PullRequest`, `payload` containing the Git PR API response | Active, nondraft PR; exact repository ID/target ref; lastMergeSourceCommit and lastMergeTargetCommit; forkSource when present |

See the native [GitHub PR payload contract](https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request)
and [Azure Git PR API](https://learn.microsoft.com/en-us/rest/api/azure/devops/git/pull-requests/get-pull-request?view=azure-devops-rest-7.1).
Prepare the **source head**, not a synthetic merge checkout. The inspected and
independent policy checkouts must have complete, clean Git-visible snapshots at
the admitted head and caller-pinned policy revision. Base history must be present.
Forks require explicit policy opt-in; that does not grant credentials or sandbox
project code. Push, merge-group, draft and scheduled events are currently rejected.

Keep policy, event exports, accepted request/digest, generated definition and
interpreter under trusted caller control. Pin the policy revision in that caller,
not inside the policy commit itself. Fetch provider facts before handing execution
to a job without provider credentials. Git snapshots exclude ignored untracked
files; provision policy/runtime dependencies from controlled immutable inputs.
These are consistency checks, not an isolation boundary against concurrent writers.

## Collect CI facts and assess maintenance

```sh
govkit pipeline evidence --target /work/service --settings /accepted/settings.json \
  --change-report /evidence/change.json --observation /evidence/provider.json \
  --as-of 2026-09-24T12:00:00Z --json
govkit pipeline assess --target /work/service --settings /accepted/settings.json \
  --change-report /evidence/change.json --observation /evidence/provider.json \
  --metadata /cache/releases.json --as-of 2026-09-24T12:00:00Z \
  --output /evidence/assessment.json --json
```

`provider-observation/v1` is a caller-approved export contract, with provider,
repository/ref, head/base, observation time, generated artifact digest, canonical
change-report digest, executed runtime version, and run ID/URL. Five measured facts
are boolean or null: `enabled`, `required_check`, `all_changes`, `trusted_policy`,
and `approvals`. Null means unmeasured. The collector must inspect the actual
protected caller, event/path coverage, required status/build validation policy,
and applicable reviewer policies; copying true values from an example is not
collection. No live API collector or provider authentication is supplied here.
The paired [examples](../governance/examples/pipeline/README.md) use nulls.

Configuration checks compare generated bytes with accepted settings and the
ownership record. Runtime checks replay the change report and bind the actual
Git snapshot, accepted profile, lock, version pin and provider run. Enforcement
checks retain each explicit fact. Imported runtime and enforcement proofs retain
`unverified-artifact` origin: matching hashes and all-true export values cannot
make either required check pass. Their success claims remain unknown until an
independent authentication boundary exists; there is no caller-set trust flag.
Explicit negative observations remain failures even if another supplied runtime
report has mismatched identity. Missing facts, absent age policy, stale/future
timestamps, mismatched reports or unknown required outcomes cannot produce a
healthy integration. Explicit inactive/missing/drifted configuration produces
actionable failure. An accepted compatible version pin alone is not a failure.

The canonical check report contains `ci:configuration`, `ci:runtime`,
`ci:enforcement` and their aggregate `ci:integration`. Maintenance derives required
status from accepted policy and reuses these results. Other required CI IDs without
evidence stay unknown. The original oldest observation time survives collection;
recollecting an old export cannot renew freshness. Generated files and
their lock are included in inventory identity even when ignored by Git.

`pipeline assess` calls the same `assess_repository` engine as `maintain assess`.
It reports all four dimensions independently and returns a report even when
maintenance is needed. `pipeline evidence` exits unsuccessfully for nonpassing
required checks. Default collection is offline and read-only. Explicit
`--release-source SOURCE_ID` during assessment uses the existing approved,
anonymous, data-only refresh boundary, including profile `allow_refresh`; it does
not install packages or rewrite locks. Cached `--metadata` remains supported.
Action-specific arguments are checked before collection or publication:
`--assessment`/`--recommendation` belong only to `upgrade-preview`,
`--change-report`/`--observation` to `evidence` or `assess`, and
`--metadata`/`--release-source` only to `assess`. Inapplicable arguments are errors.

## Publish only when selected

`--output` creates a new private report file outside the assessed repository.
Existing files and symlink ancestors are rejected. Directory handles and an atomic
create-only link protect publication from redirected paths and overwrites; the
parent directory must already exist and support these POSIX operations.
`change_output` uses the same boundary and also excludes the policy checkout.
Neither option uploads anything. Reports contain governance descriptors, paths,
digests and findings; they do not add raw source, prompts or developer telemetry.
Use access controls appropriate for those descriptors.

After reviewing publication, a protected caller can include the paired
`ci/github/maintenance-publication.yml` or
`ci/azure/maintenance-publication.yml` examples. They upload only the named
assessment file through the provider's artifact facility. GitHub uses
[upload-artifact](https://docs.github.com/en/actions/tutorials/store-and-share-data);
Azure uses [PublishPipelineArtifact](https://learn.microsoft.com/en-us/azure/devops/pipelines/tasks/reference/publish-pipeline-artifact-v1?view=azure-pipelines),
which requires Azure DevOps Services. Neither example creates a workflow, broadens
permissions, or turns publication on during generation. Pin/review third-party
actions and retention settings in the protected caller.

## Preview the selected upgrade's integration

```sh
govkit pipeline upgrade-preview --target /work/service \
  --settings /accepted/settings.json --assessment /evidence/assessment.json \
  --recommendation RECOMMENDATION_ID --pack-source /accepted/candidate-pack \
  --as-of 2026-09-24T12:00:00Z --json
```

The assessment and candidate are revalidated before composing proposed gates,
configuration operations, permission requirements and follow-up checks. Pack
snapshots are explicit; metadata never downloads executable code. Existing
customizations remain protected. A CLI candidate updates the proposed runtime pin;
the current CLI renders it without claiming that candidate was installed or ran.
When no pack lock exists, a CLI candidate resolves the accepted profile from the
explicit available catalog (bundled snapshots plus `--pack-source`). An existing
lock continues to select its installed pinned closure.
This is a read-only proposal with `writes_authorized: false`. Apply the selected
package/resource upgrade through its owning workflow, then review fresh pipeline
settings and a new generation preview/digest before any configuration write.
