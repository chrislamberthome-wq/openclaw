"""Tests for hash chain integrity in trace.jsonl."""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verifier.canonical import canonical_dumps

TRACE_PATH = Path(__file__).resolve().parent.parent / "trace" / "trace.jsonl"


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _load_events() -> list[dict]:
    events = []
    for line in TRACE_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def test_trace_has_five_events():
    events = _load_events()
    assert len(events) == 5


def test_stages_are_fixed_sequence():
    events = _load_events()
    assert [e["stage"] for e in events] == [
        "reflect",
        "plan",
        "learn",
        "regulate",
        "govern",
    ]


def test_genesis_prev_hash_is_zeros():
    events = _load_events()
    assert events[0]["prev_hash"] == "0" * 64


def test_hash_chain_is_unbroken():
    events = _load_events()
    expected_prev = "0" * 64
    for event in events:
        assert event["prev_hash"] == expected_prev, (
            f"Hash chain broken at seq={event['seq']}"
        )
        expected_prev = _sha256(canonical_dumps(event))


def test_seq_is_monotonic():
    events = _load_events()
    seqs = [e["seq"] for e in events]
    assert seqs == list(range(1, len(events) + 1))


def test_all_events_have_cycle_id():
    events = _load_events()
    cycle_ids = {e["cycle_id"] for e in events}
    assert len(cycle_ids) == 1, "All events must share one cycle_id"


def test_broken_hash_chain_detected():
    """Mutating an event breaks subsequent hash verification."""
    events = _load_events()
    # Break event 2 by changing its prev_hash
    events[1] = dict(events[1])
    events[1]["prev_hash"] = "a" * 64

    expected_prev = "0" * 64
    broken = False
    for event in events:
        if event["prev_hash"] != expected_prev:
            broken = True
            break
        expected_prev = _sha256(canonical_dumps(event))

    assert broken, "Mutation was not detected"
