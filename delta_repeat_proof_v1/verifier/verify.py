"""Main verification entry point.

Exit codes:
  0  Verification passed (receipt status = PASS).
  1  Verification failed (receipt status = FAIL; invariant violated).
  2  Verification error (malformed input, tooling fault, or unreadable data).

Usage (from repo root):
    python delta_repeat_proof_v1/verifier/verify.py

Usage (from delta_repeat_proof_v1/):
    python verifier/verify.py
"""

import hashlib
import json
import sys
from pathlib import Path


def _find_root() -> Path:
    """Locate the delta_repeat_proof_v1 directory regardless of cwd."""
    here = Path(__file__).resolve().parent
    candidate = here.parent
    if (candidate / "trace" / "trace.jsonl").exists():
        return candidate
    # Support running from repo root
    repo_root = here.parent.parent
    candidate2 = repo_root / "delta_repeat_proof_v1"
    if (candidate2 / "trace" / "trace.jsonl").exists():
        return candidate2
    raise FileNotFoundError("Cannot locate delta_repeat_proof_v1 root")


def _canonical_dumps(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _verify_hash_chain(events: list[dict]) -> None:
    """Raise ValueError if the hash chain is broken."""
    genesis = "0" * 64
    expected_prev = genesis
    for i, event in enumerate(events):
        if event.get("prev_hash") != expected_prev:
            raise ValueError(
                f"Hash chain broken at event seq={event.get('seq', i + 1)}: "
                f"expected prev_hash={expected_prev!r}, "
                f"got {event.get('prev_hash')!r}"
            )
        expected_prev = _sha256(_canonical_dumps(event))


def _extract_governance(events: list[dict]) -> dict:
    """Return the governance payload from the 'govern' stage event."""
    for event in events:
        if event.get("stage") == "govern":
            payload = event.get("payload", {})
            return {
                "decision_id": payload.get("decision_id"),
                "cycle_id": event.get("cycle_id"),
                "verdict": payload.get("verdict"),
                "constraints_applied": payload.get("constraints_applied"),
            }
    raise ValueError("No 'govern' stage event found in trace")


def main() -> int:
    try:
        root = _find_root()
        trace_path = root / "trace" / "trace.jsonl"
        task_path = root / "input" / "cognitive_task.json"
        receipt_path = root / "receipt" / "receipt.json"
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    # --- Load and validate canonical trace ---
    try:
        raw_lines = trace_path.read_text(encoding="utf-8").splitlines()
        events = []
        for lineno, line in enumerate(raw_lines, 1):
            if not line.strip():
                continue
            canonical_line = _canonical_dumps(json.loads(line))
            if canonical_line != line:
                print(
                    f"ERROR: Non-canonical JSON at trace line {lineno}",
                    file=sys.stderr,
                )
                return 2
            events.append(json.loads(line))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: Cannot read trace: {exc}", file=sys.stderr)
        return 2

    # --- Enforce five-stage cycle ---
    required_stages = ["reflect", "plan", "learn", "regulate", "govern"]
    actual_stages = [e.get("stage") for e in events]
    if actual_stages != required_stages:
        print(
            f"FAIL: Expected stages {required_stages}, got {actual_stages}",
            file=sys.stderr,
        )
        return 1

    # --- Hash chain ---
    try:
        _verify_hash_chain(events)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    # --- Governance ---
    try:
        governance = _extract_governance(events)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    verdict = governance.get("verdict")
    if verdict == "DENY":
        print("FAIL: Governance verdict is DENY; execution halted.", file=sys.stderr)
        _write_fail_receipt(receipt_path, events, verdict)
        return 1
    if verdict != "ALLOW":
        print(f"FAIL: Unexpected governance verdict: {verdict!r}", file=sys.stderr)
        return 1

    # --- Replay ---
    try:
        # Support running as `python verifier/verify.py` or as a module.
        try:
            from verifier.replay import replay_matches  # noqa: PLC0415
        except ModuleNotFoundError:
            sys.path.insert(0, str(root))
            from verifier.replay import replay_matches  # noqa: PLC0415

        replay_ok = replay_matches(task_path)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Replay failed: {exc}", file=sys.stderr)
        return 2

    # --- Compute trace SHA-256 ---
    trace_sha256 = _sha256(trace_path.read_text(encoding="utf-8"))

    # --- Build receipt ---
    cycle_id = events[0].get("cycle_id", "unknown")
    receipt = {
        "cycle_id": cycle_id,
        "trace_sha256": trace_sha256,
        "replay_match": replay_ok,
        "governance_verdict": verdict,
        "status": "PASS" if replay_ok else "FAIL",
    }

    # --- Compare against stored receipt ---
    try:
        stored = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: Cannot read receipt: {exc}", file=sys.stderr)
        return 2

    if receipt != stored:
        print("FAIL: Generated receipt does not match stored receipt.", file=sys.stderr)
        print(f"  Generated: {_canonical_dumps(receipt)}", file=sys.stderr)
        print(f"  Stored:    {_canonical_dumps(stored)}", file=sys.stderr)
        return 1

    if receipt["status"] != "PASS":
        print(f"FAIL: Receipt status is {receipt['status']!r}", file=sys.stderr)
        return 1

    print(f"PASS: {_canonical_dumps(receipt)}")
    return 0


def _write_fail_receipt(receipt_path: Path, events: list[dict], verdict: str) -> None:
    """Overwrite receipt.json with a FAIL receipt (used only in DENY path)."""
    trace_path = receipt_path.parent.parent / "trace" / "trace.jsonl"
    try:
        trace_sha256 = hashlib.sha256(
            trace_path.read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest()
    except OSError:
        trace_sha256 = "0" * 64

    cycle_id = events[0].get("cycle_id", "unknown") if events else "unknown"
    fail_receipt = {
        "cycle_id": cycle_id,
        "trace_sha256": trace_sha256,
        "replay_match": False,
        "governance_verdict": verdict,
        "status": "FAIL",
    }
    receipt_path.write_text(
        json.dumps(fail_receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    sys.exit(main())
