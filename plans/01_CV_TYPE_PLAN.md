# CV Type: Governed Computer-Vision Model Development

**Status:** Plan only — no implementation yet.
**Author:** govkit working group
**Created:** 2026-06-05
**Target version:** govkit v0.12.0 (current v0.11.1 per release history)
**Precedent:** `--type data` + the `python-dbt` stack overlay (v0.10.x–v0.11.x) — this plan mirrors that pairing.

---

## 1. Summary

Add a new project shape **`--type cv`** for computer-vision model development, paired with a **`python-tensorflow-vision`** stack overlay. The type imposes a separation-of-concerns contract on CV code — the discipline CV developers (and the agents writing for them) routinely collapse into a single leakage-prone notebook — and enforces the highest-value boundaries in CI.

Scope is **discriminative vision** (classify / detect / segment) for two user profiles: **training from scratch** and **fine-tuning pretrained backbones**. Inference-only consumption is out of scope (that's closer to `--type api` with a model-adapter port). Generative / multimodal vision is explicitly deferred — see §7.

**Ship L3 + L4 now. Defer L5.** L3 is the SoC spine; L4 adds the eval-regression + leakage gate, which is where CV maps onto govkit unusually well. L5 today is GenAI-Operations-shaped (LLM gateway, guardrails, prompt eval) and does **not** fit discriminative CV; a CV "Model Operations" L5 is a separate, later decision gated on the generative-vs-discriminative question.

### Why this is a good fit for govkit

govkit's value scales with the gap between what an agent produces *by default* and what a disciplined practitioner produces. For CV that gap is unusually wide: the agent's training data is saturated with single-file, leakage-prone tutorial/Kaggle code, so an unconstrained agent confidently reproduces exactly those anti-patterns. Path-scoped rules constrain the agent **at generation time**, and CI gates convert tacit CV discipline ("never augment the eval path", "split by group key") into mechanical feedback an agentic loop can iterate against.

**Boundary of the claim (state it honestly):** govkit raises the floor on engineering discipline, reproducibility, and leakage prevention. It does **not** raise the floor on modeling judgment or production data quality. An agent can produce a clean, provenance-tracked pipeline that still picks the wrong augmentation policy or trains a model that doesn't converge. The pitch is "structurally sound, reproducible, leak-resistant CV code," not "a good ML researcher."

---

## 2. Canonical project layout (the contract's backbone)

Each directory is a seam CV developers routinely collapse. Every boundary below is a path-scoped rule + a cheap CI check.

```
data/                # versioned datasets — DVC/pointer + recorded hash; never committed blobs
configs/             # hyperparams + eval protocol as DATA (yaml), not literals in code
src/
  preprocessing/     # SINGLE source of truth for deterministic transforms (resize, normalize,
                     #   color-space). Imported by BOTH datasets/ AND inference/ — never duplicated.
  datasets/          # loading + split assembly; imports preprocessing/, may NOT import models/
  augment/           # stochastic augmentation ONLY — train split only; co-transforms labels
  models/            # architecture definitions ONLY — no optimizer, no data I/O, no fit/loop
  training/          # the loop / compile+fit; owns optimizer+schedule; imports models/, never defines
  evaluation/        # sole toucher of the TEST split; writes metrics+provenance artifact
  inference/         # loads a trained artifact; imports preprocessing/, never training/
labels/              # annotation source-of-truth + versioned class taxonomy (COCO/YOLO/VOC/masks)
notebooks/           # orchestration + visualization ONLY — import from src/, never define pipeline
```

Two structural corrections that distinguish this from a naive layout (both are common production failures):

- **`preprocessing/` is shared, not duplicated.** Train/serve preprocessing skew (resize/normalize/**RGB-vs-BGR**) is the #1 CV production bug. Normalization is *not* augmentation; it must live in shared `preprocessing/` imported by both `datasets/` and `inference/`. Augmentation is stochastic and train-only (TTA is the explicit carve-out).
- **`labels/` is first-class.** In CV the labels *are* the product. Annotation format, class taxonomy (as versioned data), and consistency checks get their own seam and rule.

---

## 3. L3 — the SoC spine (path-scoped rules)

Mirrors `rules/data/*` (one rule per seam, `paths_template` + `paths` frontmatter). Authored once, shipped identically to all three agents (§6).

| Rule file | Enforced boundary (CI-checkable) |
|---|---|
| `rules/cv/preprocessing.md` | Deterministic transforms only; the single import target for both `datasets/` and `inference/` |
| `rules/cv/datasets.md` | Loading + split assembly; no `import models`; **group/temporal/near-dup-aware splitting** |
| `rules/cv/augment.md` | Stochastic aug; train-split only (TTA carve-out); **must co-transform boxes/masks** |
| `rules/cv/models.md` | Architecture defs only — no optimizer, no `DataLoader`/`tf.data`, no `fit`/train loop |
| `rules/cv/training.md` | Owns loop / `compile`+`fit`; imports `models/`, never defines; sets seeds; writes checkpoint + metrics |
| `rules/cv/evaluation.md` | Sole toucher of the **test** split; pins eval protocol; emits metrics+provenance artifact |
| `rules/cv/inference.md` | Loads artifact; imports `preprocessing/`, never `training/`; preprocessing identical to train |
| `rules/cv/labels.md` | Annotation consistency (every image labeled, IDs in range, bboxes in-bounds, no degenerate boxes); taxonomy as versioned data |
| `rules/cv/reproducibility.md` | Seeds + recorded env (CUDA/cuDNN/TF) + dataset hash; **bounded** nondeterminism (not bit-exact); config-as-data |
| `rules/cv/notebooks.md` | `.ipynb` may not define an `nn`/Keras model or a train loop — visualization/exploration is fine |

Reused generic rules at L3: `rules/generic/repo-scope-backend.md`. Reused at L4: `test-first.md`, `spec-compliance.md`.

**Reuse from the `data` type:** vision datasets routinely contain faces = biometric PII, so `rules/data/pii.md` and `data-quality.md` concepts port directly. Decide at build time whether to reuse-by-reference or fork CV-specific copies.

### Governed architecture contracts (`docs/cv/architecture/`)

Mirrors `docs/data/architecture/`:

- `ARCH_CONTRACT.md` — top-level shape
- `BOUNDARIES.md` — the layer directionality rules (preprocessing shared; datasets→training→evaluation; inference isolated)
- `DATA_SPLIT_CONTRACT.md` — **group / temporal / near-duplicate** leakage prevention; val vs test distinction; test-set immutability
- `EVAL_CONTRACT.md` — per-class + sliced metrics, frozen eval protocol (IoU/NMS/score thresholds), noise band
- `REPRODUCIBILITY_CONTRACT.md` — seeds, recorded env + dataset version, bounded determinism, artifact/checkpoint provenance
- `LABEL_CONTRACT.md` — annotation schema, taxonomy versioning, consistency rules

---

## 4. L4 — the eval-regression + leakage gate (where CV shines)

L4 adds `test-first` + `spec-compliance` rules, the spec-planning skills, a starter feature, and the CV-specific CI gate. CI **cannot retrain** (training is slow/GPU-bound), so the gate works like the `data` type's: it gates on a **committed artifact**, not a training run.

### 4.1 The metrics+provenance artifact (the governed, agent-legible object)

> Captured here per the earlier framing decision — this is a govkit-extending-into-ML gap, not a harness-vs-OpenAI gap, so it lives in this plan rather than `HARNESS_GAP_ROADMAP.md`. Promote to the roadmap only if the `data` type needs the same object.

`evaluation/` emits a structured, versioned artifact (e.g. `evaluation/metrics.json` + schema in `governance/cv/schemas/`) recording:

- **Per-class and per-slice metrics** — not just aggregate. Aggregate mAP can rise while a safety-critical rare class or demographic slice collapses; the gate must read the breakdown. This is also where the biometric/fairness story becomes real.
- **Eval protocol** — IoU thresholds, NMS settings, score threshold, max detections. Metrics are uncomparable without it.
- **Dataset version/hash** — the exact data the metric was computed on. In CV the data churns constantly; a metric without a data version can't be compared across PRs.
- **Seed(s) + run variance** — mean±std across seeds so the gate can apply a **noise band** instead of failing on sub-noise deltas.

### 4.2 The CI gate (`ci/{github,azure}/cv-eval-gate.yml`)

1. Artifact exists and validates against the schema.
2. Per-class / per-slice metrics meet thresholds declared in `eval_criteria.yaml` and **don't regress** beyond the noise band.
3. **Leakage check** — train/test disjointness on **group keys + perceptual hashes**, not exact IDs (group/temporal/near-dup leakage; see §5).
4. Eval protocol + dataset version recorded.

Cheap pre-commit checks that *do* run in the agent's inner loop (high leverage because the heavy checks can't): folder-boundary import rules, "no model/loop defs in notebooks", config-as-data, label-bounds validation.

### 4.3 Starter feature (`features/starter_cv/`)

L3: `acceptance.feature`, `nfrs.md`, `plan.md`, `architecture_preflight.md`. L4 adds `eval_criteria.yaml` with **per-class** metric thresholds and a declared frozen test split — TF-targeted.

---

## 5. `python-tensorflow-vision` stack overlay

TF-first per decision. Mirrors `cli/stacks/python-dbt/` (6 docs + `overlay.yaml`).

- `TECH_STACK.md` — TF 2.x / Keras, `tf.data`, TF-Hub / KerasCV pretrained backbones, `torchmetrics`-equivalent (`keras.metrics` + COCO eval), TFRecord
- `MODEL_LAYERING.md` — functional vs `Model`-subclass conventions; **the Keras friction (see below)**
- `TRAINING_CONVENTIONS.md` — `compile`/`fit` vs custom `train_step`; callbacks; mixed precision
- `AUGMENTATION.md` — KerasCV / `tf.image` / Albumentations; label-co-transforming for detection/segmentation
- `EVALUATION.md` — per-class + sliced eval, COCO mAP/IoU, calibration (optional)
- `REPRODUCIBILITY.md` — `tf.config.experimental.enable_op_determinism()`, `TF_DETERMINISTIC_OPS`, seed + env recording; SavedModel vs H5 artifact convention; TFRecord schema seam
- `overlay.yaml` — `skill_context` (framework=tensorflow, eval libs, artifact format, source-folder hints), `default_assumptions`, `review_checklist`

**Keras idiom friction — resolve explicitly.** The generic "`models/` defines architecture only, no training loop" rule fights Keras, where training conventionally lives inside the model via `compile()`/`fit()`. Resolution: `models/` builds the architecture (functional or subclass); `training/` owns `compile`/`fit`/`train_step` orchestration. State this in `MODEL_LAYERING.md` or TF developers will reject the contract.

**Experiment tracking** (TensorBoard / W&B / MLflow) is the real system-of-record for runs, parallel to git. Reference a convention in the overlay; the metrics artifact (§4.1) is the *gated* projection of it.

Follow-on overlay: `python-pytorch-vision` (same contract, different idioms).

---

## 6. Agent parity + wiring

Per the parity invariant, every artifact ships identically across `claude-code`, `codex`, and `copilot`. A new type is ~3× the file count.

Per agent: manifest `type.cv` variant (L3 `files`/`governed`, `level_4` merge block), `claude-md`/`agents-md`/`copilot-instructions` (`cv.md` + `l4-cv.md`), `rules/cv/*` (→ `.claude/rules/`, codex `rules/`, copilot `instructions/cv/*.instructions.md`), reused `skills/backend/*`. Manifest `options.type.choices` gains `"cv"`; `ci.{github,azure}.by_type` gains `cv` entries (L3 quality gate; L4 `cv-eval-gate.yml`).

CLI/governance wiring: `overlay.yaml` discovered by `cli/overlay.py`; stack registered in `cli/stack_select.py` / `manifest.json options.stack`; `cli/detect.py` learns a TF-vision fingerprint; `cli/doctor.py` D006 picks up overlay versioning for free; `governance/cv/schemas/` for the metrics artifact schema. Test fixtures: `tests/fixtures/python-tf-vision/`.

---

## 7. Deferred: L5 and generative/multimodal

L5 today installs LLM-gateway / guardrails / llm-evaluation / multi-agent — **generative-shaped**, a mismatch for a ResNet/YOLO. Two honest L5 paths, both later:

- **Discriminative CV → new "Model Operations" L5**: drift monitoring, inference observability, human-in-the-loop review, rollback/versioning, robustness + fairness. Net-new authoring, not reuse.
- **Generative/multimodal vision** (VLMs, diffusion, image-gen) → the *existing* GenAI-Ops L5 becomes genuinely relevant (safety/guardrail/eval-as-judge surfaces). Reuse is real there.

Decision gate: confirm whether in-scope users are discriminative-only before any L5 work.

---

## 8. Staging (mirrors how data + python-dbt landed)

- **PR 1 — `cv` type spine (L3):** manifest `type.cv`, `rules/cv/*`, `cv.md`, `docs/cv/architecture/*` contracts, `features/starter_cv/` (L3). Parity ×3. Tests.
- **PR 2 — `python-tensorflow-vision` overlay:** 6 docs + `overlay.yaml`, `detect`/`doctor`/`stack_select` wiring, fixture.
- **PR 3 — L4 eval-regression + leakage gate:** metrics-artifact schema, `cv-eval-gate.yml` (GitHub + Azure), `eval_criteria.yaml` starter, L4 manifest block + parity.

Keep L4 lean initially (the `data` type shipped a deliberately thin L4) and grow it.

---

## 9. Open decisions

1. ~~**Type name**~~ — **DECIDED: `cv`** (locked 2026-06-05; matches short existing types).
2. **PII reuse** — reuse `data` type's `pii.md`/`data-quality.md` by reference, or fork CV-specific copies (faces = biometric is a stronger consent story than tabular PII).
3. **Metrics-artifact format** — bespoke `metrics.json` schema vs adopting an existing model-card / eval format.
4. **Discriminative-only confirmation** — gates the L5 question (§7).
5. **DVC vs alternative** for the dataset-versioning convention in `data/`.

---

## 10. Tracking

- [ ] PR 1: `cv` type spine (L3) — manifest, rules, contracts, starter, parity ×3, tests
- [ ] PR 2: `python-tensorflow-vision` overlay + CLI/doctor/detect wiring + fixture
- [ ] PR 3: L4 eval-regression + leakage gate + metrics-artifact schema + eval_criteria starter
- [ ] Resolve §9 open decisions (name, PII reuse, artifact format, discriminative scope, DVC)
- [ ] README: add `cv` to the type table + a short "governing CV" section
- [ ] Follow-on: `python-pytorch-vision` overlay

---

## Related

- Precedent pairing: `--type data` + `cli/stacks/python-dbt/`.
- Runtime legibility for ML (model/eval-artifact legibility): [HARNESS_GAP_ROADMAP.md](HARNESS_GAP_ROADMAP.md) Initiative 2.
- Heavyweight out-of-loop ML audits (perceptual-hash leakage, sliced-eval): [HARNESS_GAP_ROADMAP.md](HARNESS_GAP_ROADMAP.md) Initiative 1.
