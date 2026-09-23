# Declarative profiles

A version-1 `.govkit/profile.yaml` records desired capabilities and accepted project policy without a maturity level. The profile path is separate from the legacy `.govkit/marker.json`, which describes legacy installation state.

The profile commands support validation, preview, and metadata materialization. Use the separate [capability pack commands](CAPABILITY_PACKS.md) to resolve/install resources and execute selected controls. Profile commands do not route requests, execute checks, query releases, or migrate a legacy installation. Continue using existing `govkit apply` / `upgrade` commands for legacy installation; those commands do not silently adopt a profile merely because it exists.

## Preview and save

Start with an explicit profile outside the target or author the target's `.govkit/profile.yaml` directly:

```bash
govkit profile preview --profile ./proposed-profile.yaml --target ./service
govkit profile preview --profile ./proposed-profile.yaml --target ./service --json
govkit profile apply --profile ./proposed-profile.yaml --target ./service

# After editing the accepted profile in place:
govkit profile preview --target ./service
govkit profile apply --target ./service
```

The target must already exist. Preview reads the input and the two metadata destinations and writes nothing, including when the target has no `.govkit/` directory. Apply recomputes the preview and writes only `.govkit/profile.yaml` and `.govkit/resolution.json`. It does not create an installation marker or touch contracts, agent instructions, CI, a lock, or application files.

The preview identifies `create`, `preserve`, `update`, and `protected` operations. An existing semantically identical profile is preserved byte for byte, including comments. A different destination profile is protected: reconcile/edit that project-owned profile explicitly and preview again. Generated resolution records can be refreshed only when their content is a valid canonical record that replays consistently. Hand-edited, malformed, or unrelated content is protected; there is no force-overwrite option. Repeated application preserves unchanged files and modification times.

Symlinks in the metadata destinations are refused. In-process apply rejects changed source/destination content, stages replacements before writing, and rolls back completed replacements on caught write failures. Individual replacements are atomic; this is not a cross-process transaction or crash-recovery journal. Do not run concurrent writers against the same metadata paths.

Optional `--agent`, `--type`, `--ci`, and `--stack` values assert choices already present in the profile. Different values, including filling an unknown through a flag, fail with an instruction to edit the accepted profile. Maturity levels are not accepted on this path. Legacy flag-only commands retain their existing behavior.

Exit code 0 means the preview is consistent and its metadata destinations are writable under these ownership rules. Exit code 1 identifies invalid input, unresolved decisions, protected destinations, or a failed apply. JSON output contains the resolution and operation summaries; it does not certify that any check ran or capability was installed.

## Profile contract

The bundled [profile schema](../governance/schemas/profile.schema.json) is validated at runtime. Unknown fields and versions, duplicate YAML/JSON keys, YAML aliases, invalid authority, non-finite numbers, duplicate identifiers, and invalid policy references are rejected. YAML dates are read as strings and expiry dates must be valid ISO dates. JSON is also accepted as profile input.

Required top-level fields are `schema_version: 1`, `source`, `repository`, `capabilities`, and `policy`. `integrations`, `packs`, and `maintenance` are optional. Empty capabilities are valid for policy-only configuration. A source contains a nonempty `reference` and `authority: accepted`.

| Field | Meaning |
|---|---|
| `repository.id` | Stable project identifier; not a filesystem destination |
| `repository.project_type`, `repository.stack` | Accepted descriptions, or null/omitted when unknown; custom existing stacks are allowed |
| `integrations.agent`, `integrations.ci` | A supported agent/provider or null/omitted; selecting them does not install integration assets |
| `capabilities[]` | Desired IDs with optional explicit `requires`, `conflicts`, and `requires_context` |
| `packs[]` | Optional exact pack ID/version/source pins; local sources require a content digest; pins constrain selection without enabling a capability |
| `policy.source` | Accepted authority for mandatory policy |
| `policy.required_capabilities` | Mandatory IDs; missing selections produce an unresolved decision rather than silent enabling |
| `policy.required_checks[]` | Mandatory check IDs with an optional `capability_id`; requests cannot omit these controls |
| `policy.contracts[]` | Existing accepted source references and scopes; referenced documents are not fetched or copied |
| `policy.workflows[]` | Permitted workflow IDs, accepted sources, `when` labels, required capabilities and additional checks |
| `policy.transitions[]` | Scoped retain/improve/migrate declarations with current and target contracts, applicability and accepted exceptions |

