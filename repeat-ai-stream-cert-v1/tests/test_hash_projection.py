"""Tests for verifier.hash_projection — v1.0."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from verifier.canonicalize import canonical_json_bytes
from verifier.hash_projection import (
    EXCLUDED_FIELDS,
    compute_receipt_hash,
    hash_projection,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:  # type: ignore[type-arg]
    with open(FIXTURES / name) as f:
        return json.load(f)


class TestHashProjection:
    def test_excluded_fields_are_absent(self) -> None:
        receipt = _load("receipt_PASS.json")
        proj = hash_projection(receipt)
        for field in EXCLUDED_FIELDS:
            assert field not in proj, f"Excluded field {field!r} found in projection"

    def test_included_fields_are_present(self) -> None:
        receipt = _load("receipt_PASS.json")
        proj = hash_projection(receipt)
        required = [
            "receipt_type", "entry_id", "event_id", "input_hash",
            "model_id", "model_version", "model_sha256",
            "preprocess_version", "policy_version", "runtime",
            "output", "decision",
        ]
        for field in required:
            assert field in proj, f"Required field {field!r} missing from projection"

    def test_receipt_hash_excluded(self) -> None:
        receipt = _load("receipt_PASS.json")
        proj = hash_projection(receipt)
        assert "receipt_hash" not in proj

    def test_signature_excluded(self) -> None:
        receipt = _load("receipt_PASS.json")
        receipt["signature"] = "dummy-sig"
        proj = hash_projection(receipt)
        assert "signature" not in proj

    def test_observed_at_excluded(self) -> None:
        receipt = _load("receipt_PASS.json")
        proj = hash_projection(receipt)
        assert "observed_at" not in proj

    # TM-07: hash projection ignores receipt_hash and signature
    def test_signature_does_not_affect_hash(self) -> None:
        """Adding or changing signature must not change the computed hash."""
        receipt = _load("receipt_PASS.json")
        h1 = compute_receipt_hash(receipt)
        receipt["signature"] = "some-arbitrary-signature"
        h2 = compute_receipt_hash(receipt)
        assert h1 == h2

    # TM-08: observational timestamp change does not affect receipt_hash
    def test_observed_at_does_not_affect_hash(self) -> None:
        """Changing observed_at must not change the computed hash."""
        receipt = _load("receipt_PASS.json")
        h1 = compute_receipt_hash(receipt)
        receipt["observed_at"] = "2099-12-31T23:59:59Z"
        h2 = compute_receipt_hash(receipt)
        assert h1 == h2

    def test_compute_receipt_hash_matches_fixture(self) -> None:
        """Recomputed hash must equal the declared receipt_hash in the PASS fixture."""
        receipt = _load("receipt_PASS.json")
        computed = compute_receipt_hash(receipt)
        assert computed == receipt["receipt_hash"]

    def test_compute_receipt_hash_is_sha256_hex(self) -> None:
        receipt = _load("receipt_PASS.json")
        h = compute_receipt_hash(receipt)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_projection_is_deterministic(self) -> None:
        receipt = _load("receipt_PASS.json")
        h1 = compute_receipt_hash(receipt)
        h2 = compute_receipt_hash(receipt)
        assert h1 == h2

    def test_changing_output_changes_hash(self) -> None:
        receipt = _load("receipt_PASS.json")
        h1 = compute_receipt_hash(receipt)
        receipt["output"]["anomaly_score"] = 0.50
        # Must recompute receipt_hash after projection to get a different value
        from verifier.hash_projection import hash_projection as hp
        proj = hp(receipt)
        h2 = hashlib.sha256(canonical_json_bytes(proj)).hexdigest()
        assert h1 != h2

    def test_changing_model_sha256_changes_hash(self) -> None:
        receipt = _load("receipt_PASS.json")
        h1 = compute_receipt_hash(receipt)
        receipt["model_sha256"] = "f" * 64
        from verifier.hash_projection import hash_projection as hp
        proj = hp(receipt)
        h2 = hashlib.sha256(canonical_json_bytes(proj)).hexdigest()
        assert h1 != h2
