#!/usr/bin/env python3
"""Verification matrix runner.

Performs three operations in sequence and emits JSON records:
  1. Baseline verification  – verifier must exit 0, receipt status PASS.
  2. Determinism runs       – run verifier N times, hash receipt.json, all hashes identical.
  3. Adversarial runs       – four tamper classes, each must fail closed.

Output is one JSON record per check to stdout; overall exit code is 0 iff all
checks pass, 1 otherwise.

Usage:
    python scripts/run_verification_matrix.py [--runs N]
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROOF_ROOT = Path(__file__).resolve().parent.parent
VERIFIER = PROOF_ROOT / "verifier" / "verify.py"

# Ensure the verifier package is importable when this script runs from any cwd.
if str(PROOF_ROOT) not in sys.path:
    sys.path.insert(0, str(PROOF_ROOT))

from verifier.canonical import canonical_dumps as _vcanonical  # noqa: E402


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _canonical_dumps(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(root / "verifier" / "verify.py")],
        capture_output=True,
        text=True,
    )


def _stage(tmp_dir: str) -> Path:
    dest = Path(tmp_dir) / "proof"
    shutil.copytree(PROOF_ROOT, dest)
    return dest


def _rebuild_hash_chain(events: list[dict]) -> list[str]:
    prev_hash = "0" * 64
    lines = []
    for event in events:
        event = dict(event)
        event["prev_hash"] = prev_hash
        can = _vcanonical(event)
        lines.append(can)
        prev_hash = _sha256(can)
    return lines


def emit(record: dict) -> None:
    print(json.dumps(record, sort_keys=True))


# ---------------------------------------------------------------------------
# Check 1: Baseline
# ---------------------------------------------------------------------------

def check_baseline() -> bool:
    result = _run(PROOF_ROOT)
    passed = result.returncode == 0
    receipt_status = "UNKNOWN"
    if result.stdout.startswith("PASS:"):
        try:
            receipt_status = json.loads(result.stdout[5:].strip())["status"]
        except Exception:  # noqa: BLE001
            pass
    emit({
        "check": "baseline",
        "exit_code": result.returncode,
        "status": receipt_status if passed else "FAIL",
        "passed": passed,
    })
    return passed


# ---------------------------------------------------------------------------
# Check 2: Determinism
# ---------------------------------------------------------------------------

def check_determinism(n: int = 5) -> bool:
    receipt_hashes: set[str] = set()
    for _ in range(n):
        result = _run(PROOF_ROOT)
        if result.returncode != 0:
            emit({
                "check": "determinism",
                "passed": False,
                "reason": f"Verifier exited {result.returncode} during determinism run",
            })
            return False
        # Hash the receipt.json file content (not the stdout).
        receipt_text = (PROOF_ROOT / "receipt" / "receipt.json").read_text(encoding="utf-8")
        receipt_hashes.add(_sha256(receipt_text))

    passed = len(receipt_hashes) == 1
    emit({
        "check": "determinism",
        "runs": n,
        "distinct_receipt_hashes": len(receipt_hashes),
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
    })
    return passed


# ---------------------------------------------------------------------------
# Check 3: Adversarial cases
# ---------------------------------------------------------------------------

def _adversarial_hash_chain_break(root: Path) -> None:
    """Tamper: mutate payload of event 2 without fixing hash chain."""
    trace_path = root / "trace" / "trace.jsonl"
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(l) for l in lines if l.strip()]
    events[1] = dict(events[1])
    events[1]["payload"] = {"steps": ["TAMPERED"]}
    new_lines = [_vcanonical(events[0]), _vcanonical(events[1])]
    for ev in events[2:]:
        new_lines.append(_vcanonical(ev))
    trace_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    # Update receipt trace_sha256
    trace_sha256 = _sha256(trace_path.read_text(encoding="utf-8"))
    rp = root / "receipt" / "receipt.json"
    r = json.loads(rp.read_text(encoding="utf-8"))
    r["trace_sha256"] = trace_sha256
    rp.write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")


def _adversarial_non_canonical(root: Path) -> None:
    """Tamper: pretty-print one trace line."""
    trace_path = root / "trace" / "trace.jsonl"
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(l) for l in lines if l.strip()]
    pretty = json.dumps(events[0], sort_keys=True, indent=2)
    modified = [pretty] + [_vcanonical(e) for e in events[1:]]
    trace_path.write_text("\n".join(modified) + "\n", encoding="utf-8")


def _adversarial_replay_mismatch(root: Path) -> None:
    """Tamper: set expected_output to wrong value."""
    task_path = root / "input" / "cognitive_task.json"
    task = json.loads(task_path.read_text(encoding="utf-8"))
    task["expected_output"] = 999
    task_path.write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")


def _adversarial_governance_deny(root: Path) -> None:
    """Tamper: set governance verdict to DENY, rebuild chain."""
    trace_path = root / "trace" / "trace.jsonl"
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(l) for l in lines if l.strip()]
    for ev in events:
        if ev["stage"] == "govern":
            ev["payload"] = dict(ev["payload"])
            ev["payload"]["verdict"] = "DENY"
    rebuilt = _rebuild_hash_chain(events)
    trace_path.write_text("\n".join(rebuilt) + "\n", encoding="utf-8")
    trace_sha256 = _sha256(trace_path.read_text(encoding="utf-8"))
    rp = root / "receipt" / "receipt.json"
    r = json.loads(rp.read_text(encoding="utf-8"))
    r["trace_sha256"] = trace_sha256
    r["governance_verdict"] = "DENY"
    r["status"] = "FAIL"
    r["replay_match"] = False
    rp.write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")


_ADVERSARIAL_CASES = [
    ("adversarial: hash-chain break", _adversarial_hash_chain_break, (1,)),
    ("adversarial: non-canonical JSON", _adversarial_non_canonical, (1, 2)),
    ("adversarial: replay mismatch", _adversarial_replay_mismatch, (1,)),
    ("adversarial: governance DENY", _adversarial_governance_deny, (1,)),
]


def check_adversarial() -> bool:
    all_passed = True
    for name, mutate_fn, expected_codes in _ADVERSARIAL_CASES:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = _stage(tmp_dir)
            try:
                mutate_fn(root)
            except Exception as exc:  # noqa: BLE001
                emit({
                    "check": name,
                    "exit_code": -1,
                    "status": "ERROR",
                    "passed": False,
                    "reason": str(exc),
                })
                all_passed = False
                continue

            result = _run(root)
            passed = (
                result.returncode in expected_codes
                and "PASS" not in result.stdout
            )
            record = {
                "check": name,
                "exit_code": result.returncode,
                "status": "FAIL" if not passed else "PASS",
                "passed": passed,
            }
            if not passed:
                record["stderr"] = result.stderr.strip()
            emit(record)
            all_passed = all_passed and passed

    return all_passed


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Run verification matrix")
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of determinism runs (default: 5)",
    )
    args = parser.parse_args()

    results = []

    b = check_baseline()
    results.append(b)

    d = check_determinism(args.runs)
    results.append(d)

    a = check_adversarial()
    results.append(a)

    overall = all(results)
    emit({
        "check": "overall",
        "passed": overall,
        "status": "PASS" if overall else "FAIL",
    })
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
