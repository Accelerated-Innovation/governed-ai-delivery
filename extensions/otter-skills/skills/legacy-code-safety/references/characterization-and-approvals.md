# Characterization and Approval Testing

Read this reference when existing behavior is poorly understood or the useful observable result is too large for a few focused assertions.

## Characterization loop

1. Choose one input relevant to the requested change.
2. Invoke the current production path through the narrowest safe boundary.
3. Begin with an expectation known to be wrong, or with unapproved output.
4. Run the code and observe the actual result.
5. Inspect whether the observation is meaningful, stable, and safe to retain.
6. Record the observation and name the behavior it demonstrates.
7. Repeat only for relevant partitions, boundaries, and failure paths.

Expected values come from execution. Documentation, tickets, comments, and the agent's interpretation may explain an observation, but they do not replace it.

If behavior appears defective, record:

```text
Observed behavior:
Reason it may be defective:
Known consumers or compatibility risk:
Decision needed:
```

Do not silently repair it during baseline characterization.

## When approval testing fits

Prefer an approval artifact when the result is structured and broad enough that individual assertions would hide the whole:

- reports and rendered documents
- serializers, parsers, and transformations
- command-line output
- combinations of many business-rule cases
- a stable event or call trace at a subsystem boundary

Use focused assertions when the important result is small. Approval testing is not a reason to snapshot an entire application or object graph.

## Approval loop

1. Arrange representative input.
2. Act through a safe boundary.
3. Render only relevant results in a stable, human-readable form.
4. Diff received output against the approved artifact.
5. Inspect every meaningful difference.
6. Approve intentionally and keep the artifact with the test.

Before approval, control or remove timestamps, random identifiers, unstable ordering, machine paths, concurrency noise, secrets, personal data, and irrelevant bulk.

Never update approved output merely to make a failing suite green. A changed artifact is evidence requiring a decision.

## Demonstrate sensitivity

Execution and coverage are not enough. Confirm that the test detects a relevant behavioral change by one of these means:

- observe the initial incorrect expectation fail
- temporarily perturb a protected value or branch, run the test, and revert
- run a focused mutation tool and inspect surviving mutations

Use coverage to find relevant branches not exercised, not as a quality target.

## Retirement

Keep broad characterization while it provides unique protection. As understanding improves, replace noisy approval output with focused behavioral tests where that makes failures faster and clearer. Retire an artifact only when equivalent protection is demonstrated.
