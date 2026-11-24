# Feature evidence report

`govkit evidence --feature <name>` answers one question: did this feature's scenarios pass?

It reads the scenarios in `features/<name>/acceptance.feature`, looks for a test result for each one in the JUnit XML under the target, and exits 0 only when every scenario passed. It works in a working tree while you write code, and CI runs the same command.

```bash
pytest --junitxml=junit.xml
govkit evidence --target . --feature 07_invoice_approval
```

```
govkit evidence — feature 07_invoice_approval

  passed   approval-routing-by-amount                (2 tests, bound by id)
  skipped  approval-routing-when-manager-absent      (1 test, bound by tag)
  failed   routing-completes-within-200-ms-at-p95    (1 test, bound by title)  @nfr-performance
  missing  a-rejected-invoice-returns-to-its-author  (no test result found)

  Working  FAIL  1 failed, 1 skipped, 1 missing of 4 scenarios: ...
```

The command needs no GovKit installation in the project, no level and no marker. It reads files and writes nothing.

## What a result means

| State | Meaning |
|---|---|
| `passed` | Every test bound to the scenario passed |
| `failed` | A bound test failed |
| `error` | A bound test errored |
| `skipped` | A bound test was skipped and none failed or errored |
| `missing` | No test result was found for the scenario |

A scenario with several tests, such as a Scenario Outline, takes the worst of them: error, then failed, then skipped, then passed.

The feature's "Working" outcome follows from the scenarios:

| Outcome | When | Exit |
|---|---|---|
| `PASS` | Every scenario passed | 0 |
| `ERROR` | A scenario errored, or the feature file or a result file could not be read | 1 |
| `FAIL` | A scenario failed and none errored | 1 |
| `INCONCLUSIVE` | A scenario is skipped or missing, or there is nothing to judge | 1 |

A bad invocation exits 2: an unknown feature name, `--json` without `--feature`, or `--fast-max-seconds` with `--feature`.

## What a pass does not show

- **Which commit the results came from.** The report reads the result files it finds. A stale file from an earlier run looks the same as a fresh one.
- **That a test asserts what its scenario says.** A passing `@nfr-*` scenario shows that its test passed, not that the test checks the value written in the scenario.
- **Anything about `eval_criteria.yaml`.** Criteria and measured scores are not read yet.
- **That the definition was not weakened.** A scenario that was deleted is simply no longer listed.

Treat a local `PASS` as a reason to stop and hand over, not as approval. The run that counts for merge is the one CI makes.

## How a scenario is matched to a test

In this order:

1. **By property.** A test case carries a JUnit property named `govkit.scenario`. Its value is either the scenario's full identifier (`07_invoice_approval#scenario:approval-routing-by-amount`, reported as `id`) or its tag (`@scenario:approval-routing-by-amount`, reported as `tag`).
2. **By title.** Otherwise, a test case whose name equals the scenario title once both are reduced to lower-case letters and digits. A leading `test_`, a trailing `[...]` parameter and a leading run of digits are ignored. This is the name pytest-bdd gives a scenario.

Rules that keep a match honest:

- Every test that names a scenario by property counts, whether it uses the identifier or the tag.
- A test that carries a `govkit.scenario` property is never matched by title.
- When two scenarios in the feature reduce to the same test name, neither is matched by title. The report says so.
- Only the full identifier is exact across features. A tag is unique within one feature file, and a title can repeat anywhere, so a test in another feature with the same tag or title is bound as well. Use the full identifier when that can happen.

### Writing the property with pytest-bdd

```python
# conftest.py
def pytest_bdd_before_scenario(request, feature, scenario):
    for tag in scenario.tags:
        if tag.startswith("scenario:"):
            request.node.user_properties.append(("govkit.scenario", "@" + tag))
```

Any runner that writes `<property name="govkit.scenario" value="..."/>` inside a `<testcase>` works the same way.

## Scenario identity

A scenario is identified as the Product Definition Graph identifies it, so a report can later be sent there unchanged.

- **Identifier.** `<feature directory>#scenario:<slug>`. The slug is the scenario's `@scenario:<slug>` tag, or is derived from its title when it has none. A derived slug changes when the title is reworded, and the report marks it `derived`.
- **Revision digest.** SHA-256 of the scenario's tag lines, keyword line, steps and `Examples`, with comments removed and trailing whitespace stripped. Editing a scenario changes its digest.
- **Not in the digest.** A `Background` is in no scenario's digest. Editing one changes what every scenario tests and leaves every digest the same.

GovKit reports `ERROR` for a feature file the graph would refuse, with the graph's reason:

| Reason | Cause |
|---|---|
| `parse_error` | Not UTF-8, not English, an unclosed doc string, or not exactly one `Feature:` at the top |
| `invalid_identifier` | Two `@scenario:` tags on one scenario, or a slug that is not lower-case kebab-case |
| `slug_collision` | Two scenarios, or two rules, with the same slug |
| `title_too_long` | A feature or scenario title over 200 characters |

The slug rule belongs to `aipos-plugins` and the reader and digest to `discovery-engine`. GovKit copies both and pins them with fixtures in `tests/fixtures/scenario-identity/`.

## JSON report

`--json` prints the same report as JSON and nothing else. The exit status is unchanged.

```bash
govkit evidence --target . --feature 07_invoice_approval --json > evidence.json
```

- Schema: `governance/schemas/evidence-report.schema.json`
- Example, with the feature file and JUnit XML that produce it: `governance/examples/evidence-report/`. The JUnit XML is stored as `test-run.xml` so that evidence discovery does not read an example as a real result; the example report is what the command prints when it is copied to `junit.xml`.

| Field | Content |
|---|---|
| `feature` | The directory name, the feature file's path and its SHA-256 |
| `outcome`, `detail` | The "Working" outcome and one line explaining it |
| `summary` | Counts of scenarios in each state |
| `sources` | Each result file read, with its SHA-256 and the number of skipped tests it counts but does not mark |
| `results` | One entry per scenario: identifier, revision digest, title, tags, state, how it was bound, and the bound tests |

The report is the same for the same files. It holds scenario titles and test names, and no failure text.

A valid report is well-formed. It does not authenticate where its results came from.

## Skipped tests that are not marked

Some reporters count skipped tests on the suite without marking which test cases were skipped. The count is taken suite by suite. Any test in that file that looks passed could be one of them, so a feature that would otherwise be `PASS` is `INCONCLUSIVE` and the report names the file.

## Without `--feature`

`govkit evidence` without `--feature` is unchanged. It reports each rubric dimension for the whole test run.
