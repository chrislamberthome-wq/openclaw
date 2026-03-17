"""Tests for governance validation."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TRACE_PATH = Path(__file__).resolve().parent.parent / "trace" / "trace.jsonl"


def _load_events() -> list[dict]:
    events = []
    for line in TRACE_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def _get_govern_event(events: list[dict]) -> dict:
    for e in events:
        if e["stage"] == "govern":
            return e
    raise AssertionError("No govern event found")


def test_governance_verdict_is_allow():
    events = _load_events()
    gov = _get_govern_event(events)
    assert gov["payload"]["verdict"] == "ALLOW"


def test_governance_has_decision_id():
    events = _load_events()
    gov = _get_govern_event(events)
    assert gov["payload"]["decision_id"] == "gov-0001"


def test_governance_constraints_applied_nonempty():
    events = _load_events()
    gov = _get_govern_event(events)
    assert len(gov["payload"]["constraints_applied"]) > 0


def test_governance_deny_halts(tmp_path):
    """A DENY verdict must result in exit code 1 when the verifier runs."""
    import subprocess  # noqa: PLC0415
    import shutil  # noqa: PLC0415

    root = Path(__file__).resolve().parent.parent
    staging = tmp_path / "proof"
    shutil.copytree(root, staging)

    # Mutate govern event to DENY
    trace_path = staging / "trace" / "trace.jsonl"
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        event = json.loads(line)
        if event["stage"] == "govern":
            event["payload"]["verdict"] = "DENY"
            # We also need to recanonicalise but the verifier will detect
            # non-canonical and return 2; either 1 or 2 is acceptable for DENY.
            new_lines.append(json.dumps(event, sort_keys=True, separators=(",", ":")))
        else:
            new_lines.append(line)
    trace_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    # Recompute hash chain so the verifier reaches the DENY check
    import hashlib  # noqa: PLC0415
    from verifier.canonical import canonical_dumps  # noqa: PLC0415

    new_events = [json.loads(l) for l in new_lines]
    prev_hash = "0" * 64
    rebuilt = []
    for event in new_events:
        event["prev_hash"] = prev_hash
        can = canonical_dumps(event)
        rebuilt.append(can)
        prev_hash = hashlib.sha256(can.encode("utf-8")).hexdigest()
    trace_path.write_text("\n".join(rebuilt) + "\n", encoding="utf-8")

    # Recompute trace_sha256 in receipt
    trace_sha256 = hashlib.sha256(
        trace_path.read_text(encoding="utf-8").encode("utf-8")
    ).hexdigest()
    receipt_path = staging / "receipt" / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["trace_sha256"] = trace_sha256
    receipt["governance_verdict"] = "DENY"
    receipt["status"] = "FAIL"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    result = subprocess.run(
        ["python", str(staging / "verifier" / "verify.py")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, (
        f"Expected exit 1 for DENY, got {result.returncode}\n{result.stderr}"
    )
