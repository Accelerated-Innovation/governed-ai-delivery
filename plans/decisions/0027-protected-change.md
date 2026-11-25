# ADR 0027: A change cannot weaken the tests and files that check it

Status: Proposed with the PR for #269. Merging that PR accepts the contract below.

## Context

ADR 0026 keeps a change from weakening a feature's scenarios and criteria. The change can still weaken what checks them: edit an existing test so it passes, change a fixture or a test setting, edit the CI workflow, or mark a test as skipped.

GovKit cannot guess which paths these are, and it works for any language, so it cannot parse test functions to find the ones bound to a scenario.

The maintainer decided on 2026-11-25: the declaration lives in accepted policy, and existing test files are additions-only.

## Decision

1. **The declaration is in accepted policy.** The conformance configuration (`change-policy`) gains an optional `protected` section with `tests`, `files` and `escape_markers`. It is read from the trusted policy checkout, which the change being judged cannot edit. Paths are literal and repository-relative, like every other scope in that file.
2. **A check on the captured change.** `change:protected` reads the snapshot change conformance already holds and runs nothing. `protected_change.py` is pure.
3. **`tests` are additions-only.** A new file passes. An existing file passes when every line it had at the comparison base is still there in the same order. A changed or removed line, or a deleted file, is a finding. Line endings are normalised; a file that is not UTF-8 text must be identical. A changed file mode is a finding under either rule.
4. **`files` may not change.** A new file passes. Any change to an existing file, or deleting it, is a finding. This is the rule for fixtures, helpers, settings, CI workflows and the known-failures record. A path under both follows this rule.
5. **Escape markers may not rise.** Each declared marker is literal text. Its total count in the files under `tests` and in feature definition files may fall and may not rise. A rise gives one finding per file that gained it.
6. **A finding fails the check and means a person must look.** Each has a stable code and names the file. Messages hold no file content.
7. **The check is present only when the section is declared.** A configuration without it reports what it always did. Nothing is protected by default.

## Alternatives considered

- **A declaration in the project, read at the comparison base.** It needs no policy checkout, but needs rules for a change that edits the declaration. It belongs with the level-free entry point (L07).
- **Any change to an existing test file is a finding.** Every new test would need a new file.
- **Protect only tests bound to a scenario.** It needs a parser per language to find a test's lines.
- **Protect CI workflows and the known-failures record by default.** Every existing report would gain a check, and a default path would be wrong for some projects.
- **Additions at the end of the file only.** It would close the inserted-line gap below, but a Java or C# test class cannot gain a method after its closing brace.

## Consequences

- **A line inserted inside an existing test is not seen.** An early return keeps every base line. Declared escape markers catch the common skip forms; the rest is for the reviewer and for L07's rule that nothing that was passing now fails.
- **Imports are not traced.** A helper outside the declared paths is not protected.
- A legitimate refactoring of an existing test fails until a person accepts it. That is the intended cost.
- A marker's count is by literal text, so a comment that mentions the marker counts.
- The codes are a public contract: add, never rename.
