# Behavioral baseline — contract specification

Contract version **1**. Schema: [`behavioral_baseline.schema.json`](behavioral_baseline.schema.json).
Conformance fixtures: [`../fixtures/behavioral-baseline/`](../fixtures/behavioral-baseline/).

A baseline records **exactly which behavior a product commitment approved**, bound to immutable
source revisions. It is the artifact a validator diffs a working tree against, and the artifact
whose digest an authoritative decision binds.

This document is normative for anyone implementing a producer or consumer — including one in
another language. The schema constrains shape; this specifies the parts a schema cannot: the
digest, what the digest covers, and how a selection resolves.

---

## 1. What a baseline is not

**It is not an approval.** No property means "approved", `additionalProperties` is `false`
throughout, and a document carrying `approved: true` fails validation. A baseline that validates
is a well-formed *proposal of scope*. Whether it currently authorizes work is a different
question, answered by the decision service, freshly, at the boundary that needs the answer — never
by a field, a file, a cached result, or a green badge.

**It is not a copy of the business case.** The problem, evidence and rationale live in the Product
Definition Graph and are referenced by opaque id. Copying them here would create a second editable
copy of something that already has an owner.

**It is not a second copy of the specification.** Rules and scenarios live in versioned
`acceptance.feature` artifacts. A baseline references them and records a digest of what it
referenced; it never restates them.

---

## 2. Versioning

`version` is an integer. This contract is version **1**.

A consumer holds an explicit list of supported versions and rejects anything outside it with a
**named error** — "this baseline is version N, this tool understands 1" — not a pile of schema
violations. A baseline from the future is newer, not malformed, and saying so is the difference
between a useful message and a wall of noise. The version check short-circuits: a consumer must
not report field-level errors against a shape it does not understand, because those messages would
be confidently wrong about fields that may mean something else in that version.

Adding an optional property is a compatible change within version 1. Changing canonicalization,
changing what the digest covers, or making an optional property required is **not** — each would
invalidate every digest already recorded against a decision, so each takes a new contract version.

---

## 3. Canonical form and digest

### 3.1 The rule

```
digest = "sha256:" + hex( SHA-256( canonical_bytes(baseline) ) )
```

`canonical_bytes` is produced by, in order:

1. **Drop the non-normative keys.** Exactly one today: `advisory`.
2. **Fold whole numbers written as floats to integers.** `1` and `1.0` are the same number and
   both satisfy `"type": "integer"`, but they serialize as `1` and `1.0`. Booleans are excluded
   explicitly, because `bool` subclasses `int` in Python and `true` must never become `1`.
3. **Normalize every string to Unicode NFC.** A macOS checkout can hand over NFD where Linux hands
   over NFC for the same characters; without this the same baseline digests differently on two
   machines, which is precisely the cross-consumer disagreement a digest exists to rule out.
4. **Sort every array** by each element's own canonical JSON serialization. Every array in a
   baseline is a *set* — the order someone listed two scenarios in is not part of what was
   approved.
5. **Serialize** as JSON with keys sorted by Unicode code point, separators `,` and `:` with no
   whitespace, and non-ASCII emitted literally (not `\u`-escaped).
6. **Encode** UTF-8.

Reference implementation: `cli/baseline.py` (`canonical_form`, `canonical_bytes`,
`compute_digest`). `canonical_bytes` is exposed deliberately — a digest mismatch tells you two
implementations disagree, but not where, and the bytes do.

### 3.2 What changes the digest, and what does not

| Change | Digest |
|---|---|
| Re-indenting, reordering keys, reordering arrays, line endings, trailing whitespace | **unchanged** — formatting is not behavior |
| NFC/NFD composition of the same characters | **unchanged** |
| A whole number written `1` versus `1.0` | **unchanged** |
| Adding or revising anything under `advisory` | **unchanged** — advisory material is non-normative by definition |
| A selected scenario's content digest (its steps, Examples rows, Background, Rule text, inherited tags) | **changed** |
| A source revision | **changed** |
| A scenario added to or dropped from `selected_behavior` | **changed** |
| A constraint, exclusion, evidence reference, or declared discretion | **changed** |

The last row is deliberate and worth stating plainly: **the digest covers the whole document
except `advisory`.** One rule, no per-field exceptions to remember. Evidence is included because
approval is evidence-linked — if the evidence changes, the decision deserves another look.

### 3.3 What the digest does *not* prove

Digest equality proves the **approved specification** is unchanged. It proves nothing about the
code. Implementation can drift from an unchanged spec, and untraceable behavior can be added
under a digest that still matches. Traceability, scenario-based verification and review remain
necessary; a matching digest is never offered as evidence of conformance.

---

## 3A. Sources: what counts as immutable

Every source declares a `kind`, and the kind decides which revision forms are acceptable. The
distinction is not cosmetic:

| `kind` | `revision` must be | Why |
|---|---|---|
| `repository` | a 40- or 64-character hex commit SHA | A git tag such as `v1.2.3` **can be moved**. Accepting one would let approved content change without the baseline or its digest changing — precisely what the binding exists to prevent. |
| `package` | a released version (`1.2.3`, `v1.2.3-rc.1`) | Immutable by the registry's own contract. |

`main`, a branch name, or a tag on a repository source is rejected.

`sources[].path` is an optional repository-relative prefix. Every segment must begin with an
alphanumeric or underscore, which rejects absolute paths, `.` and `..` segments, Windows
backslash separators and drive letters. Resolution outside the bound revision would read content
the digest was never taken against, leaving the "immutable" binding immutable in name only. This
is enforced twice — by pattern in the schema, and by a cross-field check whose message says why.

