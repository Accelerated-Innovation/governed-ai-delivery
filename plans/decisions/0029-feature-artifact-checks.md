# ADR 0029: Feature artifact checks chosen by the profile, not a level

Status: Proposed with the PR for #273. Merging that PR accepts the contract below.

## Context

`govkit validate` checks a feature's artifacts: that the five files exist, that the Gherkin is well formed, that `nfrs.md` has no placeholders, that `eval_criteria.yaml` is valid, and so on. It chooses the checks from a legacy level. An installation made from a profile has no level, so nothing checks these artifacts there, and `govkit conform --feature` (ADR 0028) can answer done for a feature with no plan or an invalid criteria file. Issue #220 lists the features that work only through a level.

The maintainer decided on 2026-11-26:

- The accepted profile's capabilities select the checks.
- Every check is required except the agent's own forecast.
- The profile's `project_type` picks the `eval_criteria` schema, and nothing is guessed when it is not set.
- Only the selected feature is checked in this increment.

## Decision

1. **Selection.** With `--feature`, `gherkin-delivery` in the accepted profile selects the seven level 4 checks. `llm-evaluation` adds the five level 5 checks. A profile without `gherkin-delivery` gets none, and its reports are unchanged.
2. **One check each.** Each is a conformance check named `feature:<identifier>`, with the identifier `govkit validate` already uses (ADR 0021). The check functions are `validate`'s own.
3. **States.** A failure fails the check, which is work for the agent. A warning is unknown, which is never a pass and needs a person.
4. **The forecast is advisory.** `feature:eval-prediction` is not required and is always unknown, whether the forecast is well formed or not. A forecast is the producer's own assertion.
5. **The schema.** `repository.project_type` in the accepted profile picks the backend, data or UI `eval_criteria` schema, by the same mapping the legacy marker uses. The schema is the one bundled with the installed GovKit. A copy in the inspected tree is not read. With no project type, or one with no schema, the file's structure is still checked and schema validation is unknown.
6. **The profile is read from the trusted policy checkout,** as every other accepted input is. The feature's files are read from the change checkout.
7. **The feature's files are not trusted.** Before any check reads them, a feature directory that is a symbolic link, or that directly holds a link, a non-regular file or a file larger than 1 MiB, makes every check unknown and names the file.
8. **Reserved identifiers.** A run with `--feature` is refused when a configured command or pack check already uses one of these identifiers.

## Alternatives considered

- **Accepted policy lists each check.** Finest control, but every project must write the list before anything runs.
- **Always, when a feature directory exists.** It imposes the five-artifact contract on projects that never chose it.
- **Only the checks on the definition.** A project that migrates from level 4 would lose the plan, preflight and NFR checks.
- **Default to the backend schema, or detect the schema from the file.** The first judges a data or UI project by the wrong schema. The second lets the file being judged choose its rules.
- **A whole-repository run with the known-failures record in the same increment.** It needs a second entry point. It follows with the CI templates (L08).

## Consequences

- **A profile that selects `gherkin-delivery` and uses `--feature` now needs the five artifacts.** A feature that was done under ADR 0028 alone can become continue or escalate.
- **A profile without `project_type` cannot reach done** for a feature, because `feature:eval-criteria` is unknown. The answer names the check and its message names the setting.
- **The report's overall state is a warning at best** when the checks are selected, because the advisory forecast is never a pass. The exit status and the answer are not affected.
- **`govkit validate` is unchanged.** `check_eval_criteria` gains an optional `schema` argument; without it the function behaves as before.
- **Issue #220 is narrowed, not closed.** Feature validation now has a profile route for one selected feature. The whole-repository route and the other items in that issue remain.
- **Data-form criteria are not judged differently.** The data schema is applied as the legacy check applies it.
- The identifiers are a public contract: add, never rename.
