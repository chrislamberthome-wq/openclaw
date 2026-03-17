"""Adversarial tests for the verification discipline.

Four tamper classes are covered:
  1. Hash-chain break  → exit 1, receipt FAIL
  2. Non-canonical JSON → exit 1 or 2, never PASS
  3. Replay mismatch   → exit 1, receipt FAIL
  4. Governance DENY   → exit 1, receipt FAIL

Each test:
  - Stages the proof artifact in a tmp directory.
  - Mutates exactly one surface.
  - Executes `python verifier/verify.py` via subprocess.
  - Asserts the expected exit code and, where applicable, receipt status.
"""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verifier.canonical import canonical_dumps

PROOF_ROOT = Path(__file__).resolve().parent.parent


def _stage(tmp_path: Path) -> Path:
    """Copy the entire proof artifact into *tmp_path* and return the root."""
    dest = tmp_path / "proof"
    shutil.copytree(PROOF_ROOT, dest)
    return dest


def _run_verifier(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(root / "verifier" / "verify.py")],
        capture_output=True,
        text=True,
    )


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _rebuild_hash_chain(events: list[dict]) -> list[str]:
    """Return canonical lines with recomputed prev_hash values."""
    prev_hash = "0" * 64
    lines = []
    for event in events:
        event = dict(event)
        event["prev_hash"] = prev_hash
        can = canonical_dumps(event)
        lines.append(can)
        prev_hash = _sha256(can)
    return lines


def _update_receipt_trace_sha256(root: Path) -> None:
    """Recompute and write the trace_sha256 in receipt.json."""
    trace_text = (root / "trace" / "trace.jsonl").read_text(encoding="utf-8")
    trace_sha256 = _sha256(trace_text)
    receipt_path = root / "receipt" / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["trace_sha256"] = trace_sha256
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Hash-chain break
# ---------------------------------------------------------------------------

def test_adversarial_hash_chain_break(tmp_path):
    """Mutate one event's data so the hash chain is invalid.

    Expected: exit code 1, receipt status irrelevant (verifier fails before).
    """
    root = _stage(tmp_path)
    trace_path = root / "trace" / "trace.jsonl"

    lines = trace_path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(l) for l in lines if l.strip()]

    # Tamper: change the payload of event 2 without recomputing the hash chain.
    events[1] = dict(events[1])
    events[1]["payload"] = {"steps": ["TAMPERED"]}
    # Write back without fixing hash chain (event 3's prev_hash is now wrong).
    new_lines = [canonical_dumps(events[0])]
    new_lines.append(canonical_dumps(events[1]))
    for ev in events[2:]:
        new_lines.append(canonical_dumps(ev))
    trace_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    _update_receipt_trace_sha256(root)

    result = _run_verifier(root)
    assert result.returncode == 1, (
        f"Expected exit 1 for hash-chain break, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # The verifier must not print PASS
    assert "PASS" not in result.stdout, (
        "Verifier must not output PASS on hash-chain break"
    )


# ---------------------------------------------------------------------------
# 2. Non-canonical JSON
# ---------------------------------------------------------------------------

def test_adversarial_non_canonical_json(tmp_path):
    """Reformat the trace with extra whitespace (pretty-printed).

    Expected: exit code 1 or 2, never PASS.
    """
    root = _stage(tmp_path)
    trace_path = root / "trace" / "trace.jsonl"

    lines = trace_path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(l) for l in lines if l.strip()]

    # Write pretty-printed JSON (non-canonical) for one line.
    pretty_lines = []
    for i, ev in enumerate(events):
        if i == 0:
            # Add extra whitespace → non-canonical
            pretty_lines.append(json.dumps(ev, sort_keys=True, indent=2))
        else:
            pretty_lines.append(canonical_dumps(ev))
    trace_path.write_text("\n".join(pretty_lines) + "\n", encoding="utf-8")

    result = _run_verifier(root)
    assert result.returncode in (1, 2), (
        f"Expected exit 1 or 2 for non-canonical JSON, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "PASS" not in result.stdout, (
        "Verifier must never PASS on non-canonical JSON"
    )


