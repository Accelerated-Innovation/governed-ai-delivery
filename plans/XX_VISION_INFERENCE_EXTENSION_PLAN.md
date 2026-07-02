# Vision-Inference Extension: Governed Consumption of Pretrained / Hosted Vision Models

**Status:** Plan only — no implementation yet.
**Author:** govkit working group
**Created:** 2026-06-05
**Target version:** govkit v0.12.0 (current v0.11.1) — lands independently of the `cv` type.
**Precedent:** `extensions/agentic-skills/` — same extension mechanism (in-place contract pack layered on a core type).
**Sibling plan:** [CV_TYPE_PLAN.md](CV_TYPE_PLAN.md) — the *training* shape. This is its orthogonal counterpart for *consumption*.

---

## 1. Summary

Add a govkit **extension** — `extensions/vision-inference/` — that governs applications which **consume** pretrained or hosted vision models rather than train them. Covers the two flavors confirmed in scope:

- **Discriminative vision APIs** — classify / detect / OCR via hosted (Rekognition, GCP/Azure Vision) or self-hosted (Triton/TorchServe) models.
- **Generative / VLM** — vision-language models (Claude vision, GPT-4V) and image generation (diffusion), which add a safety/guardrail/eval-as-judge surface.

### Why an extension, not a `--type`

A govkit `--type` earns its existence from a **distinct layered architecture**. Consumption has none — it **is the existing `api`/`cli` hexagon with one special outbound port** (the vision model). The entire spine of the `cv` training type (preprocessing → datasets → training → evaluation → leakage → reproducibility) does not apply. What consumption needs is a thin, cross-cutting contract pack bolted onto an existing shape — precisely the slot the [agentic-skills extension](../extensions/agentic-skills/) occupies.

This is a deliberate, candid scoping call: **inference-only is barely a model-training governance problem at all.** It's an external-dependency-integration problem with one genuinely vision-specific twist (biometric data leaving the building). Modeling it as a second training type would be wrong and would duplicate the `api` hexagon for no gain.

### What the extension mechanism buys us (vs the `cv` type)

Per the [extensions README](../extensions/agentic-skills/README.md): extensions are **agent-agnostic** and **not CLI-installed** — they live in-place under `extensions/<id>/` and are discovered by `apply`/`validate` scanning `extensions/*/manifest.yaml`. Consequences for this plan:

- **No parity ×3 tax** — one source of contracts, not triplicated across claude-code / codex / copilot.
- **No manifest / CLI / detect / doctor wiring** — nothing in `agents/*/manifest.json`, `cli/`, or CI `by_type`.
- It **layers on** `--type api` (or `cli`), reusing that type's ports/services/adapters governance for free.

That makes this materially lighter than the `cv` type — mostly contract authoring + a manifest + a schema.

---

## 2. Governance concerns (what consumption actually needs)

The training spine doesn't apply; these do:

| Concern | Why it matters for consumption |
|---|---|
| **Model behind a port/adapter** | The vendor model is an outbound dependency. No SDK leak into domain/services; provider swappable. Pure hexagonal — reuses `api` type governance. |
| **Model versioning + drift** | A hosted model changes under you. Pin model + version; record it with every prediction; detect when the provider's model moves. |
| **Black-box acceptance eval** | You can't retrain, but you must acceptance-test the consumed model on **your** held-out set, and re-gate on provider switch / version bump. A thin echo of the `cv` eval gate. |
| **Confidence-threshold decision policy + HITL** | What the system does with low-confidence predictions; when a human must review. |
| **Biometric data handling** | Sending images (faces) to a third party = consent, data-residency, retention, redaction. The genuinely vision-specific, and biggest, concern. |
| **Prediction observability** | Log input ref / output / confidence / model version / latency / cost — **PII-safe** (never log raw biometric images). |

---

## 3. Contract set

`extensions/vision-inference/docs/backend/architecture/` (mirrors how agentic-skills ships contracts):

