"""
Policy evaluation — v1.0.

Determines whether the recorded decision in an ai_inference_receipt is
reproducible from the declared output values, threshold, and policy_version.

The v1.0 policy is simple and intentionally narrow:

  - Supported policy versions: "policy-v1.0.0"
  - Decision logic: if output["anomaly_score"] >= decision["threshold"],
    classification must be "ALERT"; otherwise classification must be "PASS".
  - Any other policy_version returns PolicyResult.UNSUPPORTED (not an error).

Integrators may extend this module for their own policy_version strings, but
must not change the logic for "policy-v1.0.0" in v1.0 of this package.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class PolicyResult(Enum):
    MATCH = "MATCH"          # Declared decision reproduces from declared output
    MISMATCH = "MISMATCH"    # Declared decision does not reproduce
    UNSUPPORTED = "UNSUPPORTED"  # policy_version not recognized; skip check


def evaluate_policy(receipt: dict[str, Any]) -> PolicyResult:
    """Evaluate whether the receipt's decision reproduces under its declared policy.

    Returns:
        PolicyResult.MATCH       — decision is reproducible.
        PolicyResult.MISMATCH    — decision is not reproducible (produces FAIL).
        PolicyResult.UNSUPPORTED — policy_version is not known to this verifier.
    """
    policy_version = receipt.get("policy_version", "")

    if policy_version == "policy-v1.0.0":
        return _evaluate_v1(receipt)

    # Unknown policy version: skip policy check (not an error).
    return PolicyResult.UNSUPPORTED


def _evaluate_v1(receipt: dict[str, Any]) -> PolicyResult:
    """Evaluate the v1.0.0 anomaly-detection policy."""
    try:
        output = receipt["output"]
        decision = receipt["decision"]
        score: float = float(output["anomaly_score"])
        threshold: float = float(decision["threshold"])
        declared_class: str = decision["classification"]
    except (KeyError, TypeError, ValueError):
        # Missing or non-numeric fields are caught by schema validation upstream.
        # Treat as unsupported rather than raising here.
        return PolicyResult.UNSUPPORTED

    expected_class = "ALERT" if score >= threshold else "PASS"
    if declared_class == expected_class:
        return PolicyResult.MATCH
    return PolicyResult.MISMATCH
