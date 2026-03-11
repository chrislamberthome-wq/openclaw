"""Tests for verifier.replay_ledger — v1.0."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from verifier.replay_ledger import verify_ledger

FIXTURES = Path(__file__).parent / "fixtures"


def _load_jsonl(name: str) -> list[dict]:  # type: ignore[type-arg]
    entries = []
    with open(FIXTURES / name) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


class TestVerifyLedgerPass:
    def test_all_entries_pass(self) -> None:
        entries = _load_jsonl("ledger_PASS.jsonl")
        results = verify_ledger(entries)
        assert len(results) == 3
        for r in results:
            assert r.outcome == "PASS", f"entry {r.entry_id} expected PASS, got {r.outcome}: {r.error_detail}"

    def test_results_count_matches_entries(self) -> None:
        entries = _load_jsonl("ledger_PASS.jsonl")
        results = verify_ledger(entries)
        assert len(results) == len(entries)

    def test_first_entry_genesis(self) -> None:
        entries = _load_jsonl("ledger_PASS.jsonl")
        results = verify_ledger(entries)
        assert results[0].checks["ledger_valid"] is True


class TestVerifyLedgerTampered:
    def test_first_entry_passes(self) -> None:
        # Entry 001 is valid; only entry 002 is tampered.
        entries = _load_jsonl("ledger_TAMPERED.jsonl")
        results = verify_ledger(entries)
        assert results[0].outcome == "PASS"

    def test_second_entry_errors(self) -> None:
        # Entry 002 has a tampered prev_receipt_hash.
        entries = _load_jsonl("ledger_TAMPERED.jsonl")
        results = verify_ledger(entries)
        assert results[1].outcome == "ERROR"
        assert results[1].checks["ledger_valid"] is False

    def test_error_detail_ledger_break(self) -> None:
        entries = _load_jsonl("ledger_TAMPERED.jsonl")
        results = verify_ledger(entries)
        assert results[1].error_detail is not None
        assert "LEDGER_BREAK" in results[1].error_detail


class TestVerifyLedgerEdgeCases:
    def test_empty_ledger(self) -> None:
        results = verify_ledger([])
        assert results == []

    def test_single_entry_genesis(self) -> None:
        entries = _load_jsonl("ledger_PASS.jsonl")[:1]
        results = verify_ledger(entries)
        assert len(results) == 1
        assert results[0].outcome == "PASS"

    def test_non_dict_entry_is_error(self) -> None:
        results = verify_ledger(["not a receipt"])  # type: ignore[list-item]
        assert results[0].outcome == "ERROR"
