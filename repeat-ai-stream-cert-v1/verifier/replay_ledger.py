"""
Replay ledger verifier — v1.0.

Verifies an ordered sequence of AI inference receipts as a hash-linked ledger.
Each entry is verified individually and the chain linkage is checked across entries.
"""

from __future__ import annotations

from typing import Any

from verifier.verify_receipt import VerificationResult, verify_receipt


def verify_ledger(
    entries: list[Any],
    *,
    model_registry: dict[tuple[str, str], str] | None = None,
) -> list[VerificationResult]:
    """Verify an ordered list of receipt dicts as a hash-linked ledger.

    Args:
        entries: Ordered list of receipt dicts (first entry is the genesis).
        model_registry: Optional artifact binding registry; see verify_receipt.

    Returns:
        A list of VerificationResult, one per entry, in order.
        Verification stops propagating the chain hash on the first ERROR/FAIL
        to avoid cascading false errors, but all entries are still verified
        using their declared prev_receipt_hash.
    """
    results: list[VerificationResult] = []
    prior_hash: str | None = None

    for entry in entries:
        result = verify_receipt(
            entry,
            prior_receipt_hash=prior_hash,
            model_registry=model_registry,
        )
        results.append(result)
        # Advance the chain pointer using the declared receipt_hash so that
        # subsequent entries' ledger checks are against the actual declared value,
        # not a recomputed one (which may differ on an already-errored entry).
        if isinstance(entry, dict):
            prior_hash = entry.get("receipt_hash")
        else:
            prior_hash = None

    return results
