# Migrate an existing GovKit installation

`govkit migrate` proposes a declarative profile from an existing installation. It
preserves legacy files and adds profile metadata, pinned capability resources and
native guidance. This is ordinary governance adoption; it does not refactor the
application or approve an architecture transition.

## Review before writing

```sh
govkit migrate --target /work/service --json > /work/migration-preview.json
```

The default is preview. No target files are written. Review `proposed_profile`,
`decisions`, `operations`, `controls`, `local_verification`, `discovery_coverage`
and the canonical `maintenance` assessment. Maintenance distinguishes version
updates, resource reconciliation, capability review and CI repair. It does not
turn these findings into automatic migration operations. An optional
`--assessment /work/assessment.json` rechecks a saved assessment; use the same
option for the subsequent apply. Both commands check evidence freshness against the
current clock and reject changed release/CI freshness before writing. A still-valid
record keeps its reviewed digest; post-operation verification uses the current time.
See [maintenance assessment](MAINTENANCE_ASSESSMENT.md).
The proposed profile uses the accepted-profile syntax for review; it is **not
accepted** until you deliberately supply it through `--profile`.

Save the reviewed `proposed_profile` object as `/work/accepted-profile.json`, then:

```sh
govkit migrate preview --target /work/service \
  --profile /work/accepted-profile.json --json > /work/approved-preview.json

govkit migrate apply --target /work/service \
  --profile /work/accepted-profile.json \
  --expected-digest <digest-from-approved-preview> --json
```

Keep preview/profile output outside the target when possible: adding or editing a
file within the inspected tree changes the preview's identity. Application rereads
inputs and recomputes operations; it never executes a saved list of actions. A
changed marker, contract, extension, pipeline, source profile, destination or pack
requires a fresh preview. The digest identifies the exact proposal, not its
reviewer's identity. Use the project's normal review/authorization process.

The explicit mapping retains legacy intent:

| Existing selection | Proposed capabilities |
|---|---|
| L3 | Application governance |
| L4 | Application governance and Gherkin delivery |
| L5 | Application governance, Gherkin delivery and LLM evaluation |

Agent, project type, CI and selected stack remain explicit. The proposal references
existing architecture documents and records the complete original marker, including
calibration and opt-in authority settings. Current bundled manifest selections are
reference evidence; they do not prove that an older release installed identical
bytes. All inventoried existing files are preserved, including edited contracts,
custom extensions, instructions, workflows and pipelines. No exemplars or fresh
legacy bundle are copied over them.

Missing/unknown marker versions, pre-0.7 level meanings, obsolete `ui`, unsupported
options and native-skill collisions require focused reconciliation. Use the existing
`upgrade --migrate-levels` flow for the old pre-0.7 level swap first. An already
partially declarative installation without a migration receipt is protected;
reconcile it using the existing profile/pack tools. Local legacy extensions stay
in place; this command does not automatically convert them into executable packs
or infer their semantics. Capability providers are selected from the bundled
catalog; unsupported additional selections remain unresolved.

## Installation and enforcement are separate

A ready preview means its metadata operations can be applied. It does not mean
legacy checks pass or that any CI gate is active. The preview includes read-only
local conformance findings, observed discovery evidence and bounded coverage.
After applying, GovKit reruns repository conformance and returns `verification`,
`controls`, `remaining` and canonical `maintenance` verification. Maintenance
separates resolved, remaining, unverified and new recommendations. Changed-policy
or incomplete evidence cannot establish resolution. `enforcement_parity` stays false. A broken extension,
missing schema, skipped LLM evaluation or unknown approval is not repaired by
writing profile metadata.

