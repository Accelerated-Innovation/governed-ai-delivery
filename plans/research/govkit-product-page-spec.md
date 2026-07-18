# GovKit — Elementor Product Page Spec

**Source of truth:** `governed-ai-delivery` repo (README.md, pyproject.toml, CHANGELOG.md, LICENSE, agents/, docs/). Version **0.13.0**, Apache-2.0.
**Build target:** acceleratedinnovation.com (WordPress + Elementor 4.1.1, Poppins, brand palette).
**Rule followed:** all install commands, CLI invocations, and code blocks are copied verbatim from the repo. Anything not found in the repo is marked **`TODO`** — never invented.

---

## SEO & placement (top of page)

**Meta title (≤60 char):**
`GovKit — Governed AI Delivery Toolkit | Accelerated Innovation`

**Meta description (155 char):**
`GovKit is a free, open-source pip-installable toolkit that puts your AI coding agent inside your architecture contracts, specs, and CI gates. pip install govkit.`
*(154 characters incl. spaces.)*

**Recommended URL slug:**
`/our-solutions/product-accelerators/govkit/`

**Placement recommendation — RECOMMENDED: under Our Solutions → Product Accelerators (as a child page), not standalone.**
The site already runs five accelerator tracks, and `/our-solutions/product-accelerators/` ("Leverage AI to accelerate innovation and product delivery across your business") is the exact home for a delivery tool. Nesting GovKit there inherits the breadcrumb, nav, and internal-linking equity of an established track, and lets the page's secondary CTA point "up" to the paid Product Accelerators consulting offer. A standalone top-level page would orphan it from that funnel. Keep the global header/footer; add a breadcrumb `Our Solutions → Product Accelerators → GovKit`.

> **Open Graph / Twitter:** reuse meta title + description. OG image = branded GovKit card (see Asset Callout A). `og:type` = `article` to match sibling pages.

---

## Global style notes for every section

- **Font:** Poppins. H1/H2 Bold, sub-heads Medium, body Regular/Light.
- **Eyebrow labels** (small all-caps text above a heading, e.g. `OPEN SOURCE`) match the site's existing "OUR SOLUTIONS / USE CASES" pattern — set as a Heading widget, HTML tag `h6`, letter-spacing ~2px, color Purple `#5865e7`.
- **Primary buttons:** background gradient `linear-gradient(35deg, #0abeef, #5865e7, #19004f)`, white `#f2f2f2` text. **Secondary buttons:** transparent / white border, Light Blue `#0abeef` text.
- **Section backgrounds alternate:** White `#f2f2f2` → Dark Purple `#19004f` (white text) for rhythm, matching the site's banded layout.
- **Code Highlight widget:** language per block (`bash`, `gherkin`, `yaml`, `text`). Dark theme; background Black `#1a1a1a`, accent Light Blue `#0abeef`.

---

## Section 1 — Hero

**Elementor widgets:** Heading (H1) · Text Editor (subhead) · Button ×2 (CTA group) · Code Highlight (install snippet) · optional Icon List (trust badges).

**Background:** Dark Purple `#19004f` with the 35° gradient as an overlay accent; white text.

**Eyebrow (h6):**
`OPEN SOURCE · PIP-INSTALLABLE · APACHE-2.0`

**H1:**
`Govern Your AI Coding Agent — Before It Drifts`

**Subhead (one line):**
`GovKit puts your AI coding agent inside a governed system where your architecture contracts, acceptance criteria, and evaluation thresholds are the source of truth — not the model's training data.`

**Primary CTA button:** `Install GovKit` → anchor to Section 4 (`#install`)
**Secondary CTA button:** `View on GitHub` → `https://github.com/Accelerated-Innovation/governed-ai-delivery`
**Tertiary text link:** `Read the docs →` → `https://github.com/Accelerated-Innovation/governed-ai-delivery#readme`
*(Repo has no separate docs site; docs live in the README/`docs/`. If a docs site is published later, swap this link. **TODO: confirm canonical docs URL if different from README.**)*

**Hero Code Highlight (language `bash`), verbatim from README:**
```bash
pip install govkit
govkit apply --agent claude-code --target .
govkit calibrate
```

