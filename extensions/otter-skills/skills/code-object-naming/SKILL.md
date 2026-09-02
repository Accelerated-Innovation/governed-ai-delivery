---
name: code-object-naming
description: >
  Diagnose and improve names for code objects — variables, functions, methods,
  classes, modules, and parameters — using Ottinger's naming guide. Use when
  asked to review, choose, or rename identifiers; when names are vague, lying,
  redundant, or noisy; when planning an incremental rename refactor; or when
  extraction moments arise from hard-to-name code. Use
  representation-refactor-review instead for a broad craft or knowledge-
  representation review in which naming is only one concern.
---

# Code Object Naming

## Why Names Matter
Names are not for the compiler—they are for every human and AI that reads,
debugs, extends, or maintains the code. Good names:
- Speed defect location (~20% faster)
- Reduce documentation and comments needed
- Reduce misunderstanding-driven errors
- Improve LLM comprehension efficiency (up to ~30% fewer tokens wasted)

Names are a secondary concern only when the code is broken, untested, unsafe,
or undeployable. Once those are true, naming matters.

---

## Diagnostic Workflow

### Step 1 — Diagnose the Name

Locate the name on Belshee's naming process scale:

| Stage | What it looks like |
|---|---|
| **Missing / Nonsense** | No name, UUID-style, `tmp`, `data`, `info`, `obj` |
| **Honest but Incomplete** | Names one use but the item has broader scope |
| **Honest and Complete** | Lists all purposes but is long and unfocused |
| **Intention-Revealing** | Clear about *purpose* and carries needed context |
| **Domain Abstraction** | Single-purposed, domain-consistent, concerns separated |

**Target**: Intention-Revealing or Domain Abstraction.
**Acceptable temporary stop**: Honest but Incomplete (never Nonsense).

> If you cannot name it well right now, give it an *obviously bad* name
> (e.g., `applesauce`, `poop`, `doomed_X`) — easy to search, clearly
> temporary, embarrassing enough to remove before commit.

---

### Step 2 — Assign the Right Part of Speech

| Code object | Preferred grammar | Examples |
|---|---|---|
| Variables, parameters, fields | **Noun** | `customer`, `hourly_rate`, `invoice` |
| Data structures, classes | **Noun** | `OrderQueue`, `PaymentRecord` |
| Commands (mutations, actions) | **Verb phrase** | `dial()`, `submit_order()`, `cancel()` |
| Queries / attribute getters | **Noun preferred** (not `get_`) | `customer.preferred_name()` not `get_preferred_name()` |
| Interfaces, protocols, mixins | **Adjective / capability** | `Serializable`, `FileLike`, `Runnable` |
| Abstract base / interface pair | **Qualified noun** | `Messenger` → `SMSMessenger`, `EmailMessenger` |

**Decision rule**: Ask *"Is this a command (tell) or a query (ask)?"*
Commands → verb. Queries → noun. Ambiguity → rename until it's clear.

`as` conversion methods (e.g., `customer.date_as_ISO8601`) often signal a
missing whole value object — consider extracting a type.

---

### Step 3 — Apply Context and Familiarity

**Context hierarchy** (outer to inner): system → module → file → class →
method → variable. Each layer provides context; names inside need not repeat
what the layer already says.

**Redundancy test**: Is the word present in the enclosing class/method name?
Strip it from the member name.
```
# Bad — "employee" repeats class context
class Employee:
    employee_hourly_rate: Decimal

# Good
class Employee:
    hourly_rate: Decimal
```

**Windshield naming**: Name by *purpose* (windshield = shields from wind),
not *composition* (front glass). Ask "What is this *for*?" not "What is it
*made of*?"

**Domain terms**: Use the vocabulary domain experts use, even if it requires
learning. `mrn` (Medical Record Number), `apy` (Annual Percentage Yield),
`commit_hash` — profitable struggle. When developers learn the domain term,
they gain vocabulary that appears everywhere: code, UI, conversations.

