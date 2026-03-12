"""
Replay receipt verifier — v1.0 (frozen).

Classifies a single ai_inference_receipt as PASS, FAIL, or ERROR.

Outcome definitions (see docs/SPEC.md §5 for the normative spec):

  PASS  — Schema valid; hash valid; ledger linkage valid; declared policy
           reproduces (if checked); all required artifacts bound (if checked).

  FAIL  — Schema valid; hash valid; ledger valid; but the recorded policy
           decision does not reproduce from the declared output and policy.

  ERROR — Receipt is malformed; hash mismatches; ledger chain breaks; a
           required artifact digest is missing or mismatched; or replay
           cannot be performed under the declared contract.

The verifier is fail-closed: any unhandled exception or ambiguity produces ERROR.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema

from verifier.hash_projection import compute_receipt_hash
from verifier.policy_eval import PolicyResult, evaluate_policy

# Load the receipt schema once at import time.
_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "ai_inference_receipt.schema.json"
with open(_SCHEMA_PATH) as _f:
    _RECEIPT_SCHEMA: dict[str, Any] = json.load(_f)

_VALIDATOR = jsonschema.Draft7Validator(_RECEIPT_SCHEMA)

# Sentinel for "no prior receipt in this ledger position".
GENESIS_SENTINEL: str | None = None


@dataclass
class VerificationResult:
    """Result of verifying a single AI inference receipt."""

    outcome: str  # "PASS", "FAIL", or "ERROR"
    entry_id: str
    receipt_hash: str
    message: str
    checks: dict[str, bool | None] = field(default_factory=dict)
    error_detail: str | None = None


def verify_receipt(
    receipt: Any,
    *,
    prior_receipt_hash: str | None = GENESIS_SENTINEL,
    model_registry: dict[tuple[str, str], str] | None = None,
) -> VerificationResult:
    """Verify a single AI inference receipt.

    Args:
        receipt: The receipt object (must be a dict; other types produce ERROR).
        prior_receipt_hash: The receipt_hash of the immediately preceding ledger
            entry, or None if this is the first entry. Pass the sentinel value
            (None) for the genesis entry.
        model_registry: Optional mapping of (model_id, model_version) -> expected
            model_sha256. If provided, the receipt's model_sha256 must match.
            Pass None to skip artifact binding checks.

    Returns:
        A VerificationResult with outcome PASS, FAIL, or ERROR.
    """
    # --- Fail-closed outer guard ---
    try:
        return _verify(receipt, prior_receipt_hash=prior_receipt_hash, model_registry=model_registry)
    except Exception as exc:  # noqa: BLE001
        entry_id = _safe_entry_id(receipt)
        receipt_hash = _safe_receipt_hash(receipt)
        return VerificationResult(
            outcome="ERROR",
            entry_id=entry_id,
            receipt_hash=receipt_hash,
            message="Unhandled exception during verification.",
            checks={
                "schema_valid": None,
                "hash_valid": None,
                "ledger_valid": None,
                "policy_valid": None,
                "artifact_bound": None,
            },
            error_detail=f"{type(exc).__name__}: {exc}",
        )


def _verify(
    receipt: Any,
    *,
    prior_receipt_hash: str | None,
    model_registry: dict[tuple[str, str], str] | None,
) -> VerificationResult:
    # --- Step 0: ensure receipt is a dict ---
    if not isinstance(receipt, dict):
        return VerificationResult(
            outcome="ERROR",
            entry_id="<unknown>",
            receipt_hash="<unknown>",
            message="Receipt is not a JSON object.",
            checks={
                "schema_valid": False,
                "hash_valid": None,
                "ledger_valid": None,
                "policy_valid": None,
                "artifact_bound": None,
            },
            error_detail="TYPE_ERROR",
        )

    entry_id = _safe_entry_id(receipt)
    receipt_hash_declared = _safe_receipt_hash(receipt)

    checks: dict[str, bool | None] = {
        "schema_valid": None,
        "hash_valid": None,
        "ledger_valid": None,
        "policy_valid": None,
        "artifact_bound": None,
    }

    # --- Step 1: schema validation ---
    errors = list(_VALIDATOR.iter_errors(receipt))
    if errors:
        checks["schema_valid"] = False
        detail = "; ".join(e.message for e in errors[:3])
        return VerificationResult(
            outcome="ERROR",
            entry_id=entry_id,
            receipt_hash=receipt_hash_declared,
            message="Schema validation failed.",
            checks=checks,
            error_detail=f"SCHEMA_INVALID: {detail}",
        )
    checks["schema_valid"] = True

    # --- Step 2: hash verification ---
    try:
        recomputed = compute_receipt_hash(receipt)
    except (ValueError, TypeError) as exc:
        checks["hash_valid"] = False
        return VerificationResult(
            outcome="ERROR",
            entry_id=entry_id,
            receipt_hash=receipt_hash_declared,
            message="Failed to recompute receipt hash.",
            checks=checks,
            error_detail=f"HASH_COMPUTE_ERROR: {exc}",
        )

    if recomputed != receipt["receipt_hash"]:
        checks["hash_valid"] = False
        return VerificationResult(
            outcome="ERROR",
            entry_id=entry_id,
            receipt_hash=receipt_hash_declared,
            message="Receipt hash mismatch.",
            checks=checks,
            error_detail=f"HASH_MISMATCH: declared={receipt['receipt_hash']!r} recomputed={recomputed!r}",
        )
    checks["hash_valid"] = True

    # --- Step 3: ledger continuity ---
    prev_hash_in_receipt = receipt.get("prev_receipt_hash")
    if prior_receipt_hash != prev_hash_in_receipt:
        checks["ledger_valid"] = False
        return VerificationResult(
            outcome="ERROR",
            entry_id=entry_id,
            receipt_hash=receipt_hash_declared,
            message="Ledger chain broken: prev_receipt_hash mismatch.",
            checks=checks,
            error_detail=(
                f"LEDGER_BREAK: expected={prior_receipt_hash!r} "
                f"declared={prev_hash_in_receipt!r}"
            ),
        )
    checks["ledger_valid"] = True

    # --- Step 4: artifact binding (optional) ---
    if model_registry is not None:
        key = (receipt["model_id"], receipt["model_version"])
        expected_sha = model_registry.get(key)
        if expected_sha is None:
            checks["artifact_bound"] = False
            return VerificationResult(
                outcome="ERROR",
                entry_id=entry_id,
                receipt_hash=receipt_hash_declared,
                message="Model artifact not found in registry.",
                checks=checks,
                error_detail=f"ARTIFACT_NOT_IN_REGISTRY: key={key!r}",
            )
        if expected_sha != receipt["model_sha256"]:
            checks["artifact_bound"] = False
            return VerificationResult(
                outcome="ERROR",
                entry_id=entry_id,
                receipt_hash=receipt_hash_declared,
                message="Model artifact digest mismatch.",
                checks=checks,
                error_detail=(
                    f"ARTIFACT_MISMATCH: expected={expected_sha!r} "
                    f"declared={receipt['model_sha256']!r}"
                ),
            )
        checks["artifact_bound"] = True

    # --- Step 5: policy reproduction ---
    policy_result = evaluate_policy(receipt)
    if policy_result == PolicyResult.UNSUPPORTED:
        checks["policy_valid"] = None
    elif policy_result == PolicyResult.MATCH:
        checks["policy_valid"] = True
    else:
        # Policy evaluation returned MISMATCH
        checks["policy_valid"] = False
        return VerificationResult(
            outcome="FAIL",
            entry_id=entry_id,
            receipt_hash=receipt_hash_declared,
            message="Policy decision does not reproduce from declared output.",
            checks=checks,
            error_detail="POLICY_MISMATCH",
        )

    # --- All checks passed ---
    return VerificationResult(
        outcome="PASS",
        entry_id=entry_id,
        receipt_hash=receipt_hash_declared,
        message="All checks passed.",
        checks=checks,
    )


def _safe_entry_id(receipt: Any) -> str:
    if isinstance(receipt, dict):
        v = receipt.get("entry_id", "<unknown>")
        return str(v) if v is not None else "<unknown>"
    return "<unknown>"


def _safe_receipt_hash(receipt: Any) -> str:
    if isinstance(receipt, dict):
        v = receipt.get("receipt_hash", "<unknown>")
        return str(v) if v is not None else "<unknown>"
    return "<unknown>"
