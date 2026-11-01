#### SOAA applicability

Copy this into `features/<feature>/architecture_preflight.md` Section 15a.
Condition IDs and controls come from
`docs/backend/architecture/SOAA_APPLICABILITY.md`. Replace each `unknown` with
`applies` or `not-applicable`; an unknown condition stays unresolved. Keep the
headings below `### 15a` so the block stays inside that section.

| Condition | Status | Controls or omission reason | Verification family |
|---|---|---|---|
| `adaptive-run` | unknown | | |
| `skill-activation` | unknown | | |
| `untrusted-input` | unknown | | |
| `external-read` | unknown | | |
| `external-mutation` | unknown | | |
| `multi-tenant-data` | unknown | | |
| `model-selection` | unknown | | |
| `workflow-switching` | unknown | | |
| `persistent-memory` | unknown | | |
| `human-takeover` | unknown | | |
| `delegation` | unknown | | |
| `executable-assets` | unknown | | |

For `not-applicable`, fill `reason`, `evidence` (the verified absent or
disabled interface), `owner` and `change_trigger`. For `applies`, leave
`evidence` empty or cite the design record, and name at least one verification
family from *Minimum verification* in
`docs/backend/architecture/SKILL_ORIENTED_AGENT_ARCHITECTURE.md`. The feature
plan links each affected control boundary to one of those families.

```yaml
soaa_applicability:
  version: 1
  conditions:
    - {id: adaptive-run, status: unknown, reason: "", evidence: "", owner: "", change_trigger: ""}
    - {id: skill-activation, status: unknown, reason: "", evidence: "", owner: "", change_trigger: ""}
    - {id: untrusted-input, status: unknown, reason: "", evidence: "", owner: "", change_trigger: ""}
    - {id: external-read, status: unknown, reason: "", evidence: "", owner: "", change_trigger: ""}
    - {id: external-mutation, status: unknown, reason: "", evidence: "", owner: "", change_trigger: ""}
    - {id: multi-tenant-data, status: unknown, reason: "", evidence: "", owner: "", change_trigger: ""}
    - {id: model-selection, status: unknown, reason: "", evidence: "", owner: "", change_trigger: ""}
    - {id: workflow-switching, status: unknown, reason: "", evidence: "", owner: "", change_trigger: ""}
    - {id: persistent-memory, status: unknown, reason: "", evidence: "", owner: "", change_trigger: ""}
    - {id: human-takeover, status: unknown, reason: "", evidence: "", owner: "", change_trigger: ""}
    - {id: delegation, status: unknown, reason: "", evidence: "", owner: "", change_trigger: ""}
    - {id: executable-assets, status: unknown, reason: "", evidence: "", owner: "", change_trigger: ""}
```

#### Writer map (changed rows only)

List only the rows this feature adds or changes in the system-level writer map.
State "No other rows change."

| Aggregate | Trusted writer | Authorization rule | Version or fencing check | Durable commit | Evidence path |
|---|---|---|---|---|---|
| | | | | | |

#### Logical roles (changed rows only)

| Logical role | Implementation owner | Ports | Authoritative state | Trust boundary | Verification |
|---|---|---|---|---|---|
| | | | | | |
