"""Tests for verifier.verify_receipt — v1.0.

Covers the full test matrix from docs/TEST_MATRIX.md.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from verifier.verify_receipt import VerificationResult, verify_receipt

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:  # type: ignore[type-arg]
    with open(FIXTURES / name) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# TM-01: PASS — valid receipt, valid chain, valid policy
# ---------------------------------------------------------------------------
class TestPassCase:
    def test_pass_outcome(self) -> None:
        receipt = _load("receipt_PASS.json")
        result = verify_receipt(receipt, prior_receipt_hash=None)
        assert result.outcome == "PASS"

    def test_pass_all_checks_true(self) -> None:
        receipt = _load("receipt_PASS.json")
        result = verify_receipt(receipt, prior_receipt_hash=None)
        assert result.checks["schema_valid"] is True
        assert result.checks["hash_valid"] is True
        assert result.checks["ledger_valid"] is True

    def test_pass_no_error_detail(self) -> None:
        receipt = _load("receipt_PASS.json")
        result = verify_receipt(receipt, prior_receipt_hash=None)
        assert result.error_detail is None

    def test_pass_entry_id_and_hash_populated(self) -> None:
        receipt = _load("receipt_PASS.json")
        result = verify_receipt(receipt, prior_receipt_hash=None)
        assert result.entry_id == receipt["entry_id"]
        assert result.receipt_hash == receipt["receipt_hash"]


# ---------------------------------------------------------------------------
# TM-02: FAIL — valid structure, policy decision does not reproduce
# ---------------------------------------------------------------------------
class TestFailCase:
    def test_fail_outcome(self) -> None:
        receipt = _load("receipt_FAIL.json")
        # receipt_FAIL has entry_id=002; pass its declared prev hash
        result = verify_receipt(
            receipt,
            prior_receipt_hash=receipt["prev_receipt_hash"],
        )
        assert result.outcome == "FAIL"

    def test_fail_schema_and_hash_valid(self) -> None:
        receipt = _load("receipt_FAIL.json")
        result = verify_receipt(
            receipt,
            prior_receipt_hash=receipt["prev_receipt_hash"],
        )
        assert result.checks["schema_valid"] is True
        assert result.checks["hash_valid"] is True
        assert result.checks["ledger_valid"] is True
        assert result.checks["policy_valid"] is False

    def test_fail_error_detail_policy_mismatch(self) -> None:
        receipt = _load("receipt_FAIL.json")
        result = verify_receipt(
            receipt,
            prior_receipt_hash=receipt["prev_receipt_hash"],
        )
        assert result.error_detail == "POLICY_MISMATCH"


# ---------------------------------------------------------------------------
# TM-03: ERROR — receipt hash mismatch
# ---------------------------------------------------------------------------
class TestErrorHashMismatch:
    def test_error_hash_mismatch(self) -> None:
        receipt = _load("receipt_ERROR.json")
        result = verify_receipt(receipt, prior_receipt_hash=None)
        assert result.outcome == "ERROR"
        assert result.checks["hash_valid"] is False

    def test_error_detail_contains_hash_mismatch(self) -> None:
        receipt = _load("receipt_ERROR.json")
        result = verify_receipt(receipt, prior_receipt_hash=None)
        assert result.error_detail is not None
        assert "HASH_MISMATCH" in result.error_detail


# ---------------------------------------------------------------------------
# TM-04: ERROR — missing required field
# ---------------------------------------------------------------------------
class TestErrorMissingField:
    def test_missing_model_sha256(self) -> None:
        receipt = copy.deepcopy(_load("receipt_PASS.json"))
        del receipt["model_sha256"]
        result = verify_receipt(receipt, prior_receipt_hash=None)
        assert result.outcome == "ERROR"
        assert result.checks["schema_valid"] is False

    def test_missing_input_hash(self) -> None:
        receipt = copy.deepcopy(_load("receipt_PASS.json"))
        del receipt["input_hash"]
        result = verify_receipt(receipt, prior_receipt_hash=None)
        assert result.outcome == "ERROR"

    def test_missing_receipt_type(self) -> None:
        receipt = copy.deepcopy(_load("receipt_PASS.json"))
        del receipt["receipt_type"]
        result = verify_receipt(receipt, prior_receipt_hash=None)
        assert result.outcome == "ERROR"


# ---------------------------------------------------------------------------
# TM-05: ERROR — prev_receipt_hash does not match prior ledger entry
# ---------------------------------------------------------------------------
class TestErrorLedgerBreak:
    def test_wrong_prior_hash(self) -> None:
        receipt = _load("receipt_PASS.json")
        result = verify_receipt(receipt, prior_receipt_hash="0" * 64)
        assert result.outcome == "ERROR"
        assert result.checks["ledger_valid"] is False

    def test_error_detail_contains_ledger_break(self) -> None:
        receipt = _load("receipt_PASS.json")
        result = verify_receipt(receipt, prior_receipt_hash="0" * 64)
        assert result.error_detail is not None
        assert "LEDGER_BREAK" in result.error_detail


# ---------------------------------------------------------------------------
# TM-06: ERROR — model digest differs from approved registry
# ---------------------------------------------------------------------------
class TestErrorArtifactMismatch:
    def test_wrong_model_sha256_in_registry(self) -> None:
        receipt = _load("receipt_PASS.json")
        registry = {("anomaly-detector", "v1.0.0"): "f" * 64}  # wrong hash
        result = verify_receipt(receipt, prior_receipt_hash=None, model_registry=registry)
        assert result.outcome == "ERROR"
        assert result.checks["artifact_bound"] is False

    def test_model_not_in_registry(self) -> None:
        receipt = _load("receipt_PASS.json")
        registry: dict[tuple[str, str], str] = {}  # empty registry
        result = verify_receipt(receipt, prior_receipt_hash=None, model_registry=registry)
        assert result.outcome == "ERROR"
        assert result.checks["artifact_bound"] is False

    def test_correct_registry_entry_passes(self) -> None:
        receipt = _load("receipt_PASS.json")
        registry = {("anomaly-detector", "v1.0.0"): receipt["model_sha256"]}
        result = verify_receipt(receipt, prior_receipt_hash=None, model_registry=registry)
        assert result.outcome == "PASS"
        assert result.checks["artifact_bound"] is True


# ---------------------------------------------------------------------------
# TM-07: PASS — hash projection ignores receipt_hash and signature
# ---------------------------------------------------------------------------
class TestHashProjectionIgnoresDerivedFields:
    def test_arbitrary_signature_does_not_break_pass(self) -> None:
        receipt = _load("receipt_PASS.json")
        receipt["signature"] = "arbitrary-value-xyz"
        result = verify_receipt(receipt, prior_receipt_hash=None)
        assert result.outcome == "PASS"

    def test_absent_signature_still_passes(self) -> None:
        receipt = _load("receipt_PASS.json")
        receipt.pop("signature", None)
        result = verify_receipt(receipt, prior_receipt_hash=None)
        assert result.outcome == "PASS"


# ---------------------------------------------------------------------------
# TM-08: PASS — observational timestamp change does not affect receipt_hash
# ---------------------------------------------------------------------------
class TestObservedAtDoesNotAffectHash:
    def test_different_observed_at_still_passes(self) -> None:
        receipt = _load("receipt_PASS.json")
        receipt["observed_at"] = "2099-12-31T23:59:59Z"
        result = verify_receipt(receipt, prior_receipt_hash=None)
        assert result.outcome == "PASS"

    def test_absent_observed_at_still_passes(self) -> None:
        receipt = _load("receipt_PASS.json")
        receipt.pop("observed_at", None)
        result = verify_receipt(receipt, prior_receipt_hash=None)
        assert result.outcome == "PASS"


# ---------------------------------------------------------------------------
# TM-10: ERROR — non-dict input (fail-closed)
# ---------------------------------------------------------------------------
class TestErrorNonDictInput:
    def test_string_input_is_error(self) -> None:
        result = verify_receipt("not a receipt", prior_receipt_hash=None)  # type: ignore[arg-type]
        assert result.outcome == "ERROR"

    def test_none_input_is_error(self) -> None:
        result = verify_receipt(None, prior_receipt_hash=None)  # type: ignore[arg-type]
        assert result.outcome == "ERROR"

    def test_list_input_is_error(self) -> None:
        result = verify_receipt([], prior_receipt_hash=None)  # type: ignore[arg-type]
        assert result.outcome == "ERROR"


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------
class TestEdgeCases:
    def test_wrong_receipt_type_is_error(self) -> None:
        receipt = copy.deepcopy(_load("receipt_PASS.json"))
        receipt["receipt_type"] = "wrong_type"
        result = verify_receipt(receipt, prior_receipt_hash=None)
        assert result.outcome == "ERROR"

    def test_extra_unknown_field_is_error(self) -> None:
        # Schema uses additionalProperties: false
        receipt = copy.deepcopy(_load("receipt_PASS.json"))
        receipt["unexpected_field"] = "value"
        result = verify_receipt(receipt, prior_receipt_hash=None)
        assert result.outcome == "ERROR"

    def test_verification_result_is_dataclass(self) -> None:
        receipt = _load("receipt_PASS.json")
        result = verify_receipt(receipt, prior_receipt_hash=None)
        assert isinstance(result, VerificationResult)
        assert hasattr(result, "outcome")
        assert hasattr(result, "entry_id")
        assert hasattr(result, "receipt_hash")
        assert hasattr(result, "checks")
