#!/usr/bin/env python3
"""emit_receipt.py — Example: build and emit an AI inference receipt.

This script demonstrates how to construct a valid ai_inference_receipt
using the verifier library's canonicalization and hash projection utilities.

Usage:
    python examples/emit_receipt.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running from the repo root without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent))

from verifier.canonicalize import canonical_json_bytes
from verifier.hash_projection import hash_projection


def build_receipt(
    entry_id: str,
    event_id: str,
    input_hash: str,
    model_sha256: str,
    anomaly_score: float,
    prev_receipt_hash: str | None = None,
    threshold: float = 0.90,
) -> dict:  # type: ignore[type-arg]
    """Construct a receipt dict and compute the correct receipt_hash."""
    classification = "ALERT" if anomaly_score >= threshold else "PASS"

    receipt = {
        "receipt_type": "ai_inference_receipt",
        "entry_id": entry_id,
        "event_id": event_id,
        "prev_receipt_hash": prev_receipt_hash,
        "input_hash": input_hash,
        "input_schema_version": "event-envelope/v1",
        "model_id": "anomaly-detector",
        "model_version": "v1.0.0",
        "model_sha256": model_sha256,
        "preprocess_version": "prep-v1.0.0",
        "policy_version": "policy-v1.0.0",
        "runtime": {
            "framework": "onnxruntime",
            "framework_version": "1.18.0",
        },
        "output": {
            "anomaly_score": anomaly_score,
        },
        "decision": {
            "classification": classification,
            "threshold": threshold,
            "reason": f"score {'>=' if anomaly_score >= threshold else '<'} threshold",
        },
        "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    # Compute receipt_hash from canonical projection.
    projection = hash_projection(receipt)
    receipt["receipt_hash"] = hashlib.sha256(canonical_json_bytes(projection)).hexdigest()

    return receipt


def main() -> None:
    # Simulate hashing a raw input event.
    raw_input = json.dumps(
        {"schema_version": "event-envelope/v1", "event_id": "evt-example-001",
         "source": "sensor-gateway", "payload": {"sensor_id": "s-42", "reading": 0.95}},
        sort_keys=True,
    ).encode()
    input_hash = hashlib.sha256(raw_input).hexdigest()

    # Simulate a model artifact hash.
    model_sha256 = hashlib.sha256(b"model-artifact-bytes").hexdigest()

    receipt = build_receipt(
        entry_id="001",
        event_id="evt-example-001",
        input_hash=input_hash,
        model_sha256=model_sha256,
        anomaly_score=0.95,
    )

    print("Emitted receipt:")
    print(json.dumps(receipt, indent=2))
    print(f"\nreceipt_hash: {receipt['receipt_hash']}")
    print(f"classification: {receipt['decision']['classification']}")


if __name__ == "__main__":
    main()
