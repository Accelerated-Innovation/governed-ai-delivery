# ADR 0022: Feature evidence report and scenario binding

Status: Proposed with the L03 PR for #259. Merging that PR accepts the contract below.

## Context

`govkit evidence` reported rubric dimensions for a whole test run. Nothing connected a scenario in a feature's `acceptance.feature` to a test result, so "this feature is done" could not be computed, and projects wrote their own tests to prove each scenario had a runnable copy. The output was coloured text only.

`plans/LOOP_READY_GATES_PLAN.md` decides that the definition of done is the feature's own scenarios, tests and thresholds (decision 10), that results use the Product Definition Graph's identity (decision 18), and that one JSON report is canonical (decision 16). This increment (L03) is the first to implement them.

The first pilot runs scenarios with pytest-bdd. Its JUnit XML names a test after the scenario title and carries no tags.

## Decision

1. **A feature mode on the existing command.** `govkit evidence --feature <name>` reports one feature. Without the option the command is unchanged.
2. **Scenarios come first.** The report lists every scenario in the feature file and looks for a result for each. A scenario with no result is `missing`.
3. **Identity is mirrored, not designed.** `scenario_identity.py` copies the engine's reader and the skill pack's slug rule. Copied fixtures, produced by running the engine's reader, pin identifiers, digests and refusals. GovKit does not improve either rule.
4. **Binding is by property, then by title.**
   - A `govkit.scenario` JUnit property with the full identifier (`id`) or the `@scenario:` tag (`tag`).
   - Otherwise the scenario title against the test name, both reduced to lower-case letters and digits (`title`).
   - The report records which rule matched. Titles that reduce to the same name within a feature are not matched.
5. **The worst test decides.** Error, then failed, then skipped, then passed.
6. **One outcome, strict exit.** `PASS` only when every scenario passed; otherwise `ERROR`, `FAIL` or `INCONCLUSIVE` in that order. Exit 0 only on `PASS`, 1 otherwise, 2 for a bad invocation.
7. **A versioned JSON report.** Schema `evidence-report` version 1, with a bundled example that is the real output for bundled inputs. The text output renders the same dictionary.
8. **Read-only and independent of installation.** Feature mode reads no marker, needs no level and writes nothing.

## Alternatives considered

- **Property only.** Exact, but no scenario binds until every project adds a hook, including the pilot.
- **Title only.** Needs no project change, but cannot separate similar titles and depends on one runner's naming.
- **A mapping file.** Exact, but a second declaration of the definition, which decision 10 avoids.
- **A Gherkin parsing library.** GovKit uses one for baseline validation, as an optional dependency. It would not reproduce the engine's digest, which is defined over the engine's own line reader, and it would make the report depend on an optional install.
- **A new command.** `evidence` already means "what an executed tool observed", and the plan composes it into `conform` later.

## Consequences

- A feature's state can be computed from the feature's own artifacts, locally and in CI, with one command.
- GovKit holds a second copy of two rules it does not own. `discovery-engine#302` and `aipos-plugins#108` ask their owners to publish them with fixtures. Until then a change in either repository is caught only when the fixtures are refreshed.
- A `Background` edit changes no digest. L06 treats it as a finding.
- A `tag` or `title` binding can pick up a test from another feature. The report states the binding so a reader can judge it; only `id` is exact.
- The report does not say which commit produced the results (L05), does not read criteria (L04), and cannot tell that a scenario was removed (L06). A local `PASS` is a stop condition, not a gate.
- The identifiers, the states, the binding names, the refusal reasons and the exit codes are public. Add, never rename.
