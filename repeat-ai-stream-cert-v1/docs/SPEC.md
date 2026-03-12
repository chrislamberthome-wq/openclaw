# repeat-ai-stream-cert-v1 — Specification

**Version:** 1.0.0  
**Status:** Frozen

---

## 1. Purpose

`repeat-ai-stream-cert-v1` defines a deterministic, fail-closed streaming certificate for AI inference events.

It certifies that a recorded inference event is **reproducible** from:

- the declared input bindings (`input_hash`, `input_schema_version`)
- the declared artifact bindings (`model_sha256`, `model_id`, `model_version`)
- the declared transformation contracts (`preprocess_version`, `policy_version`)
- the declared execution context (`runtime`)
- the ledger chain (`prev_receipt_hash`)

It does **not** certify that the model's output was correct in any ground-truth sense.

---

## 2. Receipt structure

See `schemas/ai_inference_receipt.schema.json` for the normative field definitions.

The following fields are **required** in every v1 receipt:

| Field | Type | Role |
|---|---|---|
| `receipt_type` | `"ai_inference_receipt"` | Discriminator |
| `entry_id` | string | Ledger position |
| `event_id` | string | Source event binding |
| `input_hash` | SHA-256 hex | Input binding |
| `input_schema_version` | string | Input format binding |
| `model_id` | string | Model identity |
| `model_version` | string | Model version |
| `model_sha256` | SHA-256 hex | Artifact binding |
| `preprocess_version` | string | Preprocessing contract |
| `policy_version` | string | Decision policy contract |
| `runtime.framework` | string | Execution framework |
| `runtime.framework_version` | string | Framework version |
| `output` | object | Raw model output |
| `decision.classification` | string | Policy decision label |
| `decision.threshold` | number | Policy threshold |
| `decision.reason` | string | Decision rationale |
| `receipt_hash` | SHA-256 hex | Hash of canonical projection |

The following fields are **optional**:

| Field | Type | Role |
|---|---|---|
| `prev_receipt_hash` | SHA-256 hex or null | Ledger chain link |
| `observed_at` | ISO 8601 datetime | Observational timestamp |
| `signature` | string | Out-of-scope v1.0 |

---

## 3. Receipt hash computation

```
receipt_hash = SHA-256(canonical_json_bytes(hash_projection(receipt)))
```

See `docs/HASH_PROJECTION.md` for the full projection specification.  
See `docs/CANONICALIZATION.md` for the canonical JSON byte serialization rules.

---

## 4. Ledger continuity

Receipts form a singly-linked hash chain:

- The first receipt in a stream **must** have `prev_receipt_hash = null`.
- Every subsequent receipt **must** have `prev_receipt_hash` equal to the `receipt_hash` of the immediately preceding receipt in the stream.
- Gaps, reordering, or insertion are classified as `ERROR`.

---

## 5. Verification outcomes

| Outcome | Conditions |
|---------|-----------|
| `PASS` | Schema valid; hash valid; ledger chain valid; policy reproducible (if checked); artifact bound (if checked). |
| `FAIL` | Schema valid; hash valid; ledger valid; but policy decision does not reproduce. |
| `ERROR` | Schema invalid, hash mismatch, ledger chain break, missing required artifact digest, or replay impossible. |

The verifier is **fail-closed**: ambiguity resolves to `ERROR`, never to `PASS`.

---

## 6. Versioning and freezing

v1.0 contracts are frozen. The following are non-breaking:

- Adding optional fields to receipts (old verifiers skip unknown fields).
- Adding new test matrix cases.
- Documentation clarifications.

The following require a new major version:

- Any change to the `hash_projection` excluded/included field set.
- Any change to canonicalization rules.
- Any change to required fields in the schema.
- Any change to the `PASS/FAIL/ERROR` classification logic.

---

## 7. What this specification does not cover

- Model correctness or ground-truth accuracy.
- Cryptographic key management for `signature`.
- Distributed or branching ledger topologies.
- Input event replay (only the input hash is verified, not the input content).
