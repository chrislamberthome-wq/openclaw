# REPEAT Global Hash Projection

**Status:** Normative  
**Version:** 1.0.0  
**Scope:** Field-level classification and artifact-specific guidance for producing
deterministic hash inputs

---

## Purpose

A hash projection is the canonical byte sequence that a verifier hashes to produce or
validate a stored digest. This document defines:

1. Which fields are **primary** (included in the projection).
2. Which fields are **derived** (excluded from the projection).
3. How the projection is computed from an artifact.
4. The invariant that ties semantic identity to byte-level identity.

This specification extends [CANONICALIZATION.md](./CANONICALIZATION.md), which governs the
byte-level serialization rules applied after the projection is produced.

---

## Core Invariant

> **Semantic identity maps directly to byte-level identity.**
>
> Two artifacts are semantically identical if and only if their canonical projections produce
> the same bytes and therefore the same SHA-256 digest.

No implementation detail, runtime environment, language choice, or library version may
produce a different projection for the same semantic content.

---

## Field Classification

### Primary Fields

Primary fields carry the semantic content of an artifact. They are included in the hash
projection unchanged (subject to canonicalization rules).

A field is **primary** if it is not listed in the derived-fields table below.

### Derived Fields

Derived fields are produced computationally from the primary content. Including them in
their own projection would create circularity or non-determinism.

| Field name          | Type              | Reason for exclusion                                             |
|---------------------|-------------------|------------------------------------------------------------------|
| `receipt_hash`      | `string` (hex)    | SHA-256 of the projection itself — self-referential              |
| `entry_hash`        | `string` (hex)    | SHA-256 of the ledger entry projection — self-referential        |
| `signature`         | `string` (hex)    | Signed over the hash, not part of the preimage                   |
| `signatures[*].sig` | `string` (hex)    | Individual signature bytes — derived from the hash; only `sig` within each signatures entry is excluded; `signer_id` and `alg` remain in the projection |
| `verifier_result`   | `string` (enum)   | Produced by the verifier after the fact                          |
| `verification_time` | `string` (timestamp) | Stamped by the verifier; not part of the artifact content     |

**Rule:** When any derived field is absent from an artifact, its absence does not affect the
projection. The exclusion operation is idempotent: remove if present, no-op if absent.

---

## Projection Algorithm

```
hash_projection(artifact):
  1. Copy artifact.
  2. Delete the following keys if present (top-level):
       receipt_hash
       entry_hash
       signature
       signatures
       verifier_result
       verification_time
  3. Apply canonicalization rules (CANONICALIZATION.md):
       a. Normalize all string values to NFC.
       b. Validate all timestamp fields against YYYY-MM-DDTHH:MM:SSZ.
       c. Sort all object keys lexicographically by UTF-8 byte order, recursively.
       d. Serialize as UTF-8 JSON with no insignificant whitespace.
  4. Compute SHA-256 over the resulting bytes.
  5. Encode the digest as a 64-character lowercase hex string.
```

### Formal Expression

```
projection   = remove_derived_fields(artifact)
canonical    = serialize_canonical_json(projection)   // see CANONICALIZATION.md
digest       = sha256(canonical)
hash_field   = hex_lower(digest)
```

---

## Artifact-Specific Guidance

### Receipt (`receipt.schema.json`)

```
receipt_hash = sha256_hex(canonical_json(receipt minus receipt_hash and signatures[*].sig))
```

The `signatures` array skeleton (with `signer_id` and `alg` but without `sig`) is **not**
excluded from the projection. Only `receipt_hash` itself and the individual `sig` strings
within each signatures entry are excluded.

| Included in projection | Excluded from projection           |
|------------------------|------------------------------------|
| `receipt_type`         | `receipt_hash`                     |
| `spec_version`         | `signatures[*].sig`                |
| `registry_id`          | `verifier_result` (if present)     |
| `event_id`             | `verification_time` (if present)   |
| `prev_receipt_hash`    |                                    |
| `payload_hash`         |                                    |
| `policy_version`       |                                    |
| `canonicalization_version` |                               |
| `actor`                |                                    |
| `event_time`           |                                    |
| `signatures[*].signer_id` |                                |
| `signatures[*].alg`    |                                    |

### Registry Entry

```
entry_hash = sha256_hex(canonical_json(entry minus entry_hash))
```

All other fields, including any `receipt_ref`, `payload_hash`, and `sequence_no`, are
included in the projection.

---

## Verification Procedure

A verifier MUST:

1. Receive the artifact as presented.
2. Extract the stored hash value from the appropriate derived field
   (e.g., `receipt_hash`, `entry_hash`).
3. Compute `hash_projection(artifact)` according to the algorithm above.
4. Compare the recomputed digest to the stored value using a constant-time equality
   function.
5. If the values match → continue to policy and signature checks.
6. If the values differ → record outcome `FAIL` (integrity violation).
7. If the artifact is malformed or the projection cannot be computed → record outcome
   `ERROR`.

See [VERIFICATION_OUTCOMES.md](./VERIFICATION_OUTCOMES.md) for the complete outcome
semantics.

---

## Non-Goals

This document does not define:

- Signature verification (covered by the receipt schema and governance policy contract).
- Policy enforcement rules (covered by the policy contract).
- Ledger replay mechanics (covered by the registry schema).
- The specific meaning of `PASS`, `FAIL`, or `ERROR` beyond the verification step above
  (covered by [VERIFICATION_OUTCOMES.md](./VERIFICATION_OUTCOMES.md)).

---

## Relationship to Other Specifications

- **[CANONICALIZATION.md](./CANONICALIZATION.md)** — Governs the byte-level serialization
  applied inside step 3 of the projection algorithm.
- **[VERIFICATION_OUTCOMES.md](./VERIFICATION_OUTCOMES.md)** — Defines the global semantics
  of the outcome codes produced by the verification procedure.
- **[../schemas/receipt.schema.json](../schemas/receipt.schema.json)** — The normative schema
  for the REPEAT Global receipt envelope; its `receipt_hash` field is the primary application
  of this specification.
