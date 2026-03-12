# Hash Projection Rules — v1.0

**Version:** 1.0.0  
**Status:** Frozen

---

## Purpose

The hash projection defines exactly which fields of an `ai_inference_receipt` are included in the computation of `receipt_hash`, and which are excluded.

The projection must be **stable**, **deterministic**, and **narrower** than the full receipt so that:

1. Derived fields (the hash itself, signatures) do not create circular dependencies.
2. Observational metadata (wall-clock timestamps) that is not part of the formal decision contract does not affect the reproducibility hash.

---

## Included fields (normative)

The following fields are included in the hash projection **exactly as they appear in the receipt**:

| Field | Rationale |
|---|---|
| `receipt_type` | Discriminator binding |
| `entry_id` | Ledger position binding |
| `event_id` | Source event binding |
| `prev_receipt_hash` | Ledger chain binding |
| `input_hash` | Input binding |
| `input_schema_version` | Input format binding |
| `model_id` | Model identity binding |
| `model_version` | Model version binding |
| `model_sha256` | Artifact binding |
| `preprocess_version` | Preprocessing contract binding |
| `policy_version` | Policy contract binding |
| `runtime` | Execution environment binding |
| `output` | Model output (formal decision input) |
| `decision` | Policy decision (formal decision output) |

---

## Excluded fields (normative)

The following fields are **always excluded** from the hash projection:

| Field | Rationale |
|---|---|
| `receipt_hash` | Derived field; would create a circular dependency |
| `signature` | Derived field; computed over `receipt_hash`, not included in it |
| `observed_at` | Observational metadata; wall-clock timestamp is not part of the formal decision contract |

If future versions add additional observational or derived fields, those fields must be explicitly excluded by updating this document and bumping the major version.

---

## Projection algorithm

```python
EXCLUDED_FIELDS = frozenset({"receipt_hash", "signature", "observed_at"})

def hash_projection(receipt: dict) -> dict:
    return {k: v for k, v in receipt.items() if k not in EXCLUDED_FIELDS}
```

---

## Receipt hash computation

```
receipt_hash = SHA-256(canonical_json_bytes(hash_projection(receipt)))
```

Where `canonical_json_bytes` is defined in `docs/CANONICALIZATION.md`.

In Python:

```python
import hashlib
from verifier.canonicalize import canonical_json_bytes
from verifier.hash_projection import hash_projection

projection = hash_projection(receipt)
digest = hashlib.sha256(canonical_json_bytes(projection)).hexdigest()
assert digest == receipt["receipt_hash"]
```

---

## Reference implementation

See `verifier/hash_projection.py`.

---

## Stability guarantee

The set of included/excluded fields is frozen for v1.0. Any change to this set requires a new major version of the package.

The verifier will classify as `ERROR` any receipt where `receipt_hash` does not match the recomputed value using the v1.0 projection and canonicalization rules.
