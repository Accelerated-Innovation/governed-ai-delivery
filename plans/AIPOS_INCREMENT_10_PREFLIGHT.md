# Preflight — increment 10 (validate local packages against the baseline)

Written 2026-09-18, revised the same day after the owner supplied the materiality test in §2.
Governed by `governance/schemas/BEHAVIORAL_BASELINE_CONTRACT.md` and ADR-AIG-029.

---

## 1. The gap this increment has to close first

`selected_behavior[].content_digest` is in the schema and **nothing computes it.** Not
`cli/baseline.py`, whose `compute_digest` covers the baseline JSON document. Not
`repo_ingest.py` in govkit-plugins, which has no hashing at all. The fixture values are
hand-authored.

So the validator cannot be written until "did this change" is defined.

---

## 2. The test that defines it

Supplied by the owner, and it replaces the normalization table this document first proposed:

> A Gherkin edit makes it a **different feature** when it changes what a passing
> implementation would do, for whom, or under what conditions — rather than how the same
> behavior is described.
>
> **The practical tell:** if any step definition, test, or previously passing implementation
> could now fail — or a previously failing one could now pass — the contract changed, and the
> contract is the feature.

### Crosses the line

| Edit | Why it is a different feature |
|---|---|
| A `Then` changed | The promised observable outcome — the heart of the contract |
| A scenario added or removed | The acceptance surface grew or shrank. **Removal is the sneaky one:** it narrows what "done" means without anyone deciding that |
| Negative or error-path scenarios weakened or dropped | The happy path is untouched and the risk contract changed. A different feature to operations, support and security even if it demos identically |
| A `Given` changed | Preconditions encode state and data assumptions — an architectural change wearing a wording change's clothes |
| The `When` changed | A different triggering action is a different interaction surface |
| The actor changed | Alters the authorization surface and affected parties; can change the **consequence class**, which cascades into required evidence and review |
| `Scenario Outline` examples added or removed | The example table is the input domain the contract covers; trimming weakens it, adding expands the work, and either way the size/slice scoring is stale |
| Tags changed | `@mvp` → `@v2` changes the release commitment; tags binding scenarios to NFRs or eval criteria change which gates apply. Nothing behavioral moved and the **commitment** did |

### Does not

Rewording with identical semantics · typo fixes · reordering scenarios · extracting shared
`Given`s into a `Background` · renaming steps to match step-definition conventions.

---

## 3. What this test changes about the design

**A digest alone is the wrong instrument, and the first draft of this document got that
wrong.** A digest answers *different or not*. The response here is tiered — cosmetic needs
nothing, clarifying needs a readiness re-run, semantic goes back through refinement with the
PM/QA/engineering trio and reissues the Development Token — and a digest cannot tell those
apart. It would report every edit identically and hand the classification back to a human,
which is the work the `govkit-feature-refine → readiness` chain already does.

Three consequences:

**1. Compare the resolved closure, not the literal text.** Extracting shared `Given`s into a
`Background` must be invisible, and it only is if the comparison is over each scenario's
*effective* steps after `Background` inheritance. Comparing raw text would flag the one
refactor the test explicitly calls editorial.

**2. Classify by clause role, not by equality.** The report says *a `Then` changed in
`support-app/response-approval#scenario:x`*, because that is what decides the tier. "The
digest differs" does not.

**3. Sets where order is not meaning.** Tags and `Examples` rows compare as sets: a reorder
changes neither the gates that apply nor the input domain covered. **This reverses the first
draft's recommendation** to treat `Examples` row order as significant — under the test it
plainly is not, since no implementation passes or fails differently for it.

### The limit, stated plainly

**The validator cannot distinguish a reworded `Then` from a changed one.** "the user sees an
error" → "the user is shown an error" is editorial; → "the user sees a warning" is semantic.
No parser separates those, and pretending otherwise would be the more dangerous failure.

So the validator reports **facts and the maximum tier they imply**, erring strict: *a `Then`
changed* routes to semantic, and a human downgrades it to clarifying after reading the diff.
It never upgrades silently, and it never decides the tier itself.

---

## 4. What the digest is still for

Not classification — **tamper evidence**. A recorded `content_digest` is what makes "the
manifest was edited to hide an altered scenario" detectable, because the baseline's own claim
about what it covers can then be checked rather than trusted.

Normalization before hashing, on the same principle as the test: normalize what a tool or a
checkout can change without a person deciding anything.

| Input | Treatment |
|---|---|
| Unicode form | NFC — a macOS checkout hands over NFD where Linux hands over NFC |
| Line endings, trailing whitespace, blank lines, Gherkin indentation | normalized away |
| Indentation **inside a docstring** | **preserved** — a docstring is payload, and a YAML or JSON body means something different reindented |
| Comments (`#`) | excluded — no comment change can make a passing implementation fail, which is the test |
| Tag order, `Examples` row order | sorted — sets, per §3 |
| Step text internal whitespace | collapsed |

### Keyword case is not a normalization question

The first draft carried a row for it, reasoning "a parser may care, so be conservative". That
was a rule of thumb standing in for a check. The check:

```
Given a thing   ->  parsed, steps = [('Given ', 'a thing')]
given a thing   ->  parsed, steps = []
```

`gherkin-official` does not reject a lowercase keyword — it **silently yields a scenario with
no steps**. Under the owner's test that is emphatically a different feature: every step
definition that passed now has nothing to run. But it is not a digest question, and it
belongs in §5.

---

## 5. Refusals

Path traversal · ambiguous references (one slug matching two elements) · missing required
artifacts · unsupported `version` · **a manifest edited to hide an altered scenario**, which
means the validator must re-derive the closure from the working tree rather than trust the
baseline's record of it.

**A selected element that parses to nothing.** A scenario with zero steps, a `Rule` with no
body, an `Examples` block with no rows. Not a digest change and it must not be reported as
one: **the digest of an empty thing is perfectly stable**, so a scenario that has silently
lost its steps would re-approve cleanly the moment someone accepted the diff.

---

## 6. What the report has to say

Consistency, not authority — and the difference is load-bearing. This increment answers *the
working tree still says what the baseline recorded*. Whether that baseline **currently carries
authority** is increment 11's question, answered by the engine. Conflating them would let a
locally consistent tree read as authorized, which is the same error as inferring a commitment
from a card state.

For a semantic change the report names what the owner's model says is now void:

- the **readiness verdict and Development Token** were issued for a spec that no longer
  exists (`.govkit/tokens/<feature-key>.json`);
- the **size/slice assessment** is stale;
- the **evidence lineage** is broken — validation proved demand for the old behavior and
  nobody has confirmed it covers the new;
- per Canon's material-change doctrine (D6), the agents' authorization attached to *that*
  configuration of intent, so continuation requires re-approval rather than silence.

An actor, consequence or scope change also flags the upstream question: does the validation
evidence still hold.

**Read-only, and unable to be otherwise.** No rewriting specs to pass, no adding missing IDs
during enforcement, no silent manifest upgrade. A validator that can edit what it validates is
a formatter.

---

## 7. Still open

**Comments excluded** (§4) is the remaining judgement call. It follows from the test — a
comment cannot make an implementation fail — but it means an author can rewrite the prose
explaining a `Rule` without the approval noticing. Confirmed unless the owner says otherwise.
