"""
Hash projection rules — v1.0 (frozen).

Defines which fields of an ai_inference_receipt are included in the
receipt_hash computation and which are excluded.

See docs/HASH_PROJECTION.md for the full normative specification.
"""

from __future__ import annotations

import hashlib
from typing import Any

from verifier.canonicalize import canonical_json_bytes

# Fields excluded from the hash projection (frozen — do not modify for v1.0).
# receipt_hash: derived field; would create circular dependency.
# signature:    derived over receipt_hash; not part of the decision contract.
# observed_at:  observational wall-clock timestamp; not part of the formal decision.
EXCLUDED_FIELDS: frozenset[str] = frozenset({"receipt_hash", "signature", "observed_at"})


def hash_projection(receipt: dict[str, Any]) -> dict[str, Any]:
    """Return the subset of *receipt* fields included in the receipt_hash computation.

    All fields not in EXCLUDED_FIELDS are included verbatim.
    """
    return {k: v for k, v in receipt.items() if k not in EXCLUDED_FIELDS}


def compute_receipt_hash(receipt: dict[str, Any]) -> str:
    """Compute and return the SHA-256 hex digest that should equal receipt['receipt_hash'].

    Algorithm:
      1. Project the receipt using hash_projection().
      2. Serialize the projection with canonical_json_bytes().
      3. Return SHA-256(bytes).hexdigest().

    Raises:
        ValueError: if the projection contains NaN/Infinity values (from canonicalize).
        TypeError:  if the projection contains non-serializable types (from canonicalize).
    """
    projection = hash_projection(receipt)
    raw = canonical_json_bytes(projection)
    return hashlib.sha256(raw).hexdigest()
