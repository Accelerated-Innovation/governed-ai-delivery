# Feature evidence report

`govkit evidence --feature <name>` answers one question: did this feature's scenarios and criteria pass?

It reads the scenarios in `features/<name>/acceptance.feature` and looks for a test result for each one in the JUnit XML under the target. It reads the criteria in `features/<name>/eval_criteria.yaml` and compares each with a measured score. It exits 0 only when every scenario and every criterion passed. It works in a working tree while you write code, and CI runs the same command.

```bash
pytest --junitxml=junit.xml
govkit evidence --target . --record
govkit evidence --target . --feature 07_invoice_approval
```

The middle step records which commit and working tree the results came from. Without it the results do not count.

```
govkit evidence — feature 07_invoice_approval

  passed   approval-routing-by-amount                (2 tests, bound by id)
  skipped  approval-routing-when-manager-absent      (1 test, bound by tag)
  failed   routing-completes-within-200-ms-at-p95    (1 test, bound by title)  @nfr-performance
  missing  a-rejected-invoice-returns-to-its-author  (no test result found)

  Criteria
  passed   routing-explanation-faithfulness          0.91 ratio, target >= 0.85 ratio  [free]
  failed   routing-p95-latency                       0.24 seconds, target <= 0.2 seconds  [free]
  missing  refusal-safety                            no result, threshold >= 0.99  [free]
  owed     explanation-tone-review                   no result, threshold >= 0.8  [human]

  Working  FAIL  2 failed, 1 skipped, 2 missing, 1 owed of 4 scenarios and 4 criteria: ...
```

The command needs no GovKit installation in the project, no level and no marker. It needs the target to be inside a Git repository. The report reads files and writes nothing; `--record` writes one file. Neither starts a test run or an evaluation.

## What a result means

| State | Meaning |
|---|---|
| `passed` | Every test bound to the scenario passed |
| `failed` | A bound test failed |
| `error` | A bound test errored |
| `skipped` | A bound test was skipped and none failed or errored |
| `missing` | No test result was found for the scenario, or no measured score for a `free` criterion |
| `owed` | No measured score for a `paid` or `human` criterion |

A scenario with several tests, such as a Scenario Outline, takes the worst of them: error, then failed, then skipped, then passed.

The feature's "Working" outcome follows from the scenarios:

| Outcome | When | Exit |
|---|---|---|
| `PASS` | Every scenario and every criterion passed | 0 |
| `ERROR` | A scenario or criterion errored, or a definition or result file could not be used | 1 |
| `FAIL` | A scenario or criterion failed and none errored | 1 |
| `INCONCLUSIVE` | A scenario is skipped or missing, a criterion is missing or owed, the results are not recorded or are stale, or there is nothing to judge | 1 |

A bad invocation exits 2: an unknown feature name, `--json` without `--feature`, `--fast-max-seconds` with `--feature`, or `--record` with `--feature` or `--json`.

## What a pass does not show

- **That the tests ran when the record says.** The record ties result files to a commit and working tree. It can be written again without running the tests again.
- **That a test asserts what its scenario says.** A passing `@nfr-*` scenario shows that its test passed, not that the test checks the value written in the scenario.
- **Where a measured score came from.** GovKit reads the value in the results file. It does not run the evaluation or check how the value was produced.
- **Anything about the forecasts in `plan.md`.** FIRST and virtue scores there are forecasts and are not read.
- **That the definition was not weakened.** A scenario that was deleted is simply no longer listed.

Treat a local `PASS` as a reason to stop and hand over, not as approval. The run that counts for merge is the one CI makes.

## Results must belong to the current commit and working tree

A result file left over from an earlier run, or from before an edit, looks the same as a fresh one. So results count only when a record ties them to the repository as it is now.

### Recording

Run `govkit evidence --record` straight after the tests and evaluations. It writes `govkit-evidence-record.json` in the target, holding:

- the commit;
- a digest of the working tree;
- the time;
- the path and SHA-256 of each result file found.

It exits 1 and writes nothing when there are no result files or the working tree cannot be identified.

### Checking

`govkit evidence --feature <name>` then counts results only when all of these hold:

- a record exists;
- every result file it reads is in the record with the same SHA-256;
- the commit is the one recorded;
- the working tree digest is the one recorded.

| `provenance.state` | Meaning | Outcome |
|---|---|---|
| `current` | Everything is as recorded | As the results say |
| `stale` | The commit, the working tree or a result file changed after the record | `INCONCLUSIVE` |
| `unrecorded` | There is no record | `INCONCLUSIVE` |
| `unavailable` | The record cannot be used, or Git cannot identify the working tree | `INCONCLUSIVE` |
| `not-checked` | No result file was read, so there was nothing to check | As the results say |

When results do not count, each scenario and criterion still shows what the results said, and the detail repeats it after "As found". A stale failure is still worth reading. An `ERROR` stays an `ERROR`.

The fix is always the same: run the tests, then `govkit evidence --record`, then the report.

### What the working tree digest covers

- The commit, the index, and the content of every file Git reports as modified, deleted or untracked.
- Each submodule checked out inside the repository: its own commit and its own changes.
- The whole repository, also when the target is a directory below its root. A change in shared code outside the target makes results stale.
- Not files Git ignores.
- Not the result files or the record. Running the tests rewrites them, and that must not make their own results stale.

Reverting an edit restores the digest, so results recorded before the edit count again.

Add the result files and `govkit-evidence-record.json` to `.gitignore`. They are local artifacts of a run.

### What a record is not

