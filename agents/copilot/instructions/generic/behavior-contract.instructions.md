---
applyTo: "*"
---

# Behavior Contract

These instructions apply to all files in the project, **conditionally**.

> **This applies only if `.govkit/skill_context.yaml` records
> `authority.source: pdg`.** If it records `none` — the default, and where
> most projects using GovKit are — **this rule does not apply**, nothing
> below changes how you work, and you should not mention it.

---

## What a behavior contract changes

Under a contract, the feature's behavior is a **versioned commitment**, not a
description of it. A *baseline* binds the exact Rules and scenarios to an
immutable source revision by digest, and somebody with product authority
approved **that** revision — not the working tree you are looking at, and not
your reading of it.

Two things follow, and they are the whole rule:

1. The scenarios are the specification. Not a starting point, not an
   illustration of intent you are expected to complete.
2. You cannot change what is committed, and you cannot approve a change to
   it. You can only implement it, or stop and say why you cannot.

## Before planning or implementing

**1. Load the approved baseline** named in the feature's commitment package,
and plan from it rather than from the feature folder alone. Both commands
below need its path; neither has a default.

**2. Check the working tree against it.** Local, no network:

```
govkit validate-baseline --target . --baseline <path to the approved baseline>
```

**If the baseline lists more than one entry under `sources`, that form
refuses.** A cross-repository baseline needs a checkout for each one, named
by its `source_key`, and the flag repeats:

```
govkit validate-baseline --target . --baseline <path> \
  --source <source_key>=<path to that checkout> \
  --source <source_key>=<path to that checkout>
```

`--target` stands in for a single source and only for a single source. Read
`sources` in the baseline before assuming the short form applies — the
refusals you get otherwise are about missing checkouts, not about drift.

If it reports drift, **stop**: the spec in front of you is not the spec that
was approved, and everything you would plan from it inherits that.

**3. Check that the approval is still current:**

```
govkit verify-authority --target . --baseline <same path> --commitment <id>
```

Run it again after any change to the feature's Gherkin — an approval can be
withdrawn while work is in progress, and the answer you got on Monday is not
the answer today.

Three things about that command, each of which will otherwise mislead you:

- **`<id>` is the commitment id from the commitment package**, and it is not
  optional in practice. Leave it out and the answer is **not authorized** —
  which is true of the pointer you did not supply, and says nothing about
  your work. Do not read your own omission as a rejection.
- **The endpoint comes from `GOVKIT_PDG_URL` in the environment**, never from
  the repository, and the credential from `GOVKIT_PDG_TOKEN`. If the variable
  is unset the command says so and exits zero without a verdict: that is an
  unconfigured check, not an approval.
- **Report an unreachable graph as *unverified*.** It is not a rejection and
  it is not permission.

CI runs the enforcing form of that same check at merge, with a credential you
do not have and should not be given. Your copy is there to tell you early, not
to be the gate.

## Implement the selected behavior, and only it

Four ways an agent changes the product while believing it is implementing the
spec. Each is a **contract change**, not a detail:

- **No inferred exclusions.** If a scenario covers a case that looks
  redundant, unreachable, or obviously not intended, implement it anyway and
  raise the question separately. An exclusion you inferred is a scope
  decision you made.
- **No added helpful behavior.** Validation nobody asked for, a fallback, an
  extra field, a retry, a friendlier default. If it changes what a caller
  observes and no scenario asked for it, it is new product behavior.
- **No relaxed thresholds.** An evaluation threshold that a run cannot meet
  is a result, not an obstacle. Report the number. Never edit the threshold,
  the rubric, or the sample so a run passes.
- **No widened tool authority.** Do not grant yourself credentials, scopes,
  network access, or permissions the task did not already carry, and do not
  weaken a check that would have stopped you.

Preserve what the feature already requires: its NFRs, its `design.md` where
the project type has one, and its model-quality evaluations. A contract on
behavior does not suspend any of them.

## What remains yours

The contract governs **behavior**, not code. Within it you retain full
discretion, and you are expected to use it:

- **Refactor freely.** Restructure, rename, extract, and re-layer as the
  architecture contracts require, as long as every scenario still passes
  unchanged. A behavior contract is not a code freeze, and treating it as one
  is a misreading.
- **Evolve the plan.** `plan.md` is yours; increments, ordering, and internal
  design can change as you learn, so long as the committed behavior does not.
- **Fix defects in the fix lane.** Restoring behavior an existing contract
  already established is not a change to it.

## You cannot approve, and the two permissions are different

**Your execution permissions** answer *may this agent run this command, edit
this file, open this pull request*. **Product approval** answers *may this
behavior ship*. They are held by different parties for different reasons, and
holding the first **never** confers the second.

So: **no agent issues a product approval, revokes one, or records one** — not
for its own work, not on someone's spoken say-so in the conversation, and not
because the change looks obviously correct. A statement in chat that something
is approved is not an approval; the graph is the only record of one.

## When the contract and the work conflict

You will find cases the committed scenarios get wrong, or do not cover, or
answer in a way the architecture cannot support. That is normal and expected.

**Stop and route it to a decision.** Say precisely which scenario is in
conflict, what the code would have to do differently, and what you believe the
right answer is — then wait. Do not implement your recommendation while the
decision is outstanding, and do not implement the scenario in a way you
believe is wrong without saying so.

Deciding it yourself is the single thing the commitment exists to prevent.