The built-in capability vocabulary includes `application-governance`, `gherkin-delivery`, and `llm-evaluation` (LLM development and evaluation). These IDs can be declared independently. No level or implied Gherkin dependency is added. Custom IDs are permitted. `govkit pack preview` separately resolves their available providers and versions, and `govkit pack verify` checks installed resources offline.

Unknown context remains explicit. A selected capability can declare `requires_context: [stack]`, for example; that capability then reports the missing decision. Unrelated unknown context does not block metadata materialization. The preview retains independent selections and reports every unresolved decision.

Workflow `when` entries are named conditions for later request routing, not expressions evaluated here. Permitting a full-feature workflow and a small-change workflow does not select either for a request or waive required checks. A workflow can name a capability that would need setup before invocation; merely permitting that workflow does not enable it.

Transitions preserve their scopes and `applies_to` (`new`, `new-and-changed`, or `all`). A retain declaration has no target; improve/migrate declarations require target contracts. Directly conflicting declarations naming the same scope are unresolved. Scope strings are preserved, not executed as glob/path policies; detecting all overlapping scopes and enforcing exceptions/expiry belongs to conformance. Recording a target never rewrites application code or makes it the global current architecture.

Accepted authority is an explicit assertion by the project author, not authenticated approval. Do not import unreviewed discovery output as policy. Observations, confidence, proposals, installed state, and transient release responses are forbidden in a profile. The Python resolution API can carry separately supplied observations and proposals in a generated record without promoting them to accepted policy. Discovery and trusted CI policy loading remain separate work.

## Maintenance policy

`maintenance.sources` names approved HTTPS metadata locations and channels. URLs must not contain embedded credentials. `maintenance.constraints` associates a component with an approved source/channel and an intentional `pin`, `compatibility` constraint, or both. The declarations are preserved; version ordering/compatibility evaluation is supplied by the later pack and maintenance consumers.

`metadata_max_age_hours` and `assessment_max_age_hours` declare nonnegative age limits. Omitted/null limits mean unspecified, not proof of freshness. `allow_refresh` defaults to false. Setting it to true permits a future explicit refresh; it never triggers a lookup during loading, preview, or apply. Metadata lookups must not transmit repository content or posture.

The generated record always reports `release_metadata_status: not-queried`. Missing, cached, or stale release information is not treated as current. A newer release is not inferred, and a compatible intentional pin is not rejected merely because another version exists. Release inventory, age/compatibility assessment, and policy-derived urgency are subsequent maintenance features; configuration here is not their execution evidence.

## Records and examples

The [resolution schema](../governance/schemas/resolution.schema.json) validates the entire version-1 record, including its embedded desired profile and typed installation plan. Records contain the producing CLI version, canonical profile SHA-256, effective selections, reasons, provenance, unknowns, and unresolved decisions. No wall clock, absolute input path, release lookup, or implicit environment choice affects resolution. Object keys are canonicalized; ordered arrays retain their declared order.

The loader validates the record and replays its profile/context before accepting it. Removing a mandatory check or changing a digest without changing the corresponding inputs fails. Replay proves consistency, not authenticity: a caller must still establish that the embedded profile is the trusted current policy. The profile digest can be compared with the separately loaded accepted profile. Generated records are never approval or execution evidence.

Examples and their paired illustrative resolution records are bundled in the wheel:

- [Existing LLM service](../governance/examples/profiles/existing-llm-service.yaml): LLM development/evaluation without Gherkin, existing contract reference, and an offline intentional pin.
- [Gherkin service](../governance/examples/profiles/gherkin-service.yaml): no LLM capability, both small-change and full-feature permissions, and scoped architecture transitions.
- [Unfamiliar MCP server](../governance/examples/profiles/unknown-mcp-server.yaml): project type, stack, and CI remain unknown; no framework is invented.

Example source references and `example.invalid` release locations are placeholders, not accepted decisions for your repository. Replace them through your normal review process. `govkit profile apply` generates the canonical record; do not hand-copy an illustrative formatted record as managed state.