**Familiarity check**: Readability is a *relationship* between code and its
audience. Prefer team idioms and language conventions over universal rules.
- **Profitable struggle**: unfamiliar but worth learning (new language feature,
  domain term, idiomatic library pattern).
- **Unprofitable struggle**: unfamiliar with no payoff — refactor this.

---

### Step 4 — Size to Scope

Match name length to how far the name must travel.

| Scope / travel | Appropriate length | Example |
|---|---|---|
| Single expression / lambda | Single letter or `x` | `lambda x: x > 0` |
| Short loop, tiny function | Short | `rate`, `hours`, `order` |
| Multi-use within a function | Descriptive | `git_repo`, `validated_data` |
| Exported / used outside module | Carry full context | `git_repository`, `order_validator` |

**Rules of thumb**:
1. Length ~ scope. Short scope → shorter name.
2. Clear in its context, not universally.
3. Don't bury the lede — put the unique/meaningful part *first* (aids
   autocomplete and searchability).
4. Idiomatic names win: `df`, `G`, `fig`, `pd`, `nx` are unambiguous to
   their community.

---

### Step 5 — Rename or Extract

**Incremental rename protocol**:
1. Pick the name up one level on Belshee's scale (don't try to leap from
   Nonsense to Domain Abstraction in one shot).
2. Use **IDE semantic rename** — never grep-and-replace (too blunt; misses
   scope; cascades errors).
3. Run tests after each rename, even tiny ones.
4. Test the name with a teammate: does it feel natural? Do several people
   agree?

**Do NOT rename**:
- Public API names (breaking change)
- Names used by framework reflection
- Names in separately-maintained documentation

**Extraction moments** — when to extract rather than (only) rename:

| Signal | Action |
|---|---|
| Block has a paragraph comment | Extract the block to a function; use comment text as name seed |
| Complex boolean condition | Extract to `is_eligible_for_X()` predicate function |
| Variable with long explanatory name | Extract to a named function returning the value |
| Class is hard to name | Class likely has multiple responsibilities — split it |
| Repeated `as_X()` conversion method | Signal for a whole value object type |
| Name is fine in its file, confusing outside | Add context via import alias or rename |

> Extraction builds vocabulary. Every extracted function is a named concept
> that makes the codebase more browsable and its tests more focused.

---

## Quick Checklists

### Name Audit (per identifier)
- [ ] Does the name describe *purpose* (windshield) rather than composition?
- [ ] Is the name's part of speech correct for its role (noun/verb/adjective)?
- [ ] Does it avoid repeating context already provided by the enclosing scope?
- [ ] Is the meaningful/unique segment at the *front* of the name?
- [ ] Does the length match the scope (travel distance)?
- [ ] Does it use domain or team vocabulary (not invented jargon)?
- [ ] Is it distinguishable from nearby names?

### Rename Readiness
- [ ] Is this name safe to rename (not public API, not reflection-referenced)?
- [ ] IDE semantic rename available?
- [ ] Tests will run after rename?
- [ ] Rename is one step on Belshee's scale, not a giant leap?

---

## Cross-links
- **representation-refactor-review** owns broad review against all Eight Code
  Virtues. Use this skill when identifier choice, diagnosis, or a safe rename is
  the primary task; use the broader skill when naming is one symptom of a
  larger representation problem.
- **unit-testing** owns test-first behavior changes. Routine naming inside its
  green refactor step stays there; use this skill for a deeper naming pass.

---

## References (progressive disclosure)
Deeper chapter digests in `references/`:
- `ch-nouns-and-verbs.md` — parts of speech, getter naming, framework idioms
- `ch-context.md` — hierarchy, windshield naming, domain terms, over-contextualization
- `ch-familiarity.md` — profitable struggle, team idioms, shared vocabulary
- `ch-length.md` — scope-to-length matching, primacy, idiomatic nicknames
- `ch-incrementalism.md` — Belshee's scale, obviously-bad names, safe rename
- `ch-extraction.md` — paragraph markers, explanatory variables, class split signals
