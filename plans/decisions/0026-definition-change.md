# ADR 0026: A change cannot weaken the definition it is judged by

Status: Proposed with the PR for #267. Merging that PR accepts the contract below.

## Context

A feature is done when its scenarios pass and its criteria are met (ADRs 0022 to 0024). An agent given that stop condition can reach it by editing the definition: delete a failing scenario, loosen a step, lower a threshold. The evidence report judges the definition as it is now, so it cannot see this.

Actual-change conformance (ADR 0007) already captures every file at an explicit comparison base and in the working tree. The plan's L06 lists eight protections. This ADR covers the three that need no declaration from the project: scenarios, shared steps and criteria. Bound tests, test support and other protected files follow in L06b.

## Decision

1. **A check on the captured change.** `change:definition` compares each changed `features/<name>/acceptance.feature` and `features/<name>/eval_criteria.yaml` with its bytes at the comparison base. It reads the snapshot `change_scope.py` captured and runs nothing. `definition_change.py` is pure.
2. **Adding is allowed.** A new scenario, a new criterion or a new definition file passes.
3. **What existed must still be there, unchanged.** A scenario at the base must exist with the same identifier and revision digest, as `scenario_identity.py` computes them. A comment or trailing space is not in the digest and is not a change.
4. **Shared steps are covered.** A `Background` is in no scenario's digest. So each scenario also carries a digest of the `Background` blocks that cover it, at feature and `Rule` level. A changed, added or removed `Background` above an existing scenario is a finding, and so is moving a scenario under a different one. A `Background` that covers only new scenarios is not.
5. **Criteria are compared by name.** An existing criterion must be present in the same list with equal parsed content, so reordering and reformatting pass. Equality keeps types apart: `1` and `true` differ, while `1` and `1.0` do not. Anything else in the file must be equal too. This is stricter than the graph, which gives every criterion the file's digest.
6. **A file whose criteria are not all named is compared whole.** Any change to its parsed content is a finding. No rule is defined for the data form.
7. **A finding fails the check and means a person must look.** GovKit cannot tell a correction from a weakening and does not try. Each finding has a stable code and names the file and the scenario or criterion. Messages hold no step text or values.
8. **A base that cannot be compared is unknown**, never a pass. A current file that can no longer be identified is a finding.
9. **The check is present only when the change touches a definition file.** Every other change report is unchanged, including the eight bundled pilots.

## Alternatives considered

- **A check in `govkit evidence`.** The report would need a base, and would then judge the change as well as the results. Conformance already owns the base and the snapshot.
- **Always include the check.** It would pass with nothing to compare in every existing report and change every saved one.
- **Use the graph's criterion digest.** Adding one criterion would mark every other criterion as altered.
- **Judge whether an edit weakens.** A tightened threshold and a loosened one look alike without knowing the metric's direction, and a reworded step cannot be judged at all.
- **Cover `Background` by adding it to the revision digest.** The digest is the engine's rule and must match it.

## Consequences

- A legitimate correction to an existing scenario or criterion fails conformance until a person accepts it. How acceptance is recorded is not decided here; today the reviewer chooses a comparison base after the accepted change.
- Renaming a scenario without a `@scenario:` tag reads as a removal and an addition.
- The check needs the `--request`, `--base` and `--policy-target` inputs of change conformance. A level-free entry point and the verdict are L07.
- The codes are a public contract: add, never rename.
