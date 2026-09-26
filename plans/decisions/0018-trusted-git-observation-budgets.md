# ADR 0018: Trusted Git observation budgets

Status: **Accepted for implementation on merge of
[PR #211](https://github.com/Accelerated-Innovation/governed-ai-delivery/pull/211);
proposed until that merge.** The PR's recorded merge is the acceptance event for
this design and its entry in the implementation plan's decision log. No further
status edit is required to make that acceptance effective.

Runtime implementation remains pending. Selecting a larger budget for any
consumer still requires a separate policy review and protected caller setup;
design acceptance does not adopt consumer policy or activate enforcement.

## Problem and evidence

The actual-change observer captures complete Git-visible baseline and working
trees. Its defaults are 2,048 files per inventory, 1 MiB per file, 16 MiB per tree
and 256 changed paths. A tracked generated asset can exceed the per-file bound
even when the repository fits every other bound. PR #210 makes that failure
actionable; it intentionally does not change the supported configuration.

The observer's internal `max_bytes` argument permits an isolated feasibility
trial. Five real-Git controls run against merged source `a4c3949` demonstrate:

| Input and explicitly selected function-level budget | Result |
|---|---|
| 5 MiB tracked file, default 1 MiB per-file limit | Incomplete, per-file diagnostic |
| Same-sized fixture, explicit 8 MiB per-file limit | Complete |
| Exactly 8 MiB tracked file, explicit 8 MiB limit | Complete |
| 8 MiB + 1 byte tracked file, explicit 8 MiB limit | Incomplete, per-file diagnostic |
| 6 + 6 + 5 MiB files, explicit 8 MiB per-file limit | Incomplete, unchanged 16 MiB total limit |

Every trial preserves file bytes, modes, mtimes and the index. A separate private
read-only trial captures the actual selected pilot diff with the candidate bound;
its coordinates and measurements remain in the private pilot record. This is
evidence about the existing observation function, not a successful public CLI
configuration, conformance result, authenticated provider run or accepted policy.
The existing 31 scope-limit regression/control cases also pass.

The current `change-policy` schema **rejects** the proposed setting below. Do not
copy it into a live configuration until the complete implementation is delivered.

## Proposed decision

Preserve every current default. Add one optional setting to the accepted
conformance configuration referenced by `profile.policy.conformance`:

```yaml
# Proposed fragment only; unsupported by the current schema/runtime.
observation_limits:
  max_file_bytes: 8388608
```

`max_file_bytes` is an integer from 1 through 8,388,608 inclusive; omission resolves
to 1,048,576. Reject booleans, floats, nulls, unknown properties, negative/zero
values and values above the ceiling. Keep the file-count, tree-content and changed
path limits fixed in this first implementation. Their future configurability is
not part of this decision. The 8 MiB ceiling is a bounded initial product choice
supported by the trials, not a promise to inspect arbitrary repositories.

Use one immutable, validated limits value and shared defaults across observers.
The repeated calls listed below establish a concrete need for that shared value;
do not introduce a general resource-policy framework. An omitted setting must
retain existing behavior. Invalid or unavailable policy cannot silently select a
larger budget or produce passing evidence.

No target-controlled CLI flag, environment variable, request label, saved report
field or discovered convention may choose a raised limit. No extension/glob
exclusion, ignored tracked file, automatic asset deletion or global default
increase is proposed. A budget is permission to read bounded content, not
permission to omit a control or accept the architecture of that content.

## Trust and admission bootstrap

Local conformance continues to require a separately selected trusted policy
checkout. That path is a caller assertion, not authenticated approval. Resolve
the setting through the existing accepted conformance reference and retain its
byte digest in request-plan evidence. Do not read it from the inspected change's
profile/configuration. Existing 64 KiB policy/reference limits stay unchanged.

Protected admission needs particular care: it currently checks both checkouts
before loading the accepted profile/lock. Simply loading a value from a dirty
policy worktree to relax its own cleanliness check would be circular.

Before using a nondefault limit for provider admission, bind the bootstrap inputs
to the caller-selected full policy revision and pipeline profile pin. Read and
validate only the bounded profile and referenced conformance bytes, verify their
paths/modes and equality with the corresponding pinned Git blobs, and check the
checkout's HEAD. This narrow bootstrap establishes the budget source only; it
does not establish whole-checkout cleanliness or run commands. Then capture both
complete checkouts with the resolved limit and retain all existing clean-tree,
revision, request-digest and provider-event checks. Recheck the budget-source
identity before execution and in final stability assessment. Missing, dirty,
symlinked, substituted or changed bootstrap inputs must withhold execution.

Callers unable to establish that binding must remain incomplete/unadmitted. Do
not fall back to proposed target policy or accept a supplied JSON claim of trust.
This remains bounded inspection, not an operating-system execution sandbox or a
guaranteed process-memory ceiling; the total-content bound applies per tree.

## Complete integration boundary

Ship support across these consumers together. A successful direct function call
does not establish readiness of any of them.

| Consumer | Required behavior |
|---|---|
| `change_conformance.inspect_change` | Resolve the trusted budget once; use it for initial capture and final recapture; changing its accepted source invalidates the run. Retain sensitive-path routing and mandatory controls. |
| `provider_admission.admit_run` / `pipeline_runtime.run_bound` | Perform the pinned bootstrap above; use the same resolved budget for policy and target cleanliness, then common-engine execution. No provider-specific authority shortcut. |
| `pipeline_evidence` | Select current limits from the assessment's accepted policy, never from imported runtime/provider success claims; require matching budget source, repository/change/policy identities and freshness when recapturing. Imported success remains unverified. |
| `maintenance_inventory` / canonical assessment | Resolve an explicitly present accepted local policy under bounded reads, record its source identity and limitations, and use its validated budget for Git capture. A locally declared policy does not authenticate provider approval. Missing policy retains defaults; invalid declared policy retains an actionable unknown/incomplete result. |
| GitHub/Azure entry points | Continue to share the common engine and caller pins. No raw environment/template override that bypasses policy validation. |
| Reporting / saved-result replay | Preserve effective-budget provenance and old-record semantics; private paths and configuration bytes stay out of posture exports. |

Policy, runtime and recapture must not independently guess a limit from the
largest observed file. A change to accepted limits requires reassessment even
when the compared content itself did not change.

## Record compatibility

Record the resolved limit, fixed companion bounds and accepted-source digest as
observation provenance, and bind them into canonical identities. The source
digest already contributes to workflow evidence; it must also be available to
admission and maintenance/evidence comparison without trusting a supplied report.
Do not overload a human diagnostic string as the machine-readable authority.

Preserve deterministic replay of existing records as observations made with the
historical defaults. Missing budget provenance can never imply an expanded
limit. Use a new writer/schema version wherever adding the provenance changes a
strict serialized contract or its identity rules; keep the old reader and its
original digest semantics. Inventory, nested result consumers, posture exporters,
schemas and examples must be updated consistently. Exact wire field placement
and version numbers are implementation details to settle with replay fixtures
before activation; this ADR does not retroactively reinterpret version-1 records.

## Test-first implementation and acceptance

After design acceptance, begin with failing tests at the actual boundaries:

1. Omitted policy retains defaults; valid explicit values resolve deterministically;
   invalid types, unknown fields and above-ceiling values are rejected.
2. A default oversized target remains incomplete. The accepted candidate captures
   all Git-visible files; just-over-file and over-total inputs still block.
   Include staged, unstaged, deleted, binary, unsafe-kind and long escaped paths.
3. Target policy, labels, environment values and imported reports cannot enlarge
   the budget. Dirty/wrong-revision policy and changed bootstrap bytes prevent
   admission/command execution. Include a policy checkout containing large assets
   so the bootstrap problem is exercised rather than hidden by tiny fixtures.
4. Mutation of accepted budget inputs between initial capture, execution and
   recapture invalidates evidence. Provider/local parity uses the same value.
5. Maintenance and provider evidence agree on scope and source identity; absent
   trust/freshness remains unknown. All existing mandatory checks survive.
6. Historical default records replay with original digests; incompatible/new
   records fail closed in old readers. New records and privacy-filtered exports
   reject omitted/substituted provenance and retain distinct states.
7. Real installed-wheel and both-provider/all-agent pilots exercise accepted
   larger files, positive/negative controls and unchanged source snapshots.

Use existing focused tests first, then required fast and relevant wheel/provider
checks. Trials above do not satisfy these unimplemented integration criteria.

## Alternatives and next review

Removing generated builds from consumer tracking may be appropriate application
work, but requires that repository's build/deployment owners to review the
consequences. It does not eliminate the need to inspect large files in the
selected comparison base. Do not rewrite history or move the comparison base to
hide the removal. A global default increase would enlarge resource use for every
consumer. Exclusions or budgets inferred from changed assets would let proposed
content influence its own coverage. Neither is recommended.

The requested review decision is to accept this bounded trusted-policy design
for implementation, or select a separate consumer asset/build change instead.
Neither choice merges the private baseline, adopts consumer policy, changes
branch protection, activates deployment, supplies participant consent or closes
the remaining #147/#149/#142 acceptance criteria. Continue the private bootstrap
review independently; use only a reviewed/merged revision for later enforcement.
