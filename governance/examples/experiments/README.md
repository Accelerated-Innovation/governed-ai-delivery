# Experiment record examples

Each folder is a minimal synthetic repository for one feature,
`features/discovery`. Its `architecture_preflight.md` holds only the
machine-readable `preflight_outcome` block. `expected.json` lists the findings
and experiment states that `cli/experiment_store.assess_feature` must produce
at the recorded clock. `tests/test_experiment_store.py` asserts them.

| Folder | Situation | Ready for completion |
|---|---|---|
| `boundary` | A change inside accepted contracts. No experiment is needed | Yes |
| `required` | Preflight requires `EXP-001`, which is still planned | No: outstanding |
| `revised` | `EXP-001` failed and the design was revised. `EXP-002` passed and the preflight relies on it | Yes |
| `relied` | `EXP-001` passed, was adopted, and has not expired | Yes |
| `stale` | The acceptance criteria changed after `EXP-001` ran, so the preflight's reliance is stale | No: error |
| `synthetic` | The experiment requires application evidence, but the result is a synthetic fixture declared `passed` | No: errors |

All results are labeled `synthetic-fixture` and describe a hypothetical Value
Builder-style discovery feature. They test GovKit's record handling. They are
not application evidence, and they establish nothing about any runtime or about
SOAA conformance.
