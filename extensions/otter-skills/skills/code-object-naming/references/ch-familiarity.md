# Digest: Readability as Familiarity (ch: familiarity)

## Core insight
> Readability is not a property of code; it's a **relationship** between code
> and its audience.

Code is "unreadable" when parsing effort is felt to be unreasonably high by its
intended readers. This is audience-relative, not absolute.

## Profitable vs. unprofitable struggle

| Type | Definition | Action |
|---|---|---|
| **Profitable** | Unfamiliar code that, once understood, adds a valuable tool to the reader's mental toolbox | Accept; teach it; it pays forward |
| **Unprofitable** | Difficult code with no learning dividend — just friction | Refactor or rename |

Examples:
- Python list comprehension `[x.name for x in items if x.active]` — profitable
  for any Python programmer to learn.
- Arbitrary abbreviations or invented metaphors in a narrow codebase — unprofitable.

## The audience question
*Who is your primary audience?*
- Your immediate team (current + future members)
- A broader developer community (OSS, SDK)
- Domain specialists (DSP engineers, financial quants, medical informatics)

The readable choice aligns with how **that audience** already thinks and talks.
`customer` or `user`? Whichever word your team uses in conversation.

## Language and framework idioms
Each language has conventions that its practitioners recognize instantly.
Departing from them imposes cognitive cost even when the departure is
"technically correct."

- Rails `has_many :posts, dependent: :destroy` — immediately clear to Rails devs.
- Pandas `df`, NetworkX `G`, Plotly `fig` — idiomatic; non-idiomatic replacements
  confuse without helping.

## Building shared familiarity
1. **Co-create code** — pair, mob, or ensemble programming embeds shared idioms.
2. **Live code review** — synchronous walkthrough beats async comment threads for
   building vocabulary and resolving naming disagreements.
3. **Shared coding standards** — focus on *naming, organization, and expression*,
   not formatting (let `black`/`prettier` handle that).

## Practical guidelines (from manuscript)
1. Know your audience.
2. Align with existing mental models — team vocab and domain vocab.
3. Be consistent within your context.
4. Invest in shared vocabulary — document and discuss conventions.
5. Ensure cognitive effort teaches something valuable (profitable struggle test).
