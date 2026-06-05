# Model Versioning Contract

**Applies to:** consumption of a pretrained or hosted vision model behind the
adapter defined in `VISION_MODEL_ADAPTER_CONTRACT.md`. Governs how the consumed
model's identity and version are pinned, recorded, and watched for drift.

> A hosted model can change *under you* with no code change on your side. An
> unpinned, unrecorded model version makes every prediction unreproducible and
> every regression invisible.

---

## 1. Pin the model + version

- The consumed model is selected by an explicit **`model_id` + `model_version`**
  from configuration (`configs/`), never an implicit "latest".
- Where a provider does not expose a stable version, pin the **narrowest
  identifier they offer** (endpoint/model revision, container image digest for a
  self-hosted server, checkpoint hash for a local artifact) and record it.
- A change to `model_id` or `model_version` is a reviewed change (PR + the
  acceptance gate in `INFERENCE_ACCEPTANCE_CONTRACT.md`), not a silent config edit.

## 2. Record the version with every prediction

- Every prediction emits a record conforming to
  `schemas/prediction-record.schema.json`, carrying `model_id` + `model_version`
  (and `model_provider` where applicable).
- This is what makes a result reproducible and lets you attribute a metric shift
  to a specific model version.

## 3. Detect drift

- For hosted models that can change server-side, the system MUST be able to detect
  that the model moved: monitor the provider's reported version where exposed, and
  watch the acceptance metrics (`INFERENCE_ACCEPTANCE_CONTRACT.md`) on a canary
  set for unexplained shifts.
- A detected drift raises an alert and is treated as a version change — re-run the
  acceptance gate before continuing to trust outputs.

## 4. Rollback is defined, not improvised

- The previous known-good `model_id` + `model_version` is recoverable, and the
  adapter can be pointed back to it via configuration.
- Rollback criteria (which acceptance regressions trigger it) are written down, not
  decided in the moment.

## 5. What requires an ADR

- Consuming a model by a mutable "latest"/"stable" alias instead of a pinned
  version.
- Shipping a `model_version` change without running the acceptance gate.
- Disabling drift monitoring for a hosted model that can change server-side.

## 6. Anti-patterns

- `model = "general-detector"` with no version recorded.
- A metric regression that can't be tied to a model version because none was
  logged.
- Discovering a provider silently upgraded the model only after downstream
  behavior broke.
