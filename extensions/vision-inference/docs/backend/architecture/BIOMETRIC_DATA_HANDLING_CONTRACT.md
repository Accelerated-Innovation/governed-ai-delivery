# Biometric Data Handling Contract

**Applies to:** any vision-consumption path where images may contain **biometric or
personal data** (faces, gait, license plates, identifiable persons) — especially
when those images leave the trust boundary to a third-party or hosted model.

> This is the genuinely vision-specific risk of *consuming* models. Sending an
> image to a hosted API is sending potentially special-category personal data to a
> third party. This contract sets the principles; the specific values
> (jurisdiction, retention window, residency region) are **team policy** declared in
> configuration, not invented here.

---

## 1. Treat biometric data as special category

- Images that may contain biometric/personal data are classified and handled as a
  **special category** from ingestion onward — not discovered late at the API
  boundary.
- The classification (does this path handle biometric data?) is explicit in the
  feature's `architecture_preflight.md`.

## 2. Declare, don't assume, the policy

The following are **declared in configuration** (and surfaced for review), not
hard-coded or left implicit:

- **Lawful basis / consent** — the basis for processing these images, and how
  consent (where required) is captured and revocable.
- **Residency region** — where images and predictions may be processed/stored.
- **Retention window** — how long images and prediction records are kept before
  deletion; defaults to the shortest viable.
- **Third-party transmission** — which providers may receive images, and what their
  data-use/retention terms are.

A vision-consumption path that transmits biometric data to a provider not covered
by a declared policy is blocked.

## 3. Minimize and redact

- Send the **minimum** necessary: prefer on-device/edge filtering, cropping to the
  region of interest, or redaction before transmission where the use-case allows.
- Never persist raw biometric images beyond the declared retention window; prefer a
  reference or hash over the raw bytes wherever the workflow permits.

## 4. Never log the raw payload

- Raw biometric images **must not** appear in logs, traces, error reports, or
  prediction records. The prediction record references the input by id/hash only
  (see `PREDICTION_LOGGING_CONTRACT.md` and `prediction-record.schema.json`).

## 5. Right to erasure

- Deletion of a subject's images and associated prediction records is supported and
  propagates to any retained derivatives, within the declared window.

## 6. What requires an ADR

- Transmitting biometric data to a provider/region not in the declared policy.
- Retaining raw biometric images beyond the declared retention window.
- Processing biometric data with no declared lawful basis/consent.

## 7. Anti-patterns

- Uploading full frames to a hosted API when only a cropped region is needed.
- A face image landing in an exception log or an APM trace.
- "We'll figure out retention later" — retention undeclared while data accumulates.
