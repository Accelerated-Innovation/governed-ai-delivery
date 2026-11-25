# ADR 0025: A project states where its test results are

Status: Proposed with the PR for #265. Merging that PR accepts the contract below.

## Context

`govkit evidence` found test results by file name only: `junit*.xml`, `*junit*.xml` and `test-results*.xml`. GovKit is meant to work for any language, and runners do not agree on a name. Maven Surefire and Gradle write `TEST-*.xml`, so a Java feature's results read as missing. The name rule also reads any file that happens to match, such as a fixture inside a dependency folder.

The format is not the obstacle for most runners: JUnit XML is the common output. The location is.

Reading the freshness check for this change also showed a gap in ADR 0024. A result file that was recorded and then deleted left the remaining results `current`, so deleting the one file that held a failure could change the report.

## Decision

1. **The location is stated when recording.** `govkit evidence --record --junit PATTERN` takes one or more patterns, relative to the target. `--junit` without `--record` is a bad invocation.
2. **Stated patterns replace the name rule** for test results. Evaluation results keep their GovKit name. Without `--junit` nothing changes, and the record is byte-identical to before.
3. **The record keeps the patterns**, as the optional `junit_patterns`, and the feature report reads them from there. The location is stated once, and the record and the report cannot search different places. The schema stays at version 1; an older GovKit refuses a record that has the field, which reads as `unavailable`.
4. **A pattern cannot leave the target.** It is relative, uses forward slashes, has no `..` and uses `**` only as a whole folder name. A match reached through a link out of the target is refused. The same rules apply when a record is read, so an edited record cannot widen them.
5. **A pattern matches JUnit XML only.** Every file matched by a stated pattern must be XML whose root is `testsuite` or `testsuites`, or nothing is recorded. Recorded result files are left out of the working tree digest (ADR 0024, decision 5), so a pattern that matched a source file would hide that file's edits from the freshness check.
6. **A pattern that matches nothing is an error**, not an empty result. It is most likely a mistyped path.
7. **A recorded result file that is gone makes the results stale.** This holds with or without `--junit`.

## Alternatives considered

- **`--junit` on the report as well.** Two places to state the same thing, which an agent could give differently. The report would also have to decide what an unrecorded location means.
- **A configuration file.** The level-free path has no project file of GovKit's to put it in, and a new one is more than this needs.
- **More default names.** `**/TEST-*.xml` would cover Java, but each addition reads more files that are not results, and the next runner needs another.
- **Adding to the name rule instead of replacing it.** A project could then not stop a stray matching file from being read.

## Consequences

- A Java, Kotlin, JavaScript or Go project whose runner writes JUnit XML can be recorded and reported, wherever the files are written.
- This settles the location only. Whether a runner's test names match scenario titles is separate, and is checked per runner with the CI templates (L08). A `govkit.scenario` property binds on any runner that can write one.
- Formats other than JUnit XML, such as .NET TRX, are still not read. A .NET project needs a JUnit logger.
- `govkit evidence` without `--feature` keeps the name rule.
- The JUnit check reads each stated file once more when recording.
