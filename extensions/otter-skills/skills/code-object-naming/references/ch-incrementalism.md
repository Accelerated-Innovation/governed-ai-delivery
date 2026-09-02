# Digest: Incrementalism (ch: incrementalism)

## Naming is a process, not a moment

Arlo Belshee's naming-as-a-process model (https://www.digdeeproots.com/articles/naming-process/):

| Stage | Characteristics | OK to commit? |
|---|---|---|
| **Missing / Nonsense** | No name, UUID, `tmp`, `obj` | No — never leave this |
| **Honest but Incomplete** | Names one use; broader scope exists | Acceptable temporary state |
| **Honest and Complete** | Lists all purposes; long; unfocused | Acceptable; aim higher |
| **Intention-Revealing** | Clear about *purpose*; carries needed context | Good — ship it |
| **Domain Abstraction** | Single-purposed; domain-consistent; concerns separated | Best |

Move names **one step at a time** up this scale. Leaping from Nonsense to
Domain Abstraction in one step usually fails.

## Obviously-bad names as placeholders
> "If you can't give it a good name, give it a terrible one." — Ottinger & Belshee

Criteria for an obviously-bad placeholder:
1. **Easy to search** — unique enough to find with a grep/IDE search
2. **Clearly temporary** — nobody will mistake it for a final name
3. **Embarrassing enough to fix** — you will not commit this name

Examples: `applesauce`, `poop`, `doomed_print_report`, `new_thing_being_built`

Do NOT use `data`, `info`, `customerInfo` as temporaries — they look like
real names and will be abandoned in the codebase.

## Obviously-temporary names for in-flight refactors
- Prefix with `doomed_` when deprecating: `doomed_print_report()`
- Prefix with `new_` when introducing: `new_invoice_builder`
- Add a `# TODO: rename` comment at the definition site
- These signal to teammates that the item is transitional

## Safe rename protocol
1. **IDE semantic rename only** — rename via the IDE's refactoring support,
   never grep-and-replace.
   - Search-and-replace is too blunt (crosses scope boundaries, finds string literals)
   - "Rename + compiler errors" is semantic rename the hard way — tedious and
     prone to cascading errors
2. **One rename at a time** — do not fix adjacent names while doing one rename.
   Scope creep causes unrelated failures.
3. **Run tests after each rename** — even tiny renames; catch breakage immediately.
4. **Test the name with the team** — a name that feels natural to several people
   is more stable than a solo invention.

## What you cannot (safely) rename
- **Public API names** — breaking change for downstream consumers
- **Reflection-referenced names** — frameworks that look up names at runtime
  (Spring, Rails conventions, some ORMs)
- **Separately-maintained documentation** — names that appear in external specs,
  contracts, or docs not under your control

## Incremental improvement heuristics
1. Extract the most obvious functions first — blocks with existing comments
   are pre-labeled; use the comment as name seed.
2. Let good names surface bad ones — once some names are clear, poor names
   stand out more sharply.
3. Refactor in small steps; test after each one.
4. The goal is to become more correct over time, not to achieve perfection
   before the first commit.
