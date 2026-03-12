# Canonicalization Rules — v1.0

**Version:** 1.0.0  
**Status:** Frozen

---

## Purpose

Canonicalization defines a deterministic mapping from a JSON object to a byte sequence.  
It is required so that `SHA-256(canonical_bytes(projection))` produces the same value regardless of the environment in which the receipt was created.

---

## Rules (normative)

### C1 — Encoding

The output is UTF-8 encoded bytes with no BOM.

### C2 — No insignificant whitespace

There are no spaces or newlines between tokens.  
The separator between key-value pairs is `,` (no space).  
The separator between a key and its value is `:` (no space).

### C3 — Key ordering

Object keys are sorted in **lexicographic ascending order** by their Unicode code points.  
Sorting is applied recursively to all nested objects.

### C4 — String encoding

Strings are enclosed in double quotes (`"`).  
Only the following characters are escaped:
- `"` → `\"`
- `\` → `\\`
- control characters U+0000–U+001F → `\uXXXX` (four lowercase hex digits)

No other characters are escaped. In particular, non-ASCII Unicode characters are emitted as their UTF-8 byte sequences, **not** as `\uXXXX` escapes.

### C5 — Number formatting

Numbers are serialized using Python's `repr`-compatible shortest-round-trip decimal form.

- Integers that can be represented exactly as Python `int` are serialized without a decimal point (e.g. `1`, `42`, `-7`).
- Floats are serialized with enough decimal digits to round-trip through IEEE 754 double precision (e.g. `0.95`, `1.18`, `0.9`).
- `NaN`, `Infinity`, and `-Infinity` are **forbidden** in the hash projection. Their presence is classified as `ERROR`.
- Exponent notation is used only when necessary for round-trip fidelity (e.g. `1e-300`); prefer decimal form otherwise.

### C6 — Boolean values

`true` and `false` are serialized as the JSON literals `true` and `false`.

### C7 — Null values

`null` is serialized as the JSON literal `null`.

### C8 — Arrays

Array elements are serialized in original order (arrays are **not** sorted).  
Elements are separated by `,` with no space.

### C9 — Nested objects

Nested objects follow all of the above rules recursively.  
Key sort order applies at every level.

### C10 — No trailing newline

The byte sequence does not end with a newline character.

---

## Reference implementation

See `verifier/canonicalize.py`.

```python
from verifier.canonicalize import canonical_json_bytes

obj = {"b": 2, "a": 1}
assert canonical_json_bytes(obj) == b'{"a":1,"b":2}'
```

---

## Test vectors

| Input (Python) | Expected bytes |
|---|---|
| `{}` | `{}` |
| `{"b": 2, "a": 1}` | `{"a":1,"b":2}` |
| `{"x": [3, 1, 2]}` | `{"x":[3,1,2]}` |
| `{"k": {"z": 0, "a": 1}}` | `{"k":{"a":1,"z":0}}` |
| `{"v": true}` | `{"v":true}` |
| `{"v": null}` | `{"v":null}` |
| `{"s": "he\"llo"}` | `{"s":"he\"llo"}` |
| `{"n": 0.95}` | `{"n":0.95}` |
| `{"n": 1.0}` | `{"n":1.0}` |

---

## Ambiguity rules

The following are explicitly forbidden in canonical projections:

- Duplicate keys in a JSON object.
- `NaN` / `Infinity` numeric values.
- Non-UTF-8 byte sequences.

Any receipt whose projection contains these is classified as `ERROR` by the verifier.