**Trust line under the CTAs (Text Editor, small):**
`Works with Claude Code, GitHub Copilot, and OpenAI Codex · Any language — Python, C#, Java, Go, TypeScript · Python 3.11+ dev-tool requirement only, never a project dependency.`

**Asset Callout A — Hero "governed agent" badge / OG card.**
A square/landscape brand card showing the word-mark **GovKit** with a simple line-art motif of an AI agent (hexagon node) enclosed inside a contract/boundary frame — communicating "agent inside guardrails." Use the 35° gradient (`#0abeef → #5865e7 → #19004f`) for the frame, white `#f2f2f2` wordmark, Magenta `#821db0` accent dot. Poppins Bold. Deliver as SVG + 1200×630 PNG (OG).

---

## Section 2 — The problem GovKit solves

**Elementor widgets:** Heading (H2) · Text Editor · optional 3-column Icon List of failure modes.

**Background:** White `#f2f2f2`, black `#1a1a1a` text.

**Eyebrow (h6):** `THE PROBLEM`

**H2:**
`Powerful Agents, No Guardrails`

**Body (Text Editor), drawn verbatim from README framing:**
`AI coding agents are powerful — but without constraints, they drift. They invent architecture, skip tests, ignore NFRs, and make decisions that belong to your team. GovKit replaces "trust the model" with a governed workflow: your contracts, specs, and CI gates decide what good looks like — every feature, every time.`

