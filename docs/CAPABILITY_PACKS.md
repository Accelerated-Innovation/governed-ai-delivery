# Capability packs

`govkit pack` resolves desired capabilities to explicitly available packs, previews owned file operations, and pins a portable resource closure. It uses the existing bundled extension distribution and explicit local pack directories. Preview, apply, verification, and check execution perform no registry or release lookup.

## Select, preview, install

Author or review the project's [declarative profile](DECLARATIVE_PROFILES.md), then save it with `govkit profile apply` or edit `.govkit/profile.yaml` directly. The profile remains project-owned policy. Pack apply requires that the previewed profile matches the accepted target profile.

```bash
govkit pack list
govkit pack preview --target ./service
govkit pack preview --target ./service --json
govkit pack apply --target ./service
govkit pack verify --target ./service
```

`--profile proposed.yaml` supports a read-only what-if preview. Applying that proposal requires accepting the same profile at the target first. A legacy marker is not required. No full architecture library, feature workflow, CI template, or project instruction file is installed implicitly.

Two minimal example profiles are bundled: [LLM evaluation without Gherkin](../governance/examples/packs/llm-without-gherkin.yaml) and [Gherkin without LLM evaluation](../governance/examples/packs/gherkin-without-llm.yaml). Replace their policy references through project review. The earlier profile-only examples deliberately include additional project-specific checks such as `security`; installing their packs requires an explicit provider for each such check.

## Resolution and pins

Desired capabilities, the available catalog, and installed resources are distinct. The resolver chooses the highest compatible version of one provider, backtracking across shared dependency constraints. A missing capability, cycle, conflict, incompatible version, unsupported project type/agent, duplicate skill/check ID, or unmet minimum GovKit version blocks apply. Dependencies carry a rationale. Different providers require an explicit pin; listing a pack pin alone does not enable its capabilities.

Add explicitly trusted local pack directories with repeatable `--source` flags:

```bash
govkit pack list --source ./vendor/team-quality --json
govkit pack preview --target ./service --source ./vendor/team-quality
govkit pack apply --target ./service --source ./vendor/team-quality
```

These are exact pack directories containing `manifest.yaml`, not registry URLs. Existing `govkit extension add --from-git ... --ref ...` remains the explicit distribution adapter for Git sources; pass its vendored pack directory to `--source` after reviewing it. The new command does not clone or resolve floating remote branches.

Use the digest printed by `pack list` to select a local override in the profile:

```yaml
packs:
  - id: team-quality
    version: 1.0.0
    source: local
    digest: REPLACE_WITH_THE_64_CHARACTER_SHA256_FROM_PACK_LIST
```

Local pins require an exact version, source and content digest. Bundled pins require version/source and may include a digest. When bundled and local sources provide the same ID, selection is unresolved until explicitly pinned. Different content at one version also requires a digest pin. Version comparisons use `packaging` version/specifier semantics (`>=1,<2`, `==1.0.0`); `*` means unconstrained. No network access or implicit local override is involved.

## Pack contract

The existing extension manifest gains an optional versioned `capability_pack` block, validated with the bundled [schema](../governance/schemas/capability-pack.schema.json). A minimal example:

```yaml
id: team-quality
name: Team quality
version: 1.0.0
govkit_min_version: 0.21.1
extension_type: skills
contract_sets: []
skills:
  - path: skills/team-quality
    install_as: team-quality
capability_pack:
  schema_version: 1
  provides: [team-quality]
  requires: []
  conflicts: []
  resources:
    - {path: README.md, kind: advisory}
  checks:
    - {id: quality, path: checks/quality.py, required: true}
```

The `skills` section and `checks` contribution are independently optional. Dependencies name `capability`, `version`, and a nonempty `reason`. Optional `agents` narrows supported integrations. Root `supported_project_types` constrains applicability. Resource kinds are `advisory`, `contract`, `defaults`, `example`, and `reference`; copying a resource never promotes it to accepted project policy. Declare every non-skill resource a pack needs. Skill directories include all their files, including references. Entry points must be standalone Python scripts; additional resources must be declared explicitly.

Legacy manifests are normalized from their contract capabilities, skill declarations, implementation profiles, templates and licenses. References to another `extensions/<id>/...` contract add an explicit dependency with its reference as the reason. `supported_levels` survives only as legacy provenance. New resolution does not infer a level or enable Gherkin from an LLM capability. Legacy installation commands retain their level semantics and original layouts. Legacy contract prose may still refer to that layout; the new path pins these documents as reference material rather than rewriting or accepting them as project architecture.

## Portable resources and ownership

