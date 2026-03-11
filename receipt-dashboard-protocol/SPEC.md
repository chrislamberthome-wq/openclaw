# Receipt-Driven Dashboard Protocol
Status: Normative Core Frozen
Version: v1.0.0-draft1
Scope: Canonicalization, Object Model, Hash Semantics
Next Phase: Schema Derivation and Conformance Fixtures

---

## 1. Object Model

The protocol defines the following core object types:

1. **Event**
   - Represents a raw, immutable activity recorded on the event ledger.

2. **Metric Definition**
   - Identifies a versioned metric definition.

3. **Metric Receipt**
   - Verifies that a metric was computed deterministically from a bound event set and time window.

4. **Panel Definition**
   - Identifies a versioned dashboard panel definition.

5. **Panel Snapshot Receipt**
   - Verifies a rendered dashboard state at a specific point in time.

6. **Aggregation Policy**
   - Optional object identifying a policy used during aggregation.

7. **Render Contract**
   - Optional object identifying a rendering contract.

8. **Pipeline Bundle**
   - Replayable grouping of protocol objects required for deterministic verification.

### Object Type Identifier

Every protocol object MUST include a `type` field whose value identifies the object class.

Valid values are:

- `event`
- `metric_definition`
- `metric_receipt`
- `panel_definition`
- `panel_snapshot_receipt`
- `aggregation_policy`
- `render_contract`
- `pipeline_bundle`

Implementations MUST reject objects whose `type` field does not match the schema being validated.

---

## 2. Canonicalization Procedure

All protocol objects MUST be serialized and hashed according to the following canonicalization algorithm.

### Canonicalization Algorithm

1. **Field Removal**
   - Remove all fields whose names end with `_hash` from the object projection.

2. **String Normalization**
   - Normalize all string values to Unicode Normalization Form C (NFC).

3. **Timestamp Validation**
   - Validate all timestamp fields against the canonical UTC timestamp format:
     - `YYYY-MM-DDTHH:MM:SSZ`
   - Timezone offsets and fractional seconds are NOT permitted.

4. **Numeric Validation**
   - Numeric values MUST follow these rules:
     - Integers MUST be encoded as JSON numbers.
     - Non-integer numeric values MUST be encoded as decimal strings.
     - Floating-point numbers with fractional components MUST NOT be encoded as JSON numbers.

5. **Object Key Ordering**
   - Sort object keys lexicographically by their UTF-8 byte order.

6. **Array Ordering**
   - Preserve array order unless the protocol explicitly defines a sorting requirement for that array.

7. **Serialization**
   - Serialize as UTF-8 JSON with no insignificant whitespace.

8. **Hash Computation**
   - Compute SHA-256 over the resulting byte sequence.

### Timestamp Fields

The following fields are defined as timestamp fields and MUST conform to the canonical UTC timestamp format:

- `timestamp`
- `window_start`
- `window_end`
- `snapshot_time`

Implementations MUST reject:

- timezone offsets such as `+00:00` or `-05:00`
- fractional seconds
- non-UTC timestamps

---

## 3. Hash Projection Rules

### Invariant Hashing

Each protocol object MUST compute its own SHA-256 hash using the canonicalization procedure.

The canonical hash field names are:

- `event_hash`
- `metric_definition_hash`
- `metric_receipt_hash`
- `panel_definition_hash`
- `panel_snapshot_hash`
- `aggregation_policy_hash`
- `render_contract_hash`

### Hash Encoding

All hash values MUST be encoded as lowercase hexadecimal strings representing the 32-byte SHA-256 digest.

All protocol hash fields MUST therefore match:

- `^[a-f0-9]{64}$`

Implementations MUST treat any non-conforming hash encoding as `ERROR`.

### Hash Validation

Verifiers MUST treat any mismatch between a stored hash and a recomputed canonical hash as `FAIL`.

---

## 4. Window Semantics

### Range Definition

Time windows MUST be defined as half-open intervals:

- `[start, end)`

This means:

- Events with timestamps exactly equal to `start` are included.
- Events with timestamps exactly equal to `end` are excluded and belong to the next window.

### Boundary Integrity

Verifiers MUST validate that all included events fall within the declared time window according to `[start, end)` semantics.

---

## 5. Dependency Resolution

### Referenced Object Validation

Referenced objects MUST:
- exist within the pipeline bundle when bundle replay is performed
- be validated independently
- have their canonical hashes recomputed and compared against the dependent object’s references

### Metric Receipt Event Ordering

Event hashes in metric receipts MUST be sorted lexicographically using their hexadecimal string representation.

Implementations MUST reject duplicate or unordered event hashes as `FAIL`.

---

## 6. Security Considerations

### Hash Binding

Protocol objects MUST bind hash values to their canonical projections.

Any mismatch between stored and recomputed hash values MUST result in `FAIL`.

### Replay Protection

Receipts reference specific versioned definitions to prevent semantic drift during recomputation.

Pipeline bundles MUST require fully resolved dependencies during replay.

---

## 7. Versioning and Compatibility

### Breaking Changes

Breaking changes MUST increment the major version.

Example:
- `1.0.0` → `2.0.0`

### Non-Breaking Changes

Minor version increments MUST NOT alter:
- canonicalization rules
- hash projection behavior
- any behavior that changes receipt validity

Patch version increments MUST NOT change canonical bytes or canonical hash outcomes.

---

## 8. Pipeline Bundle Determinism

### Dependency Completeness

A pipeline bundle MUST contain all objects referenced by dependent objects within the bundle.

### Object Ordering

Pipeline bundles MUST organize objects in dependency order:

1. Events
2. Metric Definitions
3. Metric Receipts
4. Panel Definitions
5. Panel Snapshot Receipts
6. Optional Policies

Within each category, objects MUST be sorted lexicographically by their canonical hash values.

---

## 9. PASS / FAIL / ERROR Classification

### PASS

An object or bundle is `PASS` if it is:
- schema-valid
- dependency-complete
- canonically valid
- hash-consistent under recomputation

### FAIL

An object or bundle is `FAIL` if it is:
- schema-valid
- readable
- dependency-present where required
- but protocol invariants are violated

Examples include:
- stored hash mismatch
- unordered event hashes
- duplicate event hashes
- window-boundary violations

### ERROR

An object or bundle is `ERROR` if it is:
- malformed
- non-canonicalizable
- schema-invalid
- missing required dependencies
- unreadable

---

## 10. Conformance Requirements

Implementations claiming conformance MUST:
1. validate objects against the appropriate schema
2. enforce the canonicalization procedure exactly
3. recompute and compare canonical hashes
4. apply PASS / FAIL / ERROR classification exactly as defined
5. reject undefined behavior rather than infer semantics

The reference verifier CLI surface for this protocol is:
- `rdp-verify <type> <file>`
- `rdp-replay <bundle>`

Expected process exit codes are:
- `0` for `PASS`
- `1` for `FAIL`
- `2` for `ERROR`.