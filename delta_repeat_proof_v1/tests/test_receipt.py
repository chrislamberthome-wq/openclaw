"""Tests for receipt generation and validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verifier.receipt import build_receipt, load_stored_receipt, sha256_file

RECEIPT_PATH = Path(__file__).resolve().parent.parent / "receipt" / "receipt.json"
TRACE_PATH = Path(__file__).resolve().parent.parent / "trace" / "trace.jsonl"


def test_stored_receipt_has_pass_status():
    receipt = load_stored_receipt(RECEIPT_PATH)
    assert receipt["status"] == "PASS"


def test_stored_receipt_governance_allow():
    receipt = load_stored_receipt(RECEIPT_PATH)
    assert receipt["governance_verdict"] == "ALLOW"


def test_stored_receipt_replay_match():
    receipt = load_stored_receipt(RECEIPT_PATH)
    assert receipt["replay_match"] is True


def test_stored_receipt_trace_sha256_matches_file():
    receipt = load_stored_receipt(RECEIPT_PATH)
    assert receipt["trace_sha256"] == sha256_file(TRACE_PATH)


def test_build_receipt_pass():
    r = build_receipt(
        cycle_id="cycle-0001",
        trace_sha256="a" * 64,
        replay_match=True,
        governance_verdict="ALLOW",
    )
    assert r["status"] == "PASS"


def test_build_receipt_fail_on_replay_mismatch():
    r = build_receipt(
        cycle_id="cycle-0001",
        trace_sha256="a" * 64,
        replay_match=False,
        governance_verdict="ALLOW",
    )
    assert r["status"] == "FAIL"


def test_build_receipt_fail_on_deny():
    r = build_receipt(
        cycle_id="cycle-0001",
        trace_sha256="a" * 64,
        replay_match=True,
        governance_verdict="DENY",
    )
    assert r["status"] == "FAIL"


def test_build_receipt_fields():
    r = build_receipt(
        cycle_id="cycle-0001",
        trace_sha256="b" * 64,
        replay_match=True,
        governance_verdict="ALLOW",
    )
    assert set(r.keys()) == {
        "cycle_id",
        "trace_sha256",
        "replay_match",
        "governance_verdict",
        "status",
    }
