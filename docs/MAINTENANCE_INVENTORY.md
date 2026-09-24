# Inventory versions and preview release candidates

`govkit maintain inventory` reads a repository's recorded and actual resources.
It separates the running CLI, legacy marker version, replayed profile resolution,
locked packs and per-file digests. A matching version string never hides missing
files or customizations. These facts feed the canonical
[release/resource/repository-fit/CI assessment](MAINTENANCE_ASSESSMENT.md).

```sh
govkit maintain inventory --target /work/service --json > /work/inventory.json
```

Keep saved records outside the target. Output includes assessment time, Git revision
and bounded dirty-tree identity, profile/resolution/lock digests, resource states,
release sources, candidates, uncertainty and an inventory digest. Supply `--as-of`
with a timezone-aware timestamp for reproducible comparison. Missing/unreadable
metadata remains explicit; other inventory facts can still be useful.

- `matching`: observed bytes match the recorded digest.
- `missing`: resource refresh is a possible next operation.
- `modified`: reconcile a potential customization; it is never permission to overwrite.
- `unavailable`: inspect the path or observation limit first.

`lock_verification: verified` additionally requires existing pack/profile replay and
resource checks to succeed. Until then paths, owners and expected digests are only
recorded claims. File matching is not execution or enforcement evidence. Legacy
files without a declarative pack lock are outside this resource inventory; use the
legacy/migration checks for those installations.

## Approved release metadata

Accepted profile `maintenance.sources` and `maintenance.constraints` choose sources,
channels, exact pins and compatibility ranges. `metadata_max_age_hours` governs
freshness. No configured source or no usable metadata means unknown freshness.
An intentional compatible pin is not a requirement to upgrade.
Each component can have only one maintenance constraint; profile validation rejects
duplicates even when they name different sources or channels. Candidate previews
therefore use that component's single accepted policy.

Pass one or more explicitly supplied local JSON/YAML metadata files:

```sh
govkit maintain inventory --target /work/service \
  --metadata /work/releases.json --json > /work/inventory.json
```

Metadata conforms to `release-metadata.schema.json`. Each source records its exact
approved URL/ID, publisher `as_of`, last `retrieved_at`, lookup status and releases.
Each release names its component (`govkit` or a pack ID), version/channel, required
GovKit/Python versions and dependency component constraints. Versions and ranges use
the existing packaging dependency. Dependencies refer to installed component IDs,
not capability names; a coordinated multi-component upgrade requires a separate
plan and is not silently assumed.

A worked offline profile/metadata pair is shipped in
[governance/examples/maintenance](../governance/examples/maintenance). Its URLs and
newer versions are illustrative, not claims of published releases.

Newest known release, compatible candidates, selected upgrade target and installed
policy compliance are separate facts. Excluded versions retain reasons for channels,
prereleases mislabeled stable, runtime requirements, dependencies and both maintenance
and profile pack pins. Missing/stale/future-dated metadata cannot select an upgrade.
Without an age policy, freshness is unknown. Refreshing an old source document does
not reset its publisher age. `latest_verified` remains false: a local record, even
one recording a prior refresh, cannot certify the latest published release.

Installed policy compliance applies the same version, channel, runtime and dependency
checks as candidate eligibility. A known mismatch with accepted pins, ranges or the
stable-channel prerelease restriction is `outside-policy` without needing release
metadata. Otherwise, compliance requires a matching release in fresh usable metadata:
an eligible match is `compliant`, an excluded match is `outside-policy`, and absent,
stale or unavailable evidence is `unknown`. A numeric pin alone cannot establish
runtime or dependency compatibility.

## Explicit metadata refresh

Refresh requires accepted `maintenance.allow_refresh: true`, an approved source ID,
and an explicitly named cache path **outside the target repository**:

```sh
govkit maintain refresh --target /work/service --release-source team \
  --output /work/releases.json --json
```

The provider reads one versioned metadata document from the exact approved HTTPS
URL. Teams may publish this data file through existing release assets or static
repository hosting; no new registry or service is required. Raw PyPI/GitHub API
responses are not this contract and require normalization by the metadata publisher.
No implicit network lookup occurs during inventory, preview or request planning.

The anonymous GET includes no repository content, paths, identity, posture, prompts
or secrets. Credentials, URL queries/fragments and redirects are rejected; a redirect
requires approval of its final URL in policy. Transport uses a ten-second timeout
and a 2 MiB response limit. Failure produces a failed lookup record, an unsuccessful
CLI exit and unknown freshness. The named cache is atomically replaced with owner-only
permissions; no project metadata, lock, resource or pipeline is modified. A failed
refresh replaces that explicitly named cache with a failure record, so keep a separate
historical cache if needed. No packages or executable code are downloaded or installed.

## Review a candidate

A fresh compatible metadata candidate still needs an explicitly available pack:

```sh
govkit maintain preview --target /work/service --inventory /work/inventory.json \
  --component application-governance --pack-source /work/reviewed-pack --json
```

The command re-observes the saved inventory inputs and rejects stale or inconsistent
records. It uses the existing pack resolver and preview with the selected local
candidate and other locked packs, showing affected controls, resources and protected
customizations. Missing candidate content, incompatible actual manifests, profile
pins or unreplayable resources block readiness. Metadata alone does not authorize
execution or bypass pack digest/source constraints.

Review and apply through the existing `govkit pack preview/apply` workflow with the
same accepted profile and explicit catalog. That operation independently rechecks
inputs and edit protection; a saved maintenance preview is never executed as an
operation list. Rerun inventory and applicable conformance afterward. A CLI candidate
instead points to the developer's existing package manager: updating that package
does not refresh repository resources.

Inventory limits include 2 MiB per read, 4,096 declared resources and a 64 MiB aggregate
resource budget with one bounded overflow probe. Metadata allows 2,000 releases per
source. Symlinks/nonregular resources are unavailable and are never followed.
Git identity uses the existing bounded Git observer; ignored untracked files are not
covered. No arbitrary project checks run. These are consistency snapshots, not signed
approvals, an exhaustive architecture assessment or a transaction against concurrent
writers. Keep the target quiescent when reviewing a preview.
