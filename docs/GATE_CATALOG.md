# Shared gate contracts

`govkit pipeline catalog` describes logical conformance controls from an explicit
accepted profile and local pack snapshots. It reads no ticket service, executes no
checks, writes no workflow and queries no CI provider.

```sh
govkit pipeline catalog --target /work/service --json
govkit pipeline catalog --profile /work/accepted-profile.json
govkit pipeline catalog --profile /work/accepted-profile.json \
  --pack-source /work/trusted-pack-snapshot --json
```

The default profile is `TARGET/.govkit/profile.yaml`. Additional pack snapshots
extend the bundled catalog and use the existing dependency/version resolver;
ambiguous providers require explicit profile pins. The command returns exit 1
with a structured catalog if composition has unresolved decisions. Invalid input
produces a validation error. No default installation or policy acceptance occurs.

## What a gate declares

The versioned `gate-catalog` record contains immutable `GateSpec` declarations:

| Field | Meaning |
|---|---|
| `id` | Stable logical control ID, normally the common engine's check ID |
| `requirements` | Additive repository, capability, workflow or architecture requirements, with policy sources, selectors, scopes and blocking policy |
| `blocking` | At least one requirement is blocking when applicable; individual conditions remain in `requirements` |
| `dependencies` | Logical relationships; controls depend on the shared conformance entry point |
| `commands` | The single entry point's argument contract with explicit trusted-input placeholders |
| `triggers`, `path_filters` | Pull request/push/manual intent; no pipeline path filter can omit the entry point |
| `permissions`, `secrets`, `configuration` | Known requirements or explicit unknown provider needs; no credentials are stored |
| `evidence` | Expected common result contract, not a claim that it was produced |

All controls share one `govkit conform` invocation. They are **not separate CI
jobs** and must not cause the engine to execute repeatedly. The entry point names
`--request`, `--base` and a separate `--policy-target`; the caller must bind these
to trusted policy/resources, reviewed intent and the actual change base. Placeholders
are descriptive arguments, not a ready-to-run shell command. Executable checks
still require the existing explicit opt-in and trusted command/pack configuration.

Repository requirements cannot be demoted by an advisory pack contribution or a
conditional workflow requirement. Architecture scopes remain control scopes and
do not become pipeline path filters. Unknown providers or missing capabilities are
not silently removed. Gate dependencies, scopes, unique IDs, exact version pins
and blocking-policy consistency are validated when parsing a record.

The catalog is stable across individual requests. It lists known controls and
accepted workflow capability requirements; it is **not a complete runtime check
allowlist**. The common engine continues to resolve additive workflow rules,
actual Git changes, expanded scope, architecture, evidence and approvals. An
edited catalog or a chosen workflow label cannot authorize skipping that process.

## Identity and limits

The record includes profile identity, provider, resolved capability/pack pins and
a consistency digest. Equivalent provider selections have the same logical gate
declarations; the profile digest and provider annotation may differ. Composition
pins name exact versions selected from supplied snapshots. They do not certify
installed resources, publisher authenticity or package availability on a server.

`ready` means the catalog's pack/profile composition resolved. Every record keeps
`execution: not-run` and `enforcement: unknown`. A null permissions/secrets field
means that the control's provider needs are unmeasured. Schema and digest validation
do not authenticate policy or turn metadata into execution evidence.

I10b adds pinned GitHub/Azure renderers, protected preview/check/generate,
trusted execution wiring, configuration drift, maintenance integration and provider
evidence. This increment neither changes branch protection nor publishes artifacts.
External enforcement and reviewer requirements remain separate platform settings.

## Legacy compatibility

Bundled agent manifests reference `builtin:legacy-ci-v1`. The loader expands
`governance/ci/legacy-selection.json` into the existing ordered legacy input before
the pure adapter runs. The three agents no longer maintain duplicate CI dispatch
tables. Custom manifests with inline `variants.ci` keep their behavior; an inline
table and shared reference together are rejected rather than ambiguously merged.
Only the named bundled reference is supported; no arbitrary URL/path is loaded.

The shared legacy table retains level/type/stack selection, categories, ordering,
and existing GitHub/Azure templates. This compatibility data does not drive new
profile selection. Template installation is still not evidence that its jobs ran.
All 258 frozen legacy selections remain unchanged. The installed-wheel pilot also
exercises independent capabilities and both providers for all three agents.

See the [bundled example](../governance/examples/pipeline/README.md),
[change conformance](CHANGE_CONFORMANCE.md), and [legacy CI templates](../ci/README.md).
