# REPEAT Global Canonicalization Rules

**Status:** Normative  
**Version:** 1.0.0  
**Scope:** Byte-level serialization and hash projection for all signed or hashed artifacts

---

## Purpose

Canonicalization defines the only legal byte representation for any artifact that is signed,
hashed, or submitted for verification within REPEAT Global. A single invariant governs the
entire specification:

> **Identical semantic content MUST produce identical bytes and therefore identical hashes.**

If this invariant does not hold, hashes drift across implementations, registry replay breaks,
and governance receipts become unverifiable.

---

## Core Rules

### 1. Character Encoding

All artifacts MUST be encoded as UTF-8.

- No BOM (byte-order mark) is permitted.
- No other encoding (UTF-16, Latin-1, etc.) is legal.
- String values MUST be normalized to Unicode Normalization Form C (NFC) before hashing.

### 2. JSON Object Key Ordering

JSON object keys MUST be sorted **lexicographically by their UTF-8 byte representation**
(ascending, binary order).

```
// Correct
{"actor":"service","event_id":"abc","registry_id":"x"}

// Incorrect — keys are not sorted
{"registry_id":"x","event_id":"abc","actor":"service"}
```

This rule applies recursively to all nested objects.

### 3. No Insignificant Whitespace

Serialized canonical JSON MUST contain no insignificant whitespace:

- No spaces or newlines between tokens.
- No trailing newlines.
- Structural characters (`{`, `}`, `[`, `]`, `:`, `,`) MUST be written with no surrounding
  whitespace.

### 4. Array Order Preservation

Arrays MUST preserve their declared order exactly. No implementation MAY sort, deduplicate,
or reorder array elements unless a protocol rule explicitly mandates an ordering for a
specific field (e.g., lexicographic ordering of event hashes in an aggregation receipt).

### 5. Number Domain Restriction

To ensure deterministic serialization across all JSON implementations:

- **Integers** MUST be encoded as JSON number literals (no quotes, no decimal point).
- **Non-integer numeric values** (decimals, ratios) MUST be encoded as quoted decimal strings
  (e.g., `"3.14"`).
- **Floating-point numbers with fractional components** MUST NOT be encoded as JSON number
  literals.
- Numbers MUST fall within the JSON-safe integer range: `-(2^53 - 1)` to `(2^53 - 1)`.
- `NaN`, `Infinity`, and `-Infinity` are not permitted.

### 6. Timestamp Format

All timestamp values MUST conform to **RFC 3339 UTC with the `Z` suffix**.

**Required format:** `YYYY-MM-DDTHH:MM:SSZ`

- Fractional seconds are NOT permitted.
- Timezone offsets (e.g., `+00:00`, `-05:00`) are NOT permitted; only `Z` is legal.
- Non-UTC timestamps are NOT permitted.

Examples:

```
// Correct
"2026-03-12T07:18:57Z"

// Incorrect — fractional seconds
"2026-03-12T07:18:57.481Z"

// Incorrect — offset instead of Z
"2026-03-12T07:18:57+00:00"
```

### 7. Binary Value Encoding

Binary values (hashes, signatures, key material) MUST be encoded as **lowercase hexadecimal
strings**.

- The regex `^[a-f0-9]+$` MUST match the encoded value.
- Uppercase hex, Base64, and other encodings are not permitted.

SHA-256 digests MUST therefore match: `^[a-f0-9]{64}$`

### 8. Derived Field Exclusion

Derived fields MUST be excluded from the hash projection of their own artifact. An artifact
MUST NOT include its own derived fields when computing the canonical bytes used to produce
its hash. See the [Normative Projection Rule](#normative-projection-rule) below.

### 9. Unknown Field Policy

Implementations MUST choose one of two behaviors for unknown fields:

- **Fail-closed (default):** Reject the artifact with `ERROR` if any field not defined by
  the schema is present.
- **Extension namespace:** Accept unknown fields only if they are nested under an explicitly
  declared extension namespace key (e.g., `"x_ext"`). Fields outside that namespace that are
  not recognized by the schema MUST be rejected.

Silently ignoring unknown fields at the top level is NOT permitted.

---

## Normative Projection Rule

```
hash_projection(artifact) = artifact with all derived fields removed
```

**Derived fields that MUST be excluded from every hash projection:**

| Field name         | Reason                                                        |
|--------------------|---------------------------------------------------------------|
| `receipt_hash`     | Self-referential — the hash of the artifact itself            |
| `signature`        | Computed after the hash; including it would be circular       |
| `signatures[*].sig`| Individual signature bytes within each signatures entry; `signer_id` and `alg` remain in the projection |
| `verifier_result`  | Produced by the verifier after the fact                       |
| `verification_time`| Stamped by the verifier; not part of the artifact content     |

Implementations MUST strip these fields (if present) before serializing for hash computation.
The stripped projection is the canonical input to the SHA-256 function.

### Formal Expression

```
canonical_bytes(artifact) =
  utf8_encode(
    json_serialize_no_whitespace(
      sort_keys_recursive(
        remove_derived_fields(artifact)
      )
    )
  )

receipt_hash = sha256_hex(canonical_bytes(receipt))
```

---

## Conformance Requirements

An implementation is conformant with this specification if and only if it:

1. Serializes all artifacts as UTF-8 with NFC-normalized strings.
2. Sorts all JSON object keys lexicographically by UTF-8 byte order, recursively.
3. Emits no insignificant whitespace.
4. Preserves array order exactly.
5. Encodes integers as JSON numbers and non-integers as quoted decimal strings.
6. Rejects timestamps that are not in `YYYY-MM-DDTHH:MM:SSZ` format.
7. Encodes all binary values as lowercase hex.
8. Excludes all derived fields from hash projections.
9. Rejects unknown fields fail-closed or routes them to an explicit extension namespace.

Failure to meet any rule renders the canonical bytes non-deterministic and the resulting hash
untrustworthy.

---

## Relationship to Other Specifications

- **[HASH_PROJECTION.md](./HASH_PROJECTION.md)** — Extends these rules with field-level
  classification (derived vs. primary) and artifact-type-specific guidance.
- **[VERIFICATION_OUTCOMES.md](./VERIFICATION_OUTCOMES.md)** — Defines what `PASS`, `FAIL`,
  and `ERROR` mean when a verifier applies these canonicalization rules.
- **[../schemas/receipt.schema.json](../schemas/receipt.schema.json)** — The normative schema
  for the REPEAT Global receipt envelope, which is governed by these canonicalization rules.
