# Data Clusters, Construction Semantics, and Class Boundaries

Use this pass to decide whether a data cluster deserves a type or an existing class contains independently meaningful concepts. The goal is knowledge ownership, not more classes.

## Core distinction

> Introduce a class when related data and behaviour repeatedly travel together and have rules worth owning. Split a class when its data and methods form independently meaningful clusters joined by little shared behaviour.

Method/field clumping discovers candidate boundaries. Construction, invariants, lifecycle, and the resulting interface confirm or reject them.

## Trace construction semantics

For a suspected concept, find every path that can create or assemble it:

- constructors, named factories, builders, parsers, and conversion methods
- deserializers, ORM/framework hydration, copying, and mutation after empty construction
- test fixtures and object mothers that may reveal required preparation
- callers that repeatedly validate, normalize, default, derive, or repair the same values

Record:

- canonical inputs and required/optional values
- defaults and which boundary supplies them
- rejected combinations and other invariants
- normalization, canonicalization, and unit conversion
- values derived from other inputs and any ordering dependency
- whether partial or invalid states are representable
- identity, equality, mutability, and lifecycle
- construction effects such as IDs, timestamps, persistence, registration, or events
- competing construction dialects or invariant-bypassing paths

The language constructor is not necessarily the authoritative constructor. Repeated caller preparation may be the real construction policy scattered without an owner.

## Decide what kind of representation exists

| Evidence | Candidate representation |
| --- | --- |
| Values merely travel together | Parameter object or data record |
| Values share validity or normalization rules | Value object with guarded construction |
| Several input forms converge on one valid form | Named factories or parsers |
| Optional groups accumulate over stages | Builder, draft, or explicit staged state |
| Some fields are derived from canonical inputs | Factory that computes rather than accepts them |
| Identity and independent lifecycle matter | Entity rather than value object |
| Trusted storage must bypass ordinary creation | Explicit rehydration boundary |

These are hypotheses, not automatic pattern prescriptions. Prefer local idioms and the smallest representation that gives the knowledge one authoritative home.

## Find class partitions

Treat fields and methods as a small dependency graph:

- connect each method to the fields it reads or changes
- connect methods that call one another or maintain the same invariant
- identify dense groups with few cross-group connections

Then test each candidate group:

1. Can it be named as a domain or system concept without `Helper`, `Data`, `Part`, or an unexplained `Manager`?
2. Does it own rules or behaviour, not merely occupy adjacent lines?
3. Can it be constructed and remain valid through a coherent boundary?
4. Can its relationship with the original class be expressed through a small intention-revealing interface?
5. Does extraction avoid duplicated state, bidirectional synchronization, and chatty forwarding?

Evidence becomes stronger when the groups also have separate construction sources, invariants, optionality, lifecycles, tests, uses, or change history.

## Check counterevidence

Do not recommend splitting merely because clumps exist. A single owner may remain better when:

- an invariant genuinely spans the candidate groups
- the groups are born, change, and die together
- extraction creates constant back-and-forth calls or shared mutation
- one group is only a serialization, persistence, or presentation view of the other
- the class is intentionally a thin facade or application-service orchestrator
- framework callbacks obscure an otherwise coherent responsibility

Ask:

1. Are the groups born together?
2. Are they valid under shared rules?
3. Do they change together?
4. Do they die together?
5. Is either meaningful and useful without the other?

Mostly “no, no, no, no, yes” strongly supports a split. Mixed answers require judgment; report uncertainty rather than forcing extraction.

## Minimum recommendation thresholds

Recommend **introducing a class** only with both:

- repeated grouping or travel of the same values; and
- shared construction rules, invariants, normalization, or behaviour.

Recommend **splitting a class** only with all three:

- at least two distinct method/field clusters;
- a meaningful concept name for each cluster; and
- necessary cross-cluster interaction expressible through a small interface.

Size and counts alone never meet either threshold. Clumping alone warrants investigation, not a recommendation.

## Evidence record

```text
Concept or class:
Data and method clusters:
Construction sites and semantics:
Shared and independent invariants:
Lifecycle and co-change evidence:
Cross-cluster interactions:
Candidate names and ownership:
Evidence against extraction:
Smallest representation improvement:
Unknowns requiring characterization:
```

## Incremental refactoring

When implementation is authorized:

1. Characterize current construction and invariant behaviour.
2. Gather a repeated parameter cluster without changing semantics.
3. Move one normalization, default, or invariant to the emerging owner.
4. Redirect one creation path or method cluster at a time.
5. Separate ordinary creation from parsing, rehydration, and fixture construction when their trust boundaries differ.
6. Run relevant tests after every step and apply the improvement test.
7. Remove bypasses only after all callers migrate.

Keep an extraction only when Working is preserved and the resulting ownership and interface improve the peer virtues together.