### 3.1 Discriminative spine (always)

- `VISION_MODEL_PORT_CONTRACT.md` — the model is an outbound port behind an adapter; vendor SDK confined to the adapter; provider swappable; deterministic preprocessing at the boundary.
- `MODEL_VERSIONING_CONTRACT.md` — pin model + version; record version per prediction; drift detection when the hosted model changes; rollback policy.
- `INFERENCE_EVAL_CONTRACT.md` — black-box acceptance eval on a frozen held-out set; provider-switch / version-bump regression gate; per-class + per-slice breakdown; confidence-threshold decision policy + human-in-the-loop.
- `BIOMETRIC_DATA_HANDLING_CONTRACT.md` — consent, data residency, third-party transmission limits, retention, redaction; biometric/face as special category. **Shares language with the `cv` type's PII contract and the `data` type's `pii.md`** — DRY decision in §6.
- `PREDICTION_OBSERVABILITY_CONTRACT.md` — structured, PII-safe logging of prediction metadata (no raw biometric payloads); cost/latency/version captured.

### 3.2 Generative / VLM layer (`relates_to.extends` the L5 GenAI-Ops contracts)

Do **not** reinvent guardrails/eval-as-judge — extend the existing L5 contracts the agentic-skills extension already builds on:

- Extends: `GUARDRAILS_CONTRACT` (NSFW/safety on generated images + text), `EVALUATION_LLM_CONTRACT` (eval-as-judge for VLM outputs), `OBSERVABILITY_LLM_CONTRACT`, `llm-gateway`.
- New, vision-specific: `MULTIMODAL_INPUT_CONTRACT.md` — image+text prompt handling, **prompt-injection-via-image**, expected image size/format/normalization, output validation of generated content.

### 3.3 Schemas

`extensions/vision-inference/schemas/`:
- `extension-manifest.schema.json` (or reuse the agentic-skills one).
- `prediction-record.schema.json` — the per-prediction provenance record (model id + version, confidence, decision, slice tags) consumed by the acceptance-eval gate and observability.

---

## 4. `manifest.yaml`

Mirrors `extensions/agentic-skills/manifest.yaml`:

- `id: vision-inference`, `extension_type: architecture`
- `supported_levels: [4, 5]` — discriminative acceptance eval is L4-shaped; generative guardrails pull in L5.
- `supported_project_types: [api, cli]`
- `contract_sets`: `vision_inference` (discriminative spine) + `vision_generative` (VLM layer), each with `paths`, `applies_to` globs (`**/*vision*`, `**/*ocr*`, `**/*detect*`, `**/*classify*`, `**/*caption*`, `**/*vlm*`, `**/*predict*`, `**/*inference*`), `capabilities`, and `relates_to.extends` pointing at the L5 contracts for the generative set.
- `agent_guidance`: `architecture_preflight` / `implementation_plan` / `validation` blocks (load contracts when a feature touches vision consumption; require ADR for overrides; validate contract files exist + are cited).

---

## 5. Staging

- **PR 1 — discriminative spine:** ✅ **DONE (2026-06-05).** `extensions/vision-inference/` scaffold (`manifest.yaml`, `README.md`), the 5 spine contracts + `prediction-record.schema.json`, regression-guarded by `tests/test_vision_inference.py` (TDD red→green; full suite 141 passed). Self-contained; ships independently of the `cv` type. **Note:** contract filenames were chosen collision-free against the validate-extension overlap heuristic — `VISION_MODEL_ADAPTER`, `MODEL_VERSIONING`, `INFERENCE_ACCEPTANCE`, `BIOMETRIC_DATA_HANDLING`, `PREDICTION_LOGGING` (the §3.1 `_PORT_`/`_EVAL_`/`_OBSERVABILITY_` names would trip false overlaps with core `OBSERVABILITY_PORT`/`EVALUATION_LLM` contracts).
- **PR 2 — generative / VLM layer:** ✅ **DONE (2026-06-05).** `MULTIMODAL_INPUT_CONTRACT.md` + `vision_generative` contract set with `relates_to.extends` wired to the real L5 GenAI-Ops contracts (`GUARDRAILS`, `EVALUATION_LLM`, `OBSERVABILITY_LLM`, `LLM_GATEWAY`). Validates cleanly against repo root (those contracts exist there); in a non-L5 project the `extends` paths are missing and `doctor`/`validate` flag them — the closest thing to L5-gating, since `supported_levels` is inert. Regression-guarded by `tests/test_vision_inference.py::TestGenerativeLayer`.

