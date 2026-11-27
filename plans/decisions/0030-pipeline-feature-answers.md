# ADR 0030: The generated pipeline judges every feature a change touches

Status: Proposed with the PR for #277. Merging that PR accepts the contract below.

## Context

`govkit conform --feature NAME` answers done, continue or escalate for one feature (ADRs 0028 and 0029). CI does not know the feature's name, and a pull request can touch several. The generated pipeline (ADR 0012) already runs the conformance engine with a request, a base and a trusted policy checkout, prints the change-results record and exits 0 or 1. Provider evidence and posture read that record.

The maintainer decided on 2026-11-26:

- One engine run, with one answer for each touched feature.
- The engine selects the features from the change. A caller cannot narrow the list.
- A pipeline setting turns this on. It is off by default.
- The change-results record and the exit status stay as they are. The answers go to an optional new file.

## Decision

1. **A pipeline setting.** `"features": "changed"` in the pipeline settings is carried into the generated binding. Without it, the rendered file, its inputs and the runtime are unchanged, and saved renders replay.
2. **Selection.** With the setting, the engine judges each `features/<name>/` directory that has a changed path in the change it already captured. Starter features and removed directories are left out, as in `govkit evidence --changed-since`.
3. **Checks carry the feature's name.** Each judged feature gets `evidence:feature[<name>]` and, when the profile selects them, `feature:<identifier>[<name>]`. They are required, except the forecast. The checks on the change and the project's commands run once.
4. **One answer for each feature.** A feature's answer reads its own named checks and every check that is not named for a feature. Another feature's checks do not reach it.
5. **The record and exit status are unchanged in form.** Standard output is the change-results record, now with the named checks in it. The exit status is 0 or 1. A feature that is not done fails the run through its required checks.
6. **The answers file.** A new optional input, `feature_output`, names a new file outside both checkouts. It holds one `govkit.feature-verdicts` document: the change results once, and each feature's state, reasons and evidence report. `parse_feature_verdicts` recomputes every answer and checks that the answers cover exactly the features the record judged. One line for each feature goes to standard error.
7. **A single named feature is unchanged.** `govkit conform --feature NAME` keeps its check names and its `govkit.feature-verdict` document. The two modes do not combine.

## Alternatives considered

- **One engine run for each feature.** The project's tests and every change check would run again for each, with several records to reconcile.
- **A caller input that lists the features.** A caller could leave a touched feature out.
- **On whenever the profile selects `gherkin-delivery`.** Regenerating an existing pipeline would change what it requires.
- **Printing the answers in place of the record, with exit status 0, 1 or 3.** Provider evidence and posture would need the record extracted from inside another document.

## Consequences

- **A change that touches no feature adds no check.** The answers list is empty and the record is byte-identical to a run without the setting.
- **A failure of the change itself reaches every answer.** A failing project command makes each touched feature continue.
- **There is no overall state across features.** Each answer stands alone; the run's exit status is the record's.
- **A feature the change does not touch is not judged.** A regression in it is not seen here.
- **Check names with a feature in brackets are reserved** in a run that judges features.
- **The pipeline does not record feature evidence.** It can execute the checks its settings enable, such as `project:tests`, but a feature is judged by result files recorded before the entry point starts. The caller runs the tests and `govkit evidence --record` first, as for a local run.
- The setting's value, the check name form and the document kind are a public contract: add, never rename.
