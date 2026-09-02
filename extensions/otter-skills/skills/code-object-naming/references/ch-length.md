# Digest: Length of Names (ch: length)

## The scope-length principle
> A name only needs to carry its meaning as far as it must travel.

| Scope / travel distance | Appropriate length | Rationale |
|---|---|---|
| Single expression, lambda body | Single letter (`x`) | Scope is one expression; context unambiguous |
| Short loop body | Short (`rate`, `hours`) | Visible from declaration to last use |
| Multi-use within a function | Descriptive (`git_repo`) | Disambiguation needed |
| Used across functions in a module | Qualified (`order_validator`) | Travels; needs self-sufficiency |
| Public API / exported name | Full context (`payment_gateway_client`) | Encountered alone in the wild |

## Single-letter names: not forbidden
Single letters work when:
1. Scope is tiny (lambda, comprehension filter, short for-loop)
2. Context is unambiguous (only one concept in scope)
3. Convention supports it (`i`, `j` in matrix loops; `x`, `y` for coordinates;
   `a`, `b`, `c` in quadratic formula; `e` in exception handlers)

Problematic when the variable's declaration, initialization, and last use are
too far apart to hold in one glance.

## Redundant context adds noise, not meaning
```python
# Bad — "git" already in module name; "VersionControl" and "Repository" redundant
git.GitVersionControlRepository(path)

# Good
git.Repository(path)
```
Redundant prefixes degrade autocomplete (all words share a prefix; meaningful
part buried at the end) and add "deodorant formatting" pressure (line-wrapping
to fit the long name).

## Primacy of the unique segment
In long names, put the **meaningful / unique part first** — it aids autocomplete
and search. Burying the lede (unique part in the middle) means every user scans
past the common prefix to find the differentiator.

If you inherit a buried-lede name you can't rename: create a local alias in
your function, work with it, then rename the original later.

## Idiomatic nicknames
Some short names are idiomatic within their community and should be honored:

| Name | Community meaning |
|---|---|
| `pd` | Pandas (Python) |
| `nx` | NetworkX (Python) |
| `px` | Plotly Express (Python) |
| `df` | DataFrame (Pandas / Databricks) |
| `G` | Graph/DiGraph (NetworkX) |
| `fig` | Figure/chart (Plotly) |
| `e` | Exception (many languages) |
| `i`, `j` | Loop indices |

These are not "cryptic" — they are vocabulary. Using non-idiomatic replacements
confuses practitioners without benefit.

## Rules of thumb (from manuscript)
1. Length ~ scope (shorter scope → shorter name).
2. Clear in its context, not universally.
3. Don't bury the lede — unique segment goes first.
4. Idiomatic use trumps other rules.

## Practical exercise (from manuscript)
Commit your work first. Revise a function's names to follow these rules.
Run `git diff` and compare with a teammate. Notice that the first reaction
may be to the unfamiliarity of the style — ask whether it's easier to
*understand at a glance* rather than whether it *looks familiar*.