Selected manifests and declared resource closures are stored at `.govkit/packs/<id>/<digest>/`. The digest covers each relative filename and its bytes. The versioned `.govkit/pack-lock.json` records selected source/version/digest, dependency edges/reasons, the accepted profile snapshot/digest, required checks, resource hashes and owners. Local absolute source paths are never recorded. Commit the profile, lock, pinned resources and native skill copies together for offline use on another machine.

One neutral skill source installs at the agent's native directory:

| Agent | Skill root |
|---|---|
| Claude Code | `.claude/skills` |
| Codex | `.agents/skills` |
| Copilot | `.github/skills` |

Frontmatter is identical across agents. Relative references inside a skill remain local to that skill. The optional `{{pack_root}}` token expands to the pinned pack's path relative to the repository root. No machine-specific absolute path is embedded.

Preview reports `create`, `preserve`, `update`, `remove`, or `protected` per file, including its owner and before/proposed digests. A prior valid lock must prove ownership before an existing file can be replaced or removed. User-authored files, modified native skills and edited lock metadata are protected. There is no force option. Reapplying unchanged inputs preserves bytes and modification times. Removing a capability removes only its unedited owned files; other files in those directories remain untouched. Empty directories can remain.

Missing or modified pinned resources invalidate the lock; restore the committed lock/resource set before attempting an update. Native skill edits can be moved to a separate user-owned skill or represented by a reviewed local pack. Reconcile ownership explicitly rather than deleting a lock to claim existing files. Symlinks, path escapes, stale previews and incompatible requirements fail before installation. Writes are staged, replaced per file, and rolled back on caught failures; this is not a cross-process transaction or crash-recovery journal. Avoid concurrent writers.

`pack verify` replays manifests and the accepted profile, checks owned paths/hashes, and validates the running GovKit minimum. It needs no original local source directory. Previewing a change to a local selection requires its explicit source again; the pinned `.govkit/packs/<id>/<digest>` directory can be supplied as that local source for offline work. Ownership/digests prove consistency, not source authenticity or approval.

## Native skill namespace updates

GovKit-owned capability packs install their native skills under `govkit-` names
for every supported agent. The application-governance 1.1.1, gherkin-delivery 1.0.1
and llm-evaluation 1.0.1 pack revisions correct previously unprefixed destinations:
`govkit-application-governance`, `govkit-gherkin-delivery`, and
`govkit-llm-evaluation`. The existing `govkit-request-planning` name is unchanged.
Capability IDs and neutral source paths stay unchanged. Third-party/custom packs
retain their explicitly declared namespaces (for example, `otter-`); these are not
renamed by the runtime.

An existing pinned lock still verifies its original files offline. Upgrading the
CLI alone does not rename an installed skill. Review `govkit pack preview` and
explicitly apply the reviewed update; an exact old pack pin must first be reconciled
in the accepted profile if you intend to select the new version. Keep the prior
lock/resource set in version control for rollback.

The normal ownership rules remove an old native file only when the prior lock owns
it and its content is unchanged. Modified old files or existing unowned namespaced
destinations block apply without writes. Unrelated files under the old directory
remain intact, so an empty or partially populated old directory can remain. A
pre-existing user skill at an unprefixed name is left alone by a fresh installation.
Do not delete locks or force an update to conceal a collision. Legacy `extension
add` does not migrate pack locks or remove old skill copies; review its separate
installed files before invoking an updated skill.

## Independent controls

```bash
# Put GovKit options before CHECK_ID; everything after -- goes to the control.
govkit pack check --target ./service llm-exact-match -- --results evaluation-results.json
```

Check execution verifies pinned resources and current accepted policy, then invokes the selected script with the running Python in isolated mode, in the target directory. It does not load a skill or depend on an agent session. Missing/edited native skills do not waive or prevent the independent control. Modified pinned code is refused. Selecting a source is a trust decision: this command executes that source's code and is not a sandbox.

The `llm-evaluation` worked pack contains a real offline exact-match evaluator for supplied `{cases: [{id, expected, actual}]}` JSON. Exit 0 means every nonempty, uniquely identified case matched; 1 means mismatches; 2 means invalid input. Output contains case IDs and counts, not model responses. It does not invoke a model or prove the records' origin, freshness, completeness, or broader model quality. Its example records are demonstrations, never project evidence.

Profile `policy.required_checks` must have an executable provider among selected packs. Removing an optional capability cannot silently remove a policy-required control: the next plan remains unresolved until a provider is retained or the accepted policy is explicitly changed. Pack preview/apply records `execution: not-run`; loading a skill is never proof that a check passed. Workflow routing, authenticated evidence protocols and maintenance/update assessment remain later increments.