A record is an observation by the same person or agent that ran the tests. It can be written again without running the tests again, and it does not authenticate the result files. Locally, treat a `PASS` as a reason to stop and hand over. The run that counts is CI on a clean checkout, where the tests, the record and the report run in one job.

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

## Criteria and measured scores

Each criterion in `eval_criteria.yaml` is identified as `<feature directory>#evaluation:<name>`. Its revision is the SHA-256 of the criteria file, so editing any criterion changes the revision of all of them.

### The evaluation results file

A measured score reaches GovKit through a file your evaluation run writes. GovKit finds it anywhere under the target by name: `govkit-eval-results*.json`.

```json
{
  "schema_version": 1,
  "kind": "govkit.evaluation-results",
  "tool": "deepeval",
  "results": [
    {
      "requirement_id": "07_invoice_approval#evaluation:routing-explanation-faithfulness",
      "value": 0.91,
      "unit": "ratio",
      "metric": "faithfulness",
      "n": 50
    }
  ]
}
```

| Field | Content |
|---|---|
| `requirement_id` | The criterion's identifier. Required |
| `value` | The measured value. Give this or `error` |
| `error` | A short reason, when the evaluation ran and produced no value. GovKit reports the criterion as error and does not copy the text |
| `metric`, `unit` | What was measured and in what unit. Required when the criterion has a target |
| `n` | Sample size. Optional |

- Schema: `governance/schemas/evaluation-results.schema.json`
- GovKit does not read deepeval, promptfoo or ragas output directly. Write a short step that turns your tool's output into this file.
- A file GovKit cannot use reports `ERROR`. It is never treated as empty, because that would turn a failed evaluation into a missing one.
- When several measurements name one criterion, the worst decides.

### What a score is compared with

| The criterion declares | Compared with |
|---|---|
| A `target` | The target: `>=`, `<=`, `==` or `between`, as the Product Definition Graph compares it. The measurement must state the same metric and unit, or the criterion is error |
| No target, `fail_on: below_threshold` | Passes when the value is at least `threshold` |
| No target, `fail_on: above_threshold` | Passes when the value is at most `threshold` |
| No target, `fail_on: error` or `missing_signal` | Passes when a result exists. The value is not compared, and the report says so |

### Who may run a criterion

A criterion's `execution_class` is `free` (the default), `paid` or `human`.

- An agent may run a `free` criterion. With no result it is `missing`.
- A `paid` criterion costs money and a `human` criterion needs a person. With no result it is `owed`.
- An owed criterion is never done by waiting or by editing the criterion. It needs a person to authorise or perform it.
- Once a result exists, the class no longer matters: the score is compared like any other.
- An unknown class is an error. Reading a mistyped `paid` as `free` would tell an agent to run it.

### NFR values

An NFR written into a scenario, such as "at most 200 ms at p95", has a test, and the report shows whether that test passed. It cannot show that the test checks 200 ms. To have the number compared, declare it as a criterion with a target and write the measured value to the results file. The example does this for `routing-p95-latency`: its scenario's test and its criterion are judged separately.

### Criteria that are not compared yet

The backend `eval_criteria` schema is the only one with named criteria and numeric thresholds, and it is the only form compared.

- **Data projects.** The data schema lists criteria with an `id` and a predicate in words. They are not compared, and a feature with such criteria cannot be `PASS`: the report is `INCONCLUSIVE` and says why.
- **UI projects.** The UI schema has no criteria list. Nothing is added to the report.

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
govkit evidence --target . --feature 07_invoice_approval --json > "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/evidence.json"
```

Write the report outside the repository, as above, or to a path Git ignores. A new untracked file inside the repository changes the working tree, and the next report would call the results stale.

- Schema: `governance/schemas/evidence-report.schema.json`. The record's schema is `governance/schemas/evidence-record.schema.json`.
- Example, with the inputs that produce it: `governance/examples/evidence-report/`. The JUnit XML is stored as `test-run.xml` and the evaluation results as `evaluation-run.json`, so that discovery does not read an example as a real result. The example report is what the command prints when they are copied to `junit.xml` and `govkit-eval-results.json` and recorded; `record.json` is that record, with a placeholder commit and tree digest.

| Field | Content |
|---|---|
| `feature` | The directory name, the feature file's path and SHA-256, and the criteria file's path, SHA-256 and form |
| `outcome`, `detail` | The "Working" outcome and one line explaining it |
| `summary` | The number of scenarios and criteria, and how many are in each state |
| `provenance` | Whether the results belong to the current commit and working tree, with the recorded commit, tree digest and time |
| `sources` | Each result file read, with its SHA-256. A JUnit file also gives the number of skipped tests it counts but does not mark |
| `results` | One entry per scenario (`kind: test`): identifier, revision digest, title, tags, state, how it was bound, and the bound tests. One entry per criterion (`kind: evaluation`): identifier, revision digest, name, tags, state, class, what it was compared with, and the measurements |

The report is the same for the same files and the same record. It holds scenario titles, test names, criterion names and measured values, and no failure text.

A valid report is well-formed. It does not authenticate where its results came from.

## Skipped tests that are not marked

Some reporters count skipped tests on the suite without marking which test cases were skipped. The count is taken suite by suite, and a suite's count covers the suites nested in it. Any test in that file that looks passed could be one of them, so a feature that would otherwise be `PASS` is `INCONCLUSIVE` and the report names the file.

## Without `--feature`

`govkit evidence` without `--feature` is unchanged. It reports each rubric dimension for the whole test run.
