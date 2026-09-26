# Maintenance posture export

`govkit posture export` projects a **saved canonical maintenance assessment** into
versioned JSON or a human report. It does not inspect the repository, run project
checks, fetch release metadata, calculate new upgrade advice, or authorize changes.
The original assessment remains the source of detailed local evidence and reasons.

Version-2 assessments produce version-2 exports with an opaque
`identity.observation_digest_ref` for observation-budget provenance. Version-1
sources retain version-1 projection and replay semantics. No policy bytes or raw
source digest are disclosed; older readers reject version-2 records.

```bash
# Save an offline assessment locally. Keep this raw record private.
govkit maintain assess --target /path/to/project \
  --as-of 2026-09-24T12:00:00Z --json > /private/artifacts/assessment.json

# Inspect its privacy-filtered maintenance posture.
govkit posture export --assessment /private/artifacts/assessment.json

# Write a new JSON artifact outside the assessed repository.
govkit posture export --assessment /private/artifacts/assessment.json \
  --output /private/artifacts/posture.json --json
```

An export command exits zero when conversion/publication succeeds. That is **not**
a conformance pass: `maintenance.state`, `maintenance.exit_code`, each dimension,
and every recommendation retain the canonical results. Export errors exit one
without echoing raw validation details or evidence. Invalid argparse syntax exits
two. A present profile or installed capability does not imply an executed control.

## Contract and authority

The strict [posture-export v1 schema](../governance/schemas/posture-export.schema.json)
contains independent release, resource, repository-fit and CI dimensions, canonical
finding references and recommendations. Replay validates the assessment, inventory,
profile identity, release inputs, checks and recommendations before projection.
Output replay verifies its digest, four dimension IDs and canonical summary/state/
exit-code consistency. Neither validation nor a digest authenticates a publisher,
provider, policy author or the original assessment.

| Export field | Meaning |
|---|---|
| `as_of`, `assessment_ref`, `repository_ref`, `identity` | Assessment time and stable references to repository, source snapshot, profile/resolution, Git state and comparison baseline |
| `capabilities.configured`, `.required`, `.recorded` | Desired/required capabilities and pack-lock claims; `.lock_verification` preserves verified/unverified/unknown status |
| `configured_controls` | Repository and conditional workflow declarations, explicitly `not-assessed` by this export |
| `architecture` | Observations separately from accepted contract/transition descriptors, scopes, modes and exception expiry dates; no architecture text |
| `versions` | Running CLI, recorded installation, resolver and locked versions, known candidates/exclusions, pin/compatibility references and source freshness/lookup facts |
| `resources` | Resource references and actual matching/missing/modified/unavailable observations, separate from version equality |
| `maintenance` | The canonical four dimensions, all findings/actions, required status, urgency, target, affected resources/controls/customizations, prerequisites and preview references |
| `coverage` | Profile/Git/discovery coverage and the explicit `maintenance-dimensions-only` reporting boundary |

If a pack lock omits a resource's owner, `resources[].component_ref` is `null`.
The resource observation and the lock's unverified status remain in the export;
reporting does not infer ownership or discard the resource.

`coverage.change_results` is `not-supplied`. This increment does not export a
change's selected workflow, actual evaluation results or applicability. The
maintenance dimension's `execution: executed` means the **maintenance assessment**
ran, not that every application/security/evaluation control ran. CI unknowns remain
unknown, including unauthenticated positive provider exports from `pipeline assess`.
Change-specific reporting has a separate [change posture](CHANGE_POSTURE.md)
snapshot. [Offline aggregation](POSTURE_AGGREGATION.md) keeps their evidence
separate. The [voluntary pilot protocol](ADOPTION_PILOT.md) evaluates usefulness
and effort; this report is neither a maturity score nor a productivity measure.

## Privacy and references

Projection uses an allowlist. It does not copy source code, raw requests, prompts,
tickets, architecture text, findings/recommendation prose, command output, developer
identity, URLs, file paths or arbitrary identifiers into the export. Known public
capability labels are preserved; custom capability names become `custom` with a
stable reference. The input itself may contain private local details: keep the raw
assessment private and inspect the exported artifact before sharing it.

Arbitrary values become `ref:` plus a SHA-256 of their category and canonical value.
These are stable **pseudonymous** join keys, not anonymization: known/guessable inputs
can be correlated. Do not use them as access controls or authentication evidence.
`assessment_ref` references the already validated assessment digest. `local_ref`
contains only a fixed JSON Pointer into the original assessment, such as
`/recommendations/0` or `/inventory/candidates/0`; it does not include its filename.
Use the source assessment to look up the full reason/evidence, prerequisites,
policy/pin constraints and exact protected preview before acting.

Versions have a public normalized `display` and an exact-value `ref`. Local version
labels can contain private identifiers, so they are omitted from display. Two
versions with the same public display can have different references. An invalid or
oversized display is null; it is not silently treated as a known compatible
version. Existing canonical candidate/exclusion and policy decisions remain
unchanged. Timestamps normalize to UTC; unavailable dates remain null. Accepted
exception expiry dates preserve their date-only form.

JSON is byte-deterministic for the same saved assessment; no new timestamp, random
run ID or developer information is added. The source snapshot and its time are
preserved, rather than refreshed by exporting it again. An old export cannot prove
current health. All records are explicitly unauthenticated snapshots.

## Safe local and CI publication

Stdout is the default. `--output` explicitly creates a new JSON file with owner-only
permissions outside the assessed repository, using the existing protected artifact
writer. Existing files, symlinks and paths inside the target are refused. The
command does not install/upgrade packages, change profiles/workflows, or transmit
anything. The writer's existing POSIX/platform and concurrent-writer limitations
apply; see [provider publication](PROVIDER_EVIDENCE.md#publish-only-when-selected).

To share from CI, first run this export against the locally saved assessment.
Then explicitly configure your provider's artifact upload to select **only the
new posture JSON**. The paired opt-in
[GitHub](../ci/github/maintenance-publication.yml) and
[Azure](../ci/azure/maintenance-publication.yml) publication examples can point to
that file; review the upload implementation, access, retention and filename in the
protected caller. Do not upload the raw assessment or a containing directory by
accident. Upload is a separate caller-controlled network action; this command does
not perform it.

The [bundled example](../governance/examples/posture/README.md) illustrates optional
updates and unknown CI. A runtime-only installed-wheel pilot checks all three agent
integrations/both CI profiles, canonical action parity, privacy, resource drift,
unknown CI, private publication, duplicate-output rejection and unchanged consumer
files. These are isolated fixtures, not hosted enforcement or team adoption data.
