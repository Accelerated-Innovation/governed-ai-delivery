# Vision Inference Extension

## Purpose

The `vision-inference` extension adds governed architecture contracts for
applications that **consume** pretrained or hosted vision models — classification,
detection, segmentation, OCR, and (in a later increment) generative / vision-language
models — rather than train them.

It layers on top of the core `--type api` / `--type cli` ports-and-adapters
governance. The consumed model is an **outbound dependency behind a port**; this
extension governs the concerns that consumption adds:

- the model behind a swappable adapter/port (this increment)
- external-model version pinning + drift detection
- biometric data handling (sending images — faces — to a third party)
- black-box acceptance evaluation on a held-out set
- PII-safe prediction logging

> **Scope boundary.** Training-time concerns (datasets, augmentation, the training
> loop, leakage, reproducibility) belong to the `cv` *project type*, not this
> extension. See `plans/CV_TYPE_PLAN.md` and `plans/VISION_INFERENCE_EXTENSION_PLAN.md`.

## How extensions live in a project

Extensions are **not installed by the govkit CLI**. They live in-place under the
root-level `extensions/` folder of a consuming project, as a sibling of `docs/`,
`governance/`, and `features/`. Govkit discovers them by scanning
`extensions/*/manifest.yaml` during `apply` (for visibility) and `validate` (for
compliance). All artifact paths in `manifest.yaml` are resolved relative to the
extension folder.

## Intended use

Use this extension when a system consumes a vision model it does not train — e.g.
a hosted vision API, a self-hosted inference server (Triton/TorchServe), or a
loaded pretrained checkpoint used only for prediction.

## Contract set

Architecture contracts live under
`extensions/vision-inference/docs/backend/architecture/`:

- `VISION_MODEL_ADAPTER_CONTRACT.md` — the model behind an outbound port; SDK
  confined to the adapter; providers swappable; deterministic preprocessing.
- `MODEL_VERSIONING_CONTRACT.md` — pin `model_id` + `model_version`; record it per
  prediction; drift detection; defined rollback.
- `INFERENCE_ACCEPTANCE_CONTRACT.md` — black-box acceptance eval on a frozen
  held-out set; per-class + per-slice metrics; re-gate on any behavior-moving
  change; confidence-threshold + human-in-the-loop policy.
- `BIOMETRIC_DATA_HANDLING_CONTRACT.md` — special-category handling for images of
  people; consent/residency/retention declared as policy; never log the raw
  payload.
- `PREDICTION_LOGGING_CONTRACT.md` — structured, PII-safe prediction records with
  model provenance, confidence, latency, and cost.

### Generative / VLM contract set (`vision_generative`)

For vision-language models (Claude vision, GPT-4V) and image generation:

- `MULTIMODAL_INPUT_CONTRACT.md` — image-as-untrusted-instruction-channel
  (prompt-injection-via-image), generated-output validation, and the biometric
  obligations that still apply. **Reuses** the L5 GenAI-Ops contracts via
  `relates_to.extends` (guardrails, eval-as-judge, LLM observability, gateway)
  rather than reinventing them — so this set is intended for L5-governed projects.

Schemas live under `extensions/vision-inference/schemas/`:

- `prediction-record.schema.json` — the per-prediction provenance record consumed
  by the acceptance gate and prediction logging.