`source_key` must be unique. Two declarations of one key make every reference through it
ambiguous: a consumer cannot tell which revision the approved content came from.

---

## 4. Qualified references

```
<source-key>/<feature-key>#<kind>:<slug>
```

`kind` ∈ `rule` · `scenario` · `nfr` · `evaluation` · `design` · `agent-authority`.
Slugs are lowercase kebab-case, matching the `@rule:` / `@scenario:` tag convention in
govkit-plugins' `spec-identifiers.md`. Existing Gherkin tags are unchanged by this contract — the
qualification is the `<source-key>/<feature-key>` prefix and nothing else.

The `source-key` segment is what makes two features carrying the same local slug in different
repositories resolve distinctly. Every reference's source-key must name an entry in `sources`, or
the reference is unresolvable and the baseline is rejected.

### 4.1 Authored versus derived identity

| `id_source` | Meaning | In a new baseline |
|---|---|---|
| `tag` | An author wrote `@rule:<slug>` / `@scenario:<slug>` in the Gherkin | **Required** |
| `derived` | A tool slugified the element's name; `repo_ingest.py` records this | **Rejected** |

A derived identifier is stable only as long as the name is, so binding an approval to one binds it
to a rename. Legacy packages keep ingesting and stay readable with derived ids clearly marked;
they simply cannot be approved until migrated, and the migration is one tag line per element.

---

## 5. Resolving a selection from a file containing future scenarios

A feature file routinely holds more than the current commitment: next release's scenarios, options
under discussion, behavior deliberately deferred.

**Only what `selected_behavior` lists is in scope.** Sharing a file with a selected scenario
confers nothing. This is what stops an unselected future option from riding along into an approval
because it happens to sit under the same `Rule:`.

Two obligations follow, and both are consumer requirements, not suggestions:

1. **The closure, not the body.** A selected scenario's `content_digest` covers its full
   dependency closure — its steps, every `Examples` row, its tables and docstrings, every
   `Background` that reaches it, its `Rule`'s text and description, and its inherited tags.
   Digesting only the scenario body would let a changed `Background` alter approved behavior
   silently, which is the single most likely way an approval is invalidated without anyone
   noticing.

2. **Rule obligations survive scenario selection.** Selecting a scenario under a `Rule` brings the
   Rule's obligation into scope. Leaving out a scenario that demonstrates a required control does
   not remove the control — it removes the demonstration, and a scope-completeness check should
   say so.

Edits to *unselected* scenarios in the same file do not change the baseline digest, and a consumer
should report them separately rather than as drift — provided they provably do not touch the
closure of anything selected.

---

## 6. Artifact roles

| Field | Role | Digest |
|---|---|---|
| `selected_behavior` | Normative. The authoritative scope. Carries **`rule` and `scenario` only** — scope is behavior. | in |
| `constraints` | Normative. Carries **`nfr`, `evaluation`, `design`, `agent-authority` only**. Relaxing one is a scope change. | in |
| `exclusions` | Normative. A positive statement that something was considered and not committed. | in |
| `evidence` | Normative reference. Bodies live where they were recorded; `contradicting` evidence is recorded, not hidden. | in |
| `implementation_discretion` | Normative. What may be decided without a new product decision. | in |
| `unresolved_questions` | Normative. `blocks_commitment: true` means not ready for a decision. | in |
| `advisory` | **Non-normative.** Prototypes, design explorations, generated reports, AI analyses. | **out** |

The two behavior fields carry disjoint kinds deliberately. A Rule recorded as a constraint is
invisible to every scope check — which is how behavior quietly stops being part of what anyone
verifies — and a constraint recorded as scope inverts the same mistake.

**A prototype listed in `advisory` contributes no requirement.** If behavior it demonstrates
should be committed, it must appear in `selected_behavior` — which is a decision someone makes,
not an inference a tool draws. The worked fixture exercises exactly this: the prototype sent
automatically, and `automatic-send-on-high-confidence` is an *exclusion* with a reason.

An AI "no functional change" classification is advisory. It is never a bypass for review.

---

## 7. Conforming a consumer

The fixtures ship with the package (`governance/` is force-included into the wheel at
`cli/governance/`), so a consumer conforms without a checkout of this repository beside theirs.
Resolve them through the bundled-asset anchor — `cli.paths.GOVERNANCE_DIR` in Python — rather than
a path relative to a source tree.

| Fixture set | Assert |
|---|---|
| `valid/support-response.baseline.json` | conforms to the schema; passes every cross-field check |
| `valid/support-response.digest` | your implementation computes exactly this digest |
| `digest-vectors/same--*.json` | digest equals the golden vector |
| `digest-vectors/differs--*.json` | digest differs from the golden vector |
| `invalid/*.json` | rejected — see the table below for which mechanism catches each |

Nine of the nineteen invalid fixtures fail the **schema**: missing opportunity reference, no
sources, no selected behavior, a mutable revision, a moving git tag on a repository source, a
source path escaping the repository, a self-asserted approval, an unqualified reference, and a
constraint listed as selected behavior.

The other ten are schema-valid and fail a **cross-field check**, because they are relationships
between fields rather than field shapes: unsupported version, a reference to an undeclared
source, a derived identifier, the same ref both selected and excluded, a duplicate reference, a
declared `kind` disagreeing with its ref, a blocking unresolved question, a duplicate
`source_key`, a duplicate exclusion, and an exclusion naming an undeclared source.

**Do not "fix" a baseline to make it pass.** A validator is read-only: it never rewrites a spec,
adds a missing identifier during enforcement, or silently upgrades a manifest. One that repairs
its input cannot detect drift, because it erases the drift it exists to find.
