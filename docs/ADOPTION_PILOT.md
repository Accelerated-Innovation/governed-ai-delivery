# Voluntary team pilot for GovKit usefulness and effort

This protocol evaluates whether GovKit helps a team deliver its work. Installing
capabilities, passing controls or producing posture reports is not evidence of
productivity. The pilot is a separate, voluntary activity; the CLI adds no tracking,
collector, ticket integration, time recording or automatic transmission.

## Agree before starting

A team chooses whether to participate, a local coordinator, a short evaluation
period and the work categories it wants to try: defects, small enhancements and
larger features. Include LLM-related work when relevant, independent of workflow
size. Do not require a ticket-completion quota or manufacture work for the pilot.
Record the agreed purpose, who can see the aggregate results, retention/deletion
period and how participants can withdraw. Participation or withdrawal must not be
used in individual evaluation. Keep raw notes within the consenting team.

Choose a comparable baseline: recent similar work or a contemporaneous voluntary
comparison, documenting repository familiarity, approximate scope, tooling,
review requirements and unusual constraints. Do not compare a first-time setup on
an unfamiliar repository with an experienced team's recurring task as if their
durations measured tool impact. Do not claim causal improvement from a convenience
sample or uncontrolled before/after comparison.

## Record separate aggregate observations

Teams may supply coarse effort ranges and qualitative summaries manually. No
individual identifiers, commit/keystroke histories, prompts, tickets, source code,
review text or exact per-person timings belong in a shared result. Avoid tiny
subgroups that could identify participants; agree a minimum reporting group size
with the team before collection, combine groups or suppress results below it.

| Observation | What the team summarizes |
|---|---|
| One-time setup | Discovering the repository, reviewing/accepting policy, installing selected capabilities, configuring checks and CI, resolving initial gaps; distinguish tool work from existing debt |
| Recurring workflow overhead | Per-request planning, required artifacts, local checks/evaluation, evidence handling and maintaining configuration; exclude setup and unrelated waiting |
| Review rework | Coarse ranges of clarification/revision cycles for comparable work, with context; no individual or reviewer rankings |
| Useful findings | Team-confirmed actionable findings, duplicates/noise and missed issues discovered later, with uncertain/unverified cases distinct |
| Repeat-use preference | Voluntary aggregate would-use-again / unsure / would-not-use responses and optional nonidentifying reasons; report nonresponses separately |
| Friction and learning | Manual exceptions, confusing guidance, support effort and adjustments; identify whether observations came from a first or repeated use |

Do not translate posture, passing checks, number of findings, lines changed or tasks
completed into a value score. A useful finding may prevent rework, but the pilot
cannot estimate prevented defects or money saved without separate evidence.

## Analyze and report uncertainty

Analyze setup and recurring effort separately for each represented work category.
Use ranges or distributions appropriate to the small voluntary sample, not a
precise headline average. State how many teams and eligible work observations were
invited, contributed, declined/withdrew and were missing, if the team consents to
those aggregate counts. If an invitation denominator is unknown, say so. Never
impute missing responses as successful adoption.

Record differences in work size, repository familiarity, tool experience,
reviewer availability and policy requirements. Explain selection bias, learning
and novelty effects, small samples, uncertain recall, confounding changes and
unobserved outcomes. Suppress comparisons when work is too dissimilar. Give no
claim of statistical or causal significance without an appropriate study design.

Use this local report template; leave fields unknown until observations exist:

- Consent scope, reporting period, retention/deletion date and audience.
- Comparison method, work categories, cohort denominators and missing responses.
- One-time setup effort and existing-debt effort, separately.
- Recurring overhead, review rework and useful/noisy findings by comparable category.
- Aggregate repeat-use preference including unsure and nonresponse.
- What helped, what caused friction, and the team's proposed changes.
- Uncertainty, confounders, suppressed small groups and limits on conclusions.
- Team decision: continue, revise the workflow, gather more evidence or stop.

Let the team review the aggregate before sharing it. Share only with its agreed
audience through an explicitly chosen channel, honor withdrawals and delete notes
on the agreed schedule. No participants or observations have been recruited or
collected by shipping this protocol; live pilot evidence remains a separate activity.