**Optional 3 failure-mode chips (Icon Box ×3, one line each — all sourced from the README's drift list):**

1. **Invented architecture** — the agent reaches for patterns from its training data instead of your boundaries.
2. **Skipped tests & ignored NFRs** — non-functional requirements get left as "TBD."
3. **Team decisions made by a model** — architectural calls that should need an ADR slip through silently.

**Asset Callout B — "Drift vs. Governed" icon trio.**
Three small line icons in a row: (1) a tangled/forking arrow = *drift*; (2) a checklist/contract page = *spec*; (3) a shield with a check = *CI gate*. Stroke style, ~2px, Purple `#5865e7` default with Magenta `#821db0` hover. Transparent background SVGs.

---

## Section 3 — Core capabilities (icon-box grid)

**Elementor widgets:** Heading (H2) · Icon Box grid (3×2, six boxes). Each Icon Box = branded SVG icon + title + 1–2 sentence body.

**Background:** Dark Purple `#19004f`, white text; icons in Light Blue `#0abeef`.

**Eyebrow (h6):** `WHAT GOVKIT DOES`

**H2:**
`Governance Your Agent Actually Reads`

**Icon Box 1 — Governed agent rules**
`Path-scoped rules load automatically as the agent edits each layer — api, services, ports, adapters, security. The agent reads your architecture contracts on every turn, not its own assumptions.`

**Icon Box 2 — Spec-driven feature contracts (L4+)**
`Every feature lives under features/<name>/ with five required artifacts: Gherkin acceptance criteria, fully-populated NFRs, schema-validated eval criteria, an implementation plan, and an architecture preflight.`

**Icon Box 3 — Architecture & evaluation skills**
`Ships agent skills — /architecture-preflight, /spec-planning, /implementation-plan, /adr-author — that validate features against your contracts and predict FIRST + 7-Virtue quality scores before any code is written.`

**Icon Box 4 — CI gates that enforce, not suggest**
`govkit doctor checks whether installed governance still fits your repo; govkit validate checks whether your features meet the contract. Both run in CI: schema validation, NFR coverage, architecture-boundary enforcement, prediction thresholds.`

**Icon Box 5 — Multi-agent, multi-stack, monorepo**
`One toolkit for Claude Code, Copilot, and Codex, across FastAPI, .NET, Spring Boot, Fastify, Gin, dbt, and Databricks stack overlays. Monorepo-aware — one govkit apply per app subdirectory.`

**Icon Box 6 — GenAI operations (L5)**
`For LLM features, add governed model routing (LiteLLM), observability (OpenLLMetry + Langfuse), and evaluation/safety gates (DeepEval, Promptfoo, RAGAS, NeMo Guardrails, Guardrails AI).`

**Asset Callout C — Six capability glyphs (icon set).**
A cohesive set of six line-art glyphs on transparent background, ~64×64, 2px stroke, Light Blue `#0abeef` (active state Magenta `#821db0`):
1. Rules — a document with a path/route bracket.
2. Spec contract — a page with a checkmark and a "5" badge.
3. Skills — a wand/spark over a node.
4. CI gate — a pipeline with a shield.
5. Multi-stack — three stacked layers / hexagon cluster.
6. GenAI ops — a routing fork into a brain/LLM node.
Keep them visually consistent (same corner radius, stroke weight) so the grid reads as a family.

---

## Section 4 — Install & quickstart  `#install`

**Elementor widgets:** Heading (H2) · Text Editor (intro) · Code Highlight (steps) · Callout / Notice box (calibrate warning) · Button group.

**Background:** White `#f2f2f2`, black text. Anchor ID: `install`.

**Eyebrow (h6):** `GET STARTED IN 4 STEPS`

**H2:**
`Install, Apply, Calibrate, Commit`

**Intro (Text Editor), verbatim from README:**
`You need Python 3.11+ on your machine (GovKit is a dev tool, never a project dependency) and an AI coding agent — Claude Code, GitHub Copilot, or OpenAI Codex. GovKit ships the governance configuration; you bring the agent.`

**Code Highlight 1 — Step 1 (language `bash`):**
```bash
pip install govkit
```

**Code Highlight 2 — Step 2, from your project root (language `bash`):**
```bash
govkit apply --agent claude-code --target .
```
Caption (Text Editor): `GovKit detects your stack (language, framework, CI), scaffolds the agent rules + architecture contracts, and writes a .govkit marker recording your configuration.`

**Code Highlight 3 — Step 3 (language `bash`):**
```bash
govkit calibrate
```

**Notice / Callout box (use a colored Call-to-Action or styled Text Editor — Magenta `#821db0` left border), verbatim emphasis from README:**
`This step is not optional. The files GovKit installs are sound generic defaults — and your agent treats them as law. If you skip calibration, the agent governs your project against someone else's architecture decisions. govkit calibrate walks you through a 9-step review; prefer to review with the team first? Run govkit calibrate --non-interactive to write a checklist file instead.`

**Code Highlight 4 — Step 4, commit your baseline (language `bash`), verbatim:**
```bash
git add .govkit CLAUDE.md docs/ governance/ ci/
git commit -m "chore: add govkit governance baseline"
```

**Upgrade note (Text Editor, small), verbatim:**
`Upgrading later? pip install --upgrade govkit && govkit upgrade --target . refreshes the files GovKit owns without touching the contracts you've customized.`

**Button group:**
- Primary: `View on PyPI` → `https://pypi.org/project/govkit/`
- Secondary: `Full quickstart on GitHub` → `https://github.com/Accelerated-Innovation/governed-ai-delivery#get-started-in-4-steps`

**Asset Callout D — 4-step horizontal flow diagram.**
A linear 4-node flow: **Install → Apply → Calibrate → Commit**, each node a rounded chip connected by gradient arrows. Node fills white with Purple `#5865e7` numerals (1–4); connectors in the 35° gradient. Poppins Medium labels. Deliver SVG (full-width on desktop, stacks vertically on mobile).

---

## Section 5 — Real examples (CLI + code)

**Elementor widgets:** Heading (H2) · Tabs or stacked Code Highlight widgets · short Text Editor captions.

**Background:** Dark Purple `#19004f`, white text; code blocks dark.

**Eyebrow (h6):** `SEE IT IN USE`

**H2:**
`From Spec to Governed Feature`

**Example 1 — Scaffold a feature, then govern it (Code Highlight, language `bash`), verbatim from README feature lifecycle:**
```bash
govkit init my_feature --target .
```
Caption: `Creates features/my_feature/ from the appropriate starter (Level 4+). At L3 this errors with a pointer to --level 4 — Foundations ships rules and contracts only.`

**Example 2 — Drive the agent through the lifecycle (Code Highlight, language `text`), verbatim agent commands (Claude Code):**
```text
/architecture-preflight my_feature
/adr-author my_feature
/spec-planning my_feature
/implementation-plan my_feature
```
Caption: `The agent produces architecture_preflight.md, plan.md, and eval_criteria.yaml — and will not proceed if predicted FIRST or 7-Virtue averages fall below 4.0.`

> **Agent-equivalents note (render as a small Text Editor or 3-col table):** Copilot infers the feature from context (e.g. `/architecture-preflight`); Codex invokes skills with a `$` prefix (e.g. `$architecture-preflight my_feature`). Verbatim from README "Agent command equivalents."

**Example 3 — A feature's acceptance criteria (Code Highlight, language `gherkin`).**
The README shows the Gherkin *tagging convention* verbatim; it does not print a full ready-made `.feature` body. Use the convention text as the caption and show the worked-starter tags that the repo documents verbatim:
Caption: `Tag NFR scenarios with @nfr-performance, @nfr-security, etc.; tag E2E scenarios with @e2e (UI); add @contract scenarios when a feature produces shared artifacts. The bundled data starter (govkit init <feature> --starter data) scaffolds a customer_dim_freshness feature with @nfr-freshness / @nfr-quality / @nfr-pii / @nfr-lineage / @nfr-reliability / @nfr-cost scenarios.`
> **TODO (optional):** if you want a full `Feature:`/`Scenario:` block displayed, copy one verbatim from a bundled starter in the repo (e.g. `features/starter_backend/acceptance.feature`) — I did not invent one. Point me at it and I'll drop it in verbatim.

**Example 4 — Validate compliance in CI (Code Highlight, language `bash`), verbatim:**
```bash
govkit validate --target .
```
Caption: `Level-aware per-feature compliance — artifact existence, Gherkin structure, NFR coverage, eval-criteria schema, prediction thresholds. No-op at L3. Pair with govkit doctor for governance-fit checks.`

**Asset Callout E — Lifecycle ribbon (optional).**
A horizontal 8-step ribbon mirroring the README lifecycle: *Create folder → Acceptance criteria → NFRs → Preflight → Plan → Review → Implement → Merge.* Compact numbered dots on a gradient track; Light Blue `#0abeef` dots, white labels on the dark band. SVG.

---

## Section 6 — Who it's for / use cases

**Elementor widgets:** Heading (H2) · Icon Box or Card grid (3 cards) · Text Editor.

**Background:** White `#f2f2f2`, black text.

**Eyebrow (h6):** `WHO IT'S FOR`

**H2:**
`Built for Teams Shipping With AI Agents`

> **Note:** the README has no dedicated "personas/use cases" section. The three cards below are **derived from capabilities the repo actually supports** (maturity levels L3–L5 and project types), phrased as audiences. They introduce no features not in the repo. Adjust voice freely.

**Card 1 — Engineering teams adopting AI coding agents**
`Start at Level 3 (Foundations) — governed agent rules and architecture contracts with no codebase restructuring. Your agent follows your hexagonal boundaries from day one.`

**Card 2 — Teams committing to spec-first delivery**
`Move to Level 4 for spec-driven, test-first feature delivery: the five-artifact feature contract, feature-coupled skills, and governance CI jobs that gate every PR.`

**Card 3 — Teams shipping LLM-powered features**
`Move to Level 5 — GenAI Operations: governed model routing, LLM observability, and evaluation/safety gates so your LLM features are routed, evaluated, and guarded by contract.`

**Supporting line (Text Editor):**
`Backend APIs, CLIs, React or Angular UIs, and governed dbt / Databricks data projects — across Claude Code, GitHub Copilot, and OpenAI Codex. Any project language; GovKit copies Markdown specs, YAML configs, and Gherkin files into your repo.`

**Asset Callout F — Maturity-ladder diagram.**
A three-rung ascending ladder/stack labeled **L3 Foundations → L4 Spec-Driven → L5 GenAI Operations**, each rung wider/taller than the last to show the additive model (L4 ⊃ L3, L5 ⊃ L4). Rung fills step through the gradient stops (`#19004f` base → `#5865e7` mid → `#0abeef`/`#821db0` top). White Poppins labels with a one-line descriptor each. SVG, vertical on mobile.

---

## Section 7 — Open-source credibility

**Elementor widgets:** Heading (H2) · Icon List (facts) · Button group · optional Image (shields/badges).

**Background:** Dark Purple `#19004f`, white text.

**Eyebrow (h6):** `OPEN SOURCE`

**H2:**
`Free, Apache-2.0, and Yours to Inspect`

**Fact list (Icon List — each line a real repo fact):**
- **License:** Apache-2.0 — free for commercial use.
- **Package:** `govkit` on PyPI · current version **0.13.0**.
- **Requires:** Python 3.11+ (dev-machine tool only; never a project dependency).
- **Runtime dependency:** a single one — `PyYAML`. No heavyweight footprint.
- **Agents supported:** Claude Code · GitHub Copilot · OpenAI Codex.
- **Maintained by:** Accelerated Innovation.

**Button group:**
- Primary: `Star on GitHub` → `https://github.com/Accelerated-Innovation/governed-ai-delivery`
- Secondary: `View on PyPI` → `https://pypi.org/project/govkit/`
- Text link: `Read the CHANGELOG →` → `https://github.com/Accelerated-Innovation/governed-ai-delivery/blob/main/CHANGELOG.md`

> **TODO:** confirm the default branch name for raw links (`main` vs `master`) before publishing. Star/issue counts change over time — don't hard-code them; embed live shields.io badges or omit.

**Asset Callout G — Badge strip (optional).**
Reuse the README's real badges as a horizontal strip: PyPI version, Python 3.11+, License Apache-2.0, CI Publish status. Either embed the live shields.io images from the README or recreate as brand-colored static chips (Purple `#5865e7` / Light Blue `#0abeef`).

---

## Section 8 — Closing CTA band

**Elementor widgets:** Call to Action widget (or Heading + Button group inside a full-width Section) on the gradient background.

**Background:** full 35° gradient `linear-gradient(35deg, #0abeef, #5865e7, #19004f)`, white text.

**H2:**
`Put Your AI Agent on Rails`

**Subhead (one line):**
`Install GovKit, apply it to your repo, and let your contracts — not the model — decide what good looks like.`

**Code Highlight (inline, language `bash`):**
```bash
pip install govkit
```

**Button group (three CTAs, as requested):**
- Primary: `Install GovKit` → `https://pypi.org/project/govkit/`
- Secondary: `View on GitHub` → `https://github.com/Accelerated-Innovation/governed-ai-delivery`
- **Consulting (secondary funnel):** `Accelerate delivery with our team →` → `https://acceleratedinnovation.com/our-solutions/product-accelerators/`

**Microcopy under buttons (Text Editor, small):**
`Free and open source. Want help rolling governed AI delivery out across your teams? Talk to Accelerated Innovation.`

**Asset Callout H — CTA band motif.**
Subtle background motif on the gradient band: faint line-art of the "agent-in-contract" hexagon from the hero, scaled large at ~10% white opacity, bottom-right. Keeps the band on-brand without competing with the text. SVG overlay.

---

## Build checklist for Elementor

1. Create page at slug `/our-solutions/product-accelerators/govkit/`; set parent = Product Accelerators; add breadcrumb.
2. Paste meta title + description into your SEO plugin (Yoast/RankMath) fields; set OG image to Asset A.
3. Build 8 sections top-to-bottom; alternate White / Dark-Purple backgrounds; closing band = full gradient.
4. Set global Poppins weights and brand color swatches in Elementor's Site Settings so widgets inherit them.
5. Drop the eight asset callouts (A–H) to your designer; all are SVG-first, transparent background, brand palette only.
6. Replace the four **TODO** items before publishing: docs URL, default branch name, optional full Gherkin block, and any live badge embeds.

---

## Verbatim-source index (for your fact-check)

- Install / apply / calibrate / commit commands → README "Get started in 4 steps."
- Command table & descriptions (`apply, calibrate, doctor, validate, init, stack, extension, upgrade, list`) → README "Commands."
- Maturity levels L3/L4/L5 wording → README "Maturity Levels."
- Skill names (`/architecture-preflight, /adr-author, /spec-planning, /implementation-plan`, plus L5 `/genai-preflight, /eval-suite-planning`) → README + `agents/claude-code/skills/`.
- Stacks list → README "Bundled stacks."
- Gherkin tags & data starter (`customer_dim_freshness`) → README "Data" + lifecycle steps.
- Version 0.13.0, Apache-2.0, PyYAML dep, Python 3.11+ → pyproject.toml.
- Drift framing ("invent architecture, skip tests, ignore NFRs") → README intro.