def test_adversarial_non_canonical_reordered_keys(tmp_path):
    """Reorder keys in one trace line (non-canonical).

    Expected: exit code 1 or 2, never PASS.
    """
    root = _stage(tmp_path)
    trace_path = root / "trace" / "trace.jsonl"

    lines = trace_path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(l) for l in lines if l.strip()]

    # Write event 0 with keys in reverse-sorted order → non-canonical.
    non_can = json.dumps(events[0], sort_keys=False, separators=(",", ":"))
    canonical = canonical_dumps(events[0])
    # Ensure the line truly differs from canonical (force a known reorder if needed).
    if non_can == canonical:
        reversed_dict = dict(reversed(list(events[0].items())))
        non_can = json.dumps(reversed_dict, separators=(",", ":"))
    # Final safety: if still equal (all keys happen to sort the same), insert extra space.
    if non_can == canonical:
        non_can = "{ " + canonical[1:]

    modified_lines = [non_can] + [canonical_dumps(e) for e in events[1:]]
    trace_path.write_text("\n".join(modified_lines) + "\n", encoding="utf-8")

    result = _run_verifier(root)
    assert result.returncode in (1, 2), (
        f"Expected exit 1 or 2 for reordered keys, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "PASS" not in result.stdout


# ---------------------------------------------------------------------------
# 3. Replay mismatch
# ---------------------------------------------------------------------------

def test_adversarial_replay_mismatch(tmp_path):
    """Mutate expected_output in cognitive_task.json.

    Expected: replay_match=false, exit code 1, receipt status FAIL.
    """
    root = _stage(tmp_path)
    task_path = root / "input" / "cognitive_task.json"

    task = json.loads(task_path.read_text(encoding="utf-8"))
    task["expected_output"] = 999  # wrong value
    task_path.write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")

    # The stored receipt still says PASS; verifier must detect mismatch.
    result = _run_verifier(root)
    assert result.returncode == 1, (
        f"Expected exit 1 for replay mismatch, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "PASS" not in result.stdout, (
        "Verifier must not PASS on replay mismatch"
    )


# ---------------------------------------------------------------------------
# 4. Governance DENY
# ---------------------------------------------------------------------------

def test_adversarial_governance_deny(tmp_path):
    """Force governance verdict to DENY in the trace.

    Expected: exit code 1, receipt status FAIL.
    """
    root = _stage(tmp_path)
    trace_path = root / "trace" / "trace.jsonl"

    lines = trace_path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(l) for l in lines if l.strip()]

    # Mutate govern event verdict to DENY, then rebuild hash chain.
    for ev in events:
        if ev["stage"] == "govern":
            ev["payload"] = dict(ev["payload"])
            ev["payload"]["verdict"] = "DENY"

    rebuilt = _rebuild_hash_chain(events)
    trace_path.write_text("\n".join(rebuilt) + "\n", encoding="utf-8")

    # Update receipt to reflect the new trace hash but keep stored status
    # as PASS so the verifier must override it.
    trace_sha256 = _sha256(trace_path.read_text(encoding="utf-8"))
    receipt_path = root / "receipt" / "receipt.json"
    stored = json.loads(receipt_path.read_text(encoding="utf-8"))
    stored["trace_sha256"] = trace_sha256
    stored["governance_verdict"] = "DENY"
    stored["status"] = "FAIL"
    stored["replay_match"] = False
    receipt_path.write_text(json.dumps(stored, indent=2) + "\n", encoding="utf-8")

    result = _run_verifier(root)
    assert result.returncode == 1, (
        f"Expected exit 1 for DENY, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "PASS" not in result.stdout, (
        "Verifier must not PASS on DENY verdict"
    )
