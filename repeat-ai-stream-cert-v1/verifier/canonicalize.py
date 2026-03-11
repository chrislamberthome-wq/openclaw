"""
Canonicalization rules — v1.0 (frozen).

Converts a JSON-compatible Python object into a canonical UTF-8 byte sequence
suitable for deterministic hashing.

Rules (see docs/CANONICALIZATION.md for the full normative specification):
  C1  — UTF-8 output, no BOM.
  C2  — No insignificant whitespace.
  C3  — Object keys sorted lexicographically (recursive).
  C4  — Strings: only " \\ and control chars escaped; non-ASCII emitted as UTF-8.
  C5  — Numbers: integer-valued floats keep ".0"; shortest round-trip decimal.
  C6  — Booleans: JSON literals true / false.
  C7  — Null: JSON literal null.
  C8  — Arrays: original order, no space.
  C9  — Nested objects: rules apply recursively.
  C10 — No trailing newline.
"""

from __future__ import annotations

import math
from typing import Any


def canonical_json_bytes(obj: Any) -> bytes:
    """Return the canonical UTF-8 byte representation of *obj*.

    Raises:
        TypeError: if *obj* contains a type not representable in JSON
            (e.g. bytes, sets, custom objects).
        ValueError: if *obj* contains NaN or Infinity numeric values,
            which are forbidden by the canonicalization spec.
    """
    return _serialize(obj).encode("utf-8")


def _serialize(obj: Any) -> str:
    if obj is None:
        return "null"
    if isinstance(obj, bool):
        # bool must be checked before int (bool is a subclass of int)
        return "true" if obj else "false"
    if isinstance(obj, int):
        return str(obj)
    if isinstance(obj, float):
        return _serialize_float(obj)
    if isinstance(obj, str):
        return _serialize_string(obj)
    if isinstance(obj, dict):
        return _serialize_object(obj)
    if isinstance(obj, (list, tuple)):
        return _serialize_array(obj)
    raise TypeError(f"Object of type {type(obj).__name__!r} is not JSON serializable")


def _serialize_float(value: float) -> str:
    if math.isnan(value) or math.isinf(value):
        raise ValueError(
            f"NaN and Infinity are forbidden in canonical hash projections, got: {value!r}"
        )
    # Use repr for shortest round-trip; strip trailing zeros but keep at least one
    # decimal digit so that 1.0 stays "1.0" (not "1").
    r = repr(value)
    return r


def _serialize_string(value: str) -> str:
    # Escape only: backslash, double-quote, and control characters U+0000–U+001F.
    result = ['"']
    for ch in value:
        if ch == "\\":
            result.append("\\\\")
        elif ch == '"':
            result.append('\\"')
        elif ord(ch) < 0x20:
            result.append(f"\\u{ord(ch):04x}")
        else:
            result.append(ch)
    result.append('"')
    return "".join(result)


def _serialize_object(obj: dict) -> str:  # type: ignore[type-arg]
    # C3: sort keys lexicographically by Unicode code point order.
    parts = []
    for key in sorted(obj.keys()):
        if not isinstance(key, str):
            raise TypeError(f"Object keys must be strings, got {type(key).__name__!r}")
        parts.append(_serialize_string(key) + ":" + _serialize(obj[key]))
    return "{" + ",".join(parts) + "}"


def _serialize_array(obj: list | tuple) -> str:  # type: ignore[type-arg]
    # C8: preserve original element order.
    return "[" + ",".join(_serialize(item) for item in obj) + "]"