No CLI/agent-parity work in either PR (extension mechanism).

---

## 6. Open decisions

1. **Extension id** — `vision-inference` (recommended) vs `vision-consumption` / `vision-model-adapter`.
2. **`supported_levels`** — `[4, 5]` (recommended; discriminative=4, generative=5) vs `[5]` only.
3. **Biometric DRY** — author `BIOMETRIC_DATA_HANDLING_CONTRACT.md` once and reference it from the `cv` type + `data` `pii.md`, or keep an extension-local copy. Leans toward a single shared contract.
4. **Self-hosted vs hosted parity** — confirm the `VISION_MODEL_PORT_CONTRACT` abstracts Triton/TorchServe and hosted APIs behind one port (expected yes; the port is the point).
5. **Black-box eval reuse** — does `INFERENCE_EVAL_CONTRACT` reuse the `cv` type's metrics-artifact schema, or a lighter consumption-specific one?

### Follow-ups surfaced during implementation (govkit-core gaps, not blockers)

These were discovered while building PR 1/PR 2. Both affect the existing
`agentic-skills` extension identically, so they are govkit-core changes, not
vision-inference-local — log here, decide separately.

6. **`supported_levels` / `supported_project_types` are inert.** Nothing in the CLI
   reads them — they're declared metadata only, so an extension is discovered and
   surfaced at *any* level/type. The only de-facto level gate today is
   `relates_to.extends` (the generative set's L5 paths are absent in a non-L5 project,
   so `doctor`/`validate` flag them). **Decision:** leave advisory, or have
   `validate_extension`/doctor compare `supported_levels` against the `.govkit` marker
   level (and `supported_project_types` against the marker type) and warn/fail on
   mismatch. If enforced, re-evaluate open decision #2.
7. **`capabilities` don't reach `skill_context`.** `cli/skill_context.py:_extension_facts`
   reads `manifest.get("capabilities")` at the top level, but both this extension and
   `agentic-skills` declare `capabilities` nested under `contract_sets[]`. Result:
   `contract_paths` project correctly into `.govkit/skill_context.yaml`, but
   `capabilities` come through as `[]`. **Decision:** lift capabilities to top-level in
   manifests, or teach `_extension_facts` to flatten nested `contract_sets[].capabilities`.

---

## 7. Relationship to the `cv` type plan

Orthogonal and complementary — different teams, different repos, different mechanism:

| | `cv` **type** ([CV_TYPE_PLAN](CV_TYPE_PLAN.md)) | `vision-inference` **extension** (this) |
|---|---|---|
| Shape | New `--type` with its own layered architecture | Contract pack layered on `--type api`/`cli` |
| User | Trains / fine-tunes models | Consumes pretrained / hosted models |
| Spine | preprocessing→datasets→training→evaluation | the `api` hexagon + a vision model port |
| Parity tax | ×3 agents + CLI/manifest/CI wiring | none (extension is agent-agnostic, in-place) |
| Eval | full eval-regression + leakage gate | black-box acceptance eval on held-out set |
| Shared | biometric/PII handling; black-box-eval language (candidates for one shared contract — §6.3) |

**Sequencing:** per your call, this plan is authored before `cv` PR 1. The two can then be implemented in either order; PR 1 of either is independently shippable. The only cross-link is the optional shared biometric contract (§6.3).
