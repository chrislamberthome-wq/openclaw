# REPEAT Global Verification Outcomes

**Status:** Normative  
**Version:** 1.0.0  
**Scope:** Global semantics for all verification operations within REPEAT Global

---

## Purpose

Every verification operation in REPEAT Global MUST resolve to exactly one of three outcomes:

| Outcome | Summary |
|---------|---------|
| `PASS`  | Fully valid: structure, hash, signature, and policy all satisfied |
| `FAIL`  | Structurally valid and integrity-checkable, but policy not satisfied or a verifiable invariant is violated |
| `ERROR` | Unverifiable: malformed, ambiguous, missing dependencies, or replay-broken |

No other outcome states are permitted. Implementations MUST NOT invent partial outcomes,
degraded-pass states, soft-fail modes, or warning-only results. The prohibition on ambiguous
states is a determinism guarantee: governance and registry replay MUST produce the same
outcome when applied to the same artifact under the same policy version.

---

## Outcome Definitions

### PASS

An artifact is `PASS` if **all** of the following conditions are true:

1. **Structural validity** — The artifact conforms to its declared schema with no extra
   fields outside permitted extension namespaces.
2. **Canonicalization validity** — Every field value satisfies the canonicalization rules
   in [CANONICALIZATION.md](./CANONICALIZATION.md) (UTF-8 NFC strings, RFC 3339 UTC
   timestamps, lowercase hex binaries, etc.).
3. **Hash integrity** — The stored hash value (e.g., `receipt_hash`) matches the
   recomputed hash produced by the projection algorithm in
   [HASH_PROJECTION.md](./HASH_PROJECTION.md).
4. **Signature validity** — At least one signature in the `signatures` array verifies
   correctly against the hash projection using the declared algorithm.
5. **Policy satisfaction** — The artifact satisfies all constraints imposed by the
   policy version identified in `policy_version`.

**Rationale:** `PASS` is the only outcome that authorizes downstream use of an artifact.
Any weakening of the required conditions would allow unverified content to propagate through
the registry or governance system.

**Determinism guarantee:** Given the same artifact, the same policy version, and the same
signer public keys, any conformant verifier MUST produce `PASS`.

---

### FAIL

An artifact is `FAIL` if:

- The artifact is **structurally valid** (schema-conformant and parseable), AND
- The artifact is **integrity-checkable** (the projection algorithm can be applied), AND
- **At least one verifiable invariant is violated.** Examples:
  - The recomputed hash does not match the stored hash value (integrity violation).
  - A signature fails to verify against the hash projection.
  - Policy constraints are not satisfied (e.g., quorum threshold not met, signer not
    eligible, sequence number is non-monotonic, window-boundary rules violated).
  - Event hashes in an aggregation receipt are not sorted lexicographically.
  - `prev_receipt_hash` does not match the hash of the declared predecessor receipt.

**Rationale:** `FAIL` distinguishes between "the system cannot read this artifact" (`ERROR`)
and "the system can read this artifact but the content is wrong." `FAIL` implies that the
artifact was produced by a system that understands the protocol but violated a rule. This
distinction is important for auditing: a `FAIL` receipt is evidence of a protocol violation,
whereas an `ERROR` receipt is evidence of a system malfunction or attack.

**Determinism guarantee:** Given the same artifact and the same policy version, any
conformant verifier MUST produce `FAIL` for the same set of invariant violations. A `FAIL`
outcome MUST be reproducible by replaying the same artifact through any conformant verifier.

---

### ERROR

An artifact is `ERROR` if any of the following conditions apply:

- The artifact is malformed (not valid JSON, binary corruption, truncation).
- The artifact does not conform to its declared schema (missing required fields, wrong
  field types, unrecognized fields outside permitted extension namespaces).
- Canonicalization cannot be applied (e.g., a timestamp value that cannot be parsed,
  a numeric value outside the JSON-safe domain).
- Required dependencies are missing (e.g., a receipt references a payload hash that
  cannot be resolved during bundle replay).
- The hash projection algorithm cannot be applied (e.g., the `canonicalization_version`
  is not recognized by the verifier).
- The artifact is ambiguous and no deterministic interpretation is available.
- Replay is broken (the chain of `prev_receipt_hash` values cannot be traversed to a
  known genesis anchor).

**Rationale:** `ERROR` is the fail-closed outcome. When a verifier cannot determine
whether an artifact is valid or invalid, it MUST NOT produce `PASS` or `FAIL`. Producing
`PASS` on an unverifiable artifact would allow malformed or adversarial content to enter
the registry. Producing `FAIL` would mischaracterize a system-level failure as a protocol
violation. `ERROR` preserves the semantic distinction.

**Determinism guarantee:** A conformant verifier MUST produce `ERROR` for any artifact
it cannot fully parse, project, or check. The set of conditions that produce `ERROR` MUST
be defined exhaustively by the protocol; implementations MUST NOT use `ERROR` as a
catch-all for unexpected behavior.

---

## Outcome Precedence

When a verifier checks multiple conditions, the following precedence rules apply:

1. If the artifact cannot be parsed or projected → `ERROR` (no further checks).
2. If the artifact fails schema validation → `ERROR` (no further checks).
3. If hash integrity fails on a parseable, schema-valid artifact → `FAIL`.
4. If signature verification fails on a hash-valid artifact → `FAIL`.
5. If policy constraints are not satisfied on a signature-valid artifact → `FAIL`.
6. If all checks pass → `PASS`.

The precedence ensures that `ERROR` is always returned before `FAIL`, and `FAIL` is always
returned before `PASS`. This ordering is deterministic and cannot produce ambiguous states.

---

## Exit Codes

Verifier CLI implementations MUST use the following process exit codes:

| Outcome | Exit code |
|---------|-----------|
| `PASS`  | `0`       |
| `FAIL`  | `1`       |
| `ERROR` | `2`       |

This convention is compatible with the exit codes defined in the Receipt-Driven Dashboard
Protocol (SPEC.md) and ensures that shell-based replay pipelines can detect failures without
parsing output.

---

## Governance and Registry Replay Constraints

The outcome semantics defined here apply to all REPEAT Global artifact types without
exception, including:

- Standard receipts (`receipt.schema.json`)
- Registry entries
- Governance receipts (`seat_fill`, `policy_update`, `registry_anchor`, `revocation`,
  `council_attestation`)

**Governance replay MUST NOT invent additional outcome states.** Council-of-9 quorum checks,
seat-fill eligibility rules, and policy-update effective-date constraints are all enforced
as policy conditions that produce `FAIL` on violation — never a custom outcome.

---

## Relationship to Other Specifications

- **[CANONICALIZATION.md](./CANONICALIZATION.md)** — Defines the byte-level rules that must
  hold for an artifact to be canonicalization-valid (a prerequisite for `PASS`).
- **[HASH_PROJECTION.md](./HASH_PROJECTION.md)** — Defines the projection algorithm whose
  output is checked for hash integrity (a prerequisite for `PASS`).
- **[../schemas/receipt.schema.json](../schemas/receipt.schema.json)** — The normative
  receipt schema; structural validity against this schema is required to avoid `ERROR`.
