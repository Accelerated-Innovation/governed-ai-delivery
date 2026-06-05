# Prediction Logging Contract

**Applies to:** observability of vision-consumption paths. Governs what is recorded
for each prediction so the system is debuggable, auditable, and cost-aware —
**without** logging raw biometric payloads.

> Builds on the core `OBSERVABILITY_PORT_CONTRACT` of the `api`/`cli` type. This
> contract adds the vision-consumption specifics: model provenance, confidence, and
> PII-safe handling of image inputs.

---

## 1. Emit a structured prediction record

- Each prediction emits a structured record conforming to
  `schemas/prediction-record.schema.json`.
- It captures, at minimum: `model_id` + `model_version` (provenance),
  `outputs` with `confidence`, the `decision` taken, `latency_ms`, and `cost`
  where metered.
- Logging is **structured** (queryable fields), not free-text — so questions like
  "p95 latency for model X last week" or "low-confidence rate per class" are
  answerable.

## 2. Reference the input — never the raw image

- The record references the input by **id or content hash** (`input_ref`), never the
  raw image bytes. Raw biometric/personal images must not enter logs, traces, or
  error reports (`BIOMETRIC_DATA_HANDLING_CONTRACT.md`).
- Where an image must be retained for debugging, it is stored in the governed data
  store under the declared retention/residency policy — not in the log stream.

## 3. Make provenance and decisions queryable

- `model_id` + `model_version` on every record enables attributing a behavior shift
  to a model version and supports drift detection
  (`MODEL_VERSIONING_CONTRACT.md`).
- The recorded `decision` + `confidence` makes the confidence-threshold policy
  (`INFERENCE_ACCEPTANCE_CONTRACT.md`) auditable after the fact.

## 4. Capture cost and latency

- Per-prediction `latency_ms` and, for metered providers, `cost` are recorded so
  the external-model dependency's operational footprint is visible and bounded.

## 5. What requires an ADR

- Logging raw image bytes (biometric or otherwise) into the log/trace stream.
- Emitting predictions with no model-version provenance.
- Free-text-only logging that can't answer per-class/per-model operational
  questions.

## 6. Anti-patterns

- A debug log line containing a base64 image.
- Prediction logs that record the output but not which model version produced it.
- Cost/latency of the hosted model invisible until the invoice arrives.
