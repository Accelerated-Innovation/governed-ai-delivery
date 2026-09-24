# Reusable provider entry points

`govkit pipeline preview`, `generate`, and `check` manage a small reusable GitHub
composite action or Azure step template. Both call the same common conformance
engine against explicit prepared inputs. Existing workflows remain in place.

This is I10b. Provider event selection, trusted checkout/admission, external
required-check configuration, maintenance evidence collection and assessment
publication remain I10c. Generated files do not activate a pipeline or establish
that a control ran or is enforced.

## Review and generate

Create accepted settings independently of the profile:

```json
{
  "schema_version": 1,
  "govkit_version": "0.21.1",
  "execute_checks": ["project:tests", "llm-exact-match"]
}
```

Use the exact release you intend to provision. It must contain these entry-point
features; the example version identifies this source build, not a claim that a
matching published package contains it. Preview resolves compatibility from the
supplied packs and checks exact version syntax; it does not query package servers
or authenticate a release. The caller provisions the isolated runtime and any
test tools/dependencies. Generation performs no installation or network access.

Execution opt-ins are explicit, unique check IDs (at most 128). An empty list is
valid: required executable checks remain skipped/unconfigured until enabled,
rather than silently passing. Enabled project/pack commands remain trusted,
unsandboxed execution under the existing conformance contract.

The list is a reusable execution allowlist. The common engine validates configured
IDs, resolves the accepted request against trusted policy and actual changes, and
executes only applicable opted-in checks. A full-feature-only check or
`defect:eligibility` may remain enabled for other requests without running there.
Pack argument mappings are validated before inapplicable entries are excluded;
unknown IDs and malformed arguments still fail. Required checks are never removed
by this filtering. Direct local execution selections remain strict by default.

```sh
govkit pipeline preview --target /work/service \
  --profile /work/accepted/profile.json --settings /work/accepted/pipeline.json --json
govkit pipeline generate --target /work/service \
  --profile /work/accepted/profile.json --settings /work/accepted/pipeline.json \
  --accept-digest REVIEWED_PREVIEW_DIGEST --json
govkit pipeline check --target /work/service \
  --profile /work/accepted/profile.json --settings /work/accepted/pipeline.json --json
```

The default profile is `TARGET/.govkit/profile.yaml`. Additional `--pack-source`
paths supply explicit local snapshots. The profile chooses `github` or `azure`.
Preview includes the exact generated content, catalog, pins, required caller
configuration and proposed file operations. It writes nothing. Generation requires
the digest of the exact current preview, including source bytes and destination
bytes/modes/timestamps. Reconcile inputs and preview again after a change.

| Provider | Generated reusable file |
|---|---|
| GitHub | `.github/actions/govkit-conformance/action.yml` |
| Azure | `ci/azure/govkit-conformance.generated.yml` |

`.govkit/pipeline-lock.json` records replayable generation inputs and content.
An existing unmanaged file, edited template or invalid/edited metadata remains
protected. There is no force-overwrite option. Provider switches require explicit
reconciliation of the existing integration; generation does not remove it.
Unmodified generated files can update after a newly approved preview. Repeated
generation of the same state preserves bytes and timestamps.

Writes are individually atomic, staged and rechecked before replacement. Caught
failures restore completed files and ordinary modes/timestamps; newly created
empty directories are removed. Generation opens directory components without
following symlinks, then uses those directory handles for staging, replacement,
rollback and cleanup. Swapping a pathname to an outside symlink cannot redirect
these writes. Generation requires platform support for these operations and
rejects symlinked target ancestors; unsupported platforms fail before writes.
This is not a concurrent-writer transaction or
crash-recovery journal. Concurrent edits that prevent safe rollback are reported,
not overwritten. Local inputs and generated metadata are bounded to 4 MiB;
encoded runtime bindings are bounded to 64 KiB. Oversized proposals fail before
writes, so generation cannot create a record that its reader cannot consume.

## Prepared runtime inputs

The trusted caller supplies these values to either provider entry point:

| Input | Contract |
|---|---|
| `python` | Absolute executable path to an isolated Python with the exact pinned GovKit build |
| `target` | Absolute path to the inspected Git checkout |
| `policy_target` | Absolute path to a separate, caller-trusted accepted profile and installed pack closure |
| `request` | Absolute path to the caller-accepted normalized request JSON |
| `base` | Full 40- or 64-character trusted Git base commit SHA, already available locally |
| `pack_arguments` | Optional absolute path to a JSON mapping of check IDs to argument arrays |
| `observed_at` | Optional explicit timestamp for reproducible replay; does not authenticate CI time |

The caller must prepare complete Git history, accepted intent, independent policy
and pinned resources. Nothing in an editable target workflow authenticates those
inputs. Keep the invocation and its template under independently enforced review;
load reusable definitions from a trusted immutable revision rather than the
unreviewed change. Configure event coverage, minimal permissions, required status
checks and reviewers externally. Do not expose privileged credentials to inspected
project commands. These are caller requirements, not capabilities activated here.

Inputs bind through provider environment values, never shell interpolation. Both
templates run the pinned module with Python isolation. Before executing checks it
verifies the exact installed and lock-recorded GovKit versions, accepted profile
digest and replayed installed pack closure against the generated binding. An old
resolver version in an otherwise unchanged lock requires explicit reconciliation.
It then calls `inspect_change`, which
recomputes requirements from trusted policy and actual Git changes. The catalog is
not an allowlist; request labels, a changed plan and missing prerequisites cannot
waive mandatory checks. Different accepted requests reuse the same entry point.

Output is the existing `change-results/v1` JSON on stdout with the same exit code
as local conformance. Required failures/unknown/skipped evidence remains failing.
Results are not automatically uploaded or converted into authenticated provider
evidence. Explicit check commands can have their own side effects.

## Provider differences and configuration checks

GitHub emits composite-action metadata with required inputs and a Bash step.
Runtime validation also checks missing values because GitHub's `required` input
metadata alone does not enforce them. Azure emits typed string parameters and a
Bash step template, which an existing pipeline must include. Neither reusable
format owns workflow triggers, job permissions, checkout or branch protection.
Both currently require a Bash-capable Linux/macOS runner; Windows is unverified.
See [GitHub's metadata reference](https://docs.github.com/en/actions/reference/workflows-and-actions/metadata-syntax)
and [Azure's template reference](https://learn.microsoft.com/en-us/azure/devops/pipelines/process/templates?view=azure-devops).

`check` compares generated files with the explicit desired profile/settings and
returns `configuration: current`, `missing`, or `drifted`; missing/drifted states
exit unsuccessfully. Malformed/protected metadata produces a validation error.
Execution, activation and enforcement remain `unknown`, even for current files.
Follow-up requirements identify the caller configuration still needed. This result
is not yet a canonical maintenance/provider evidence adapter; that is I10c.

The [bundled examples](../governance/examples/pipeline/README.md) include paired
golden entry points. Tests run the actual generated scripts against local Git
fixtures for all three agents, both providers, bounded/full-feature/LLM requests
and real failing evaluations. This demonstrates shared-engine behavior and
serialization, not live hosted-provider enforcement.
