"""Receipt generation and validation.

The receipt is produced deterministically from the trace and replay results.
It is NOT read from receipt.json during verification; instead the verifier
generates a fresh receipt and compares it to the stored one.
"""

import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of the file at *path*."""
    content = path.read_text(encoding="utf-8")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def build_receipt(
    cycle_id: str,
    trace_sha256: str,
    replay_match: bool,
    governance_verdict: str,
) -> dict:
    """Build a receipt dict; status is PASS only when all checks succeed."""
    if governance_verdict == "DENY":
        status = "FAIL"
    elif not replay_match:
        status = "FAIL"
    else:
        status = "PASS"

    return {
        "cycle_id": cycle_id,
        "trace_sha256": trace_sha256,
        "replay_match": replay_match,
        "governance_verdict": governance_verdict,
        "status": status,
    }


def load_stored_receipt(path: Path) -> dict:
    """Load and return the stored receipt JSON."""
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)