The accepted profile carries an always-applicable `legacy-migration` workflow:
legacy doctor/features/extensions/approval checks remain obligations. Additional
`migration:legacy-controls`, `migration:custom-controls`, `migration:ci-enforcement`
and `migration:authority` obligations preserve unmapped legacy semantics and
provider enforcement as unknown. They are deliberately blocking when no trusted
provider is configured. They are not executable-pack declarations, and a successful
pack installation does not satisfy them. Retain and reconcile these controls under
accepted policy; a task label cannot waive them. An absent authority configuration
or an explicit `source: none` adds no authority obligation; `source: pdg` retains it.
Unknown nonempty legacy authority configurations remain unresolved obligations.
No PDG connection is made or enabled.

Migrated repositories can use `govkit request plan` and the verified installed
request-planning guidance. Actual-change conformance still requires the independently
accepted policy checkout and providers described in
[CHANGE_CONFORMANCE.md](CHANGE_CONFORMANCE.md). Missing providers stay unknown.
I09 will integrate canonical maintenance findings; I10 supplies provider contracts.
Neither integration is claimed by this increment.

## Idempotence and rollback

A second application of the same reviewed profile is a no-op if its migration-owned
resources remain intact. The receipt `.govkit/migration.json` records the original
marker layout, preserved file digests/modes/timestamps, created resources and the
proposal digest. `.govkit/migration-source.json` preserves configuration provenance
and source references. Existing `.govkit/marker.json` is unchanged; a legacy flat
`.govkit` file is relocated byte-for-byte into that directory without changing its
stored version, authority, permissions or modification time.
The receipt and source record, which duplicate marker data, use owner-only
permissions instead of inheriting a potentially permissive default file mode.

```sh
govkit migrate rollback --target /work/service \
  --expected-digest <original-migration-digest> --json
```

Rollback derives ownership from the verified profile/pack lock, checks every
created resource's bytes and modes, and removes only migration-created files and
empty directories created for them. It restores a flat marker's original bytes and
metadata when applicable. User edits to migrated resources block rollback; reconcile
or back up those edits first. Other later user files and directories are preserved.
A changed flat marker (including permissions or modification time) or additional
metadata prevents destructive layout reversal.

Writes are atomic per file and roll back caught failures, including a failed flat
marker restoration. This is not a concurrent-writer transaction or a crash-recovery
journal. Keep a normal repository/filesystem backup before authorizing migration;
stop other writers during application and rollback. Receipts and digests are local
consistency records, not signed approval or tamper-proof evidence.

## Bounds and compatibility

The snapshot allows 8,192 entries, 4,096 regular files, 2 MiB per file, 64 MiB total
and 20 directory levels. Symlinks and special files in measured scope fail closed.
`.git`, `.venv`, `venv`, `node_modules`, `vendor`, `dist`, `build`, `__pycache__`,
`.pytest_cache` and `.ruff_cache` are excluded by directory/file name. They are not
migrated or assessed. Discovery has its own smaller limits, shown in the report;
incomplete discovery is never complete policy understanding. Existing destinations
remain protected even outside the snapshot. There is no implicit network lookup,
dependency installation, project-test execution or external transmission.

Updating the **developer CLI package** changes the executable and available bundled
catalog. It does not refresh a repository. Migrating or running **profile/pack
operations** changes repository metadata/resources; it does not update the CLI.
Later resource refreshes need their own reviewed pack previews and verification.

The current 0.21.x compatibility line retains `apply`, `upgrade`, level flags and
legacy manifests. New adoption uses [explicit capabilities](CAPABILITY_ONBOARDING.md).
No removal release or warning period has been announced. I13's documentation and
compatibility work does not start a deprecation clock or remove a supported input.
A maintainer must approve and announce both a concrete release boundary and warning
period after migration and release evidence is reviewed. Until then legacy inputs
remain supported and the retirement acceptance criterion stays open.

The executable pilot is [tests/wheel_migration_smoke.py](../tests/wheel_migration_smoke.py).
It installs real L3/Codex, L4/Claude Code and L5/Copilot bundles into isolated fixtures,
preserves customizations, exercises the new request path, and verifies both drift
rejection and rollback with runtime-only dependencies.
