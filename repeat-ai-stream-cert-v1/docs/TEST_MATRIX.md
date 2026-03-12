# Test Matrix — v1.0

**Version:** 1.0.0  
**Status:** Frozen

---

## Purpose

This document defines the normative test matrix for `repeat-ai-stream-cert-v1`. Every verifier implementation **must** produce the specified outcome for each case.

---

## Matrix

### TM-01 — PASS: valid receipt, valid chain, valid policy

| Field | Value |
|---|---|
| Schema valid | Yes |
| Hash recomputed | Matches |
| Ledger chain | Valid (`prev_receipt_hash = null` for first entry) |
| Policy decision | Reproducible |
| Artifacts | Bound |
| **Expected outcome** | **PASS** |

Fixture: `tests/fixtures/receipt_PASS.json`

---

### TM-02 — FAIL: valid structure, policy decision does not reproduce

| Field | Value |
|---|---|
| Schema valid | Yes |
| Hash recomputed | Matches |
| Ledger chain | Valid |
| Policy decision | Declared `classification` differs from what policy reproduces given `output` and threshold |
| **Expected outcome** | **FAIL** |

Fixture: `tests/fixtures/receipt_FAIL.json`

Example: receipt records `classification = "ALERT"` with `threshold = 0.90` and `anomaly_score = 0.95`, but verifier policy reproduces `PASS` (e.g. if policy_version is not recognized and policy_eval returns a differing result).

---

### TM-03 — ERROR: receipt hash mismatch

| Field | Value |
|---|---|
| Schema valid | Yes |
| Hash recomputed | Does **not** match `receipt_hash` |
| **Expected outcome** | **ERROR** |

Fixture: `tests/fixtures/receipt_ERROR.json` (receipt_hash field is tampered)

---

### TM-04 — ERROR: missing required field

| Field | Value |
|---|---|
| Schema valid | No (required field absent) |
| **Expected outcome** | **ERROR** |

Test: construct a receipt missing `model_sha256` (or any other required field) and verify the outcome is `ERROR`.

---

### TM-05 — ERROR: prev_receipt_hash does not match prior ledger entry

| Field | Value |
|---|---|
| Schema valid | Yes |
| Hash recomputed | Matches |
| Ledger chain | `prev_receipt_hash` in receipt does not match `receipt_hash` of prior entry |
| **Expected outcome** | **ERROR** |

Fixture: `tests/fixtures/ledger_TAMPERED.jsonl`

---

### TM-06 — ERROR: model digest differs from approved registry

| Field | Value |
|---|---|
| Schema valid | Yes |
| Hash recomputed | Matches |
| Artifact check | `model_sha256` not in provided registry |
| **Expected outcome** | **ERROR** |

Test: call `verify_receipt` with a `model_registry` that does not contain the receipt's `(model_id, model_version, model_sha256)`.

---

### TM-07 — PASS: hash projection ignores receipt_hash and signature

| Test | Expected |
|---|---|
| Receipt with arbitrary `signature` value, correct `receipt_hash` | PASS |
| Receipt with `signature` absent, correct `receipt_hash` | PASS |
| Receipt with modified `receipt_hash` itself omitted from projection | hash still computes correctly |

Verifies: `receipt_hash` and `signature` are excluded from the projection used to compute `receipt_hash`.

---

### TM-08 — PASS: observational timestamp change does not affect receipt_hash

| Test | Expected |
|---|---|
| Receipt with `observed_at = "2026-01-01T00:00:00Z"`, correct `receipt_hash` | PASS |
| Same receipt with `observed_at = "2099-12-31T23:59:59Z"`, same `receipt_hash` | PASS |

Verifies: `observed_at` is excluded from the hash projection.

---

### TM-09 — ERROR: ledger chain break in multi-entry ledger

Fixture: `tests/fixtures/ledger_PASS.jsonl` and `ledger_TAMPERED.jsonl`

| Fixture | Expected |
|---|---|
| `ledger_PASS.jsonl` | All entries PASS |
| `ledger_TAMPERED.jsonl` | Entry with broken chain link produces ERROR |

---

### TM-10 — ERROR: malformed JSON (non-parseable receipt)

| Test | Expected |
|---|---|
| Pass a non-dict object to verifier | ERROR |
| Pass a string to verifier | ERROR |

Verifies: fail-closed behavior on non-JSON inputs.

---

## Implementation notes

- All test cases must be exercised by automated tests in `tests/`.
- The verifier must never raise an unhandled exception for any input; all exceptional paths must produce `ERROR`.
- New test cases may be added in patch releases without a version bump, provided they do not change the classification logic.
