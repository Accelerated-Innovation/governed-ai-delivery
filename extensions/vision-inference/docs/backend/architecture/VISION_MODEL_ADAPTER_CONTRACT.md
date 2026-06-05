# Vision Model Adapter Contract

**Applies to:** projects that **consume** a pretrained or hosted vision model
(classification, detection, segmentation, OCR) rather than train one. Layers on
top of the core `--type api` / `--type cli` ports-and-adapters governance — the
consumed model is just an **outbound dependency behind a port**.

> This contract governs *consumption*. Training-time concerns (datasets,
> augmentation, the training loop, leakage, reproducibility) are out of scope —
> they belong to the `cv` project type, not this extension.

---

## 1. The model is an outbound port, not a leaked dependency

- The consumed model — hosted (AWS Rekognition, GCP/Azure Vision) or self-hosted
  (Triton, TorchServe, a local checkpoint) — sits behind a single **outbound
  port** (interface) defined in the domain/services layer.
- The vendor SDK / HTTP client / framework runtime is **confined to one adapter**
  that implements the port. No `boto3`, `google.cloud.vision`, `tritonclient`,
  `torch`, or `tensorflow` import may appear in services, domain, or API layers.
- The port speaks the **domain's** vocabulary (e.g. `detect(image) -> [Detection]`),
  never the provider's response shape. Mapping provider payloads → domain types is
  the adapter's job.

**Why:** providers change, get deprecated, or get swapped for cost/latency/accuracy.
A leaked SDK type turns a provider swap into a refactor of the whole codebase.

## 2. Providers are swappable by construction

- Adding or replacing a provider means writing a new adapter against the existing
  port — **no change to services, domain, or API**.
- Provider selection is configuration, not code (`configs/`), and is injected at
  the composition root. No hard-coded provider branch inside business logic.
- A test double implementing the same port MUST be usable in unit tests without
  any network or GPU.

## 3. Deterministic preprocessing at the boundary

- Image preprocessing the provider requires (resize, normalization, **color space
  — RGB vs BGR**, channel order, encoding) is **deterministic** and lives in the
  adapter (or a shared preprocessing module the adapter imports).
- The exact preprocessing applied is recorded with the prediction (see the
  prediction logging contract) so a result can be reproduced.

## 4. Resilience is the adapter's responsibility

- Every outbound call has an explicit **timeout**; failures surface as a domain
  error type, never a raw provider exception.
- Retries (with backoff) and any fallback/degraded path are defined in the adapter
  and are **observable** — a fallback that silently returns lower-quality results
  is forbidden.
- Rate limits and cost ceilings are handled at the adapter boundary, not scattered
  through callers.

## 5. What requires an ADR

- Importing a provider SDK anywhere outside its adapter.
- Letting a provider response type cross the port into services/domain.
- A provider-specific branch inside business logic.
- A silent fallback between providers or models that changes prediction quality
  without surfacing it.

## 6. Anti-patterns

- A service that calls `rekognition.detect_labels(...)` directly.
- A domain object shaped like a provider's JSON response.
- Preprocessing duplicated (and drifting) between the adapter and a notebook.
- An adapter that swallows a timeout and returns an empty detection list as if the
  image contained nothing.
