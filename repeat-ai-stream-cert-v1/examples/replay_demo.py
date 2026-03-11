#!/usr/bin/env python3
"""replay_demo.py — Example: replay-verify a ledger of AI inference receipts.

This script loads the test fixture ledgers and runs the replay verifier,
printing a summary of each entry's verification outcome.

Usage:
    python examples/replay_demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from the repo root without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent))

from verifier.replay_ledger import verify_ledger

FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures"

OUTCOME_ICON = {
    "PASS": "✓",
    "FAIL": "✗",
    "ERROR": "!",
}


def load_jsonl(path: Path) -> list[dict]:  # type: ignore[type-arg]
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def demo_ledger(name: str) -> None:
    path = FIXTURES / name
    entries = load_jsonl(path)
    results = verify_ledger(entries)

    print(f"\n=== {name} ({len(entries)} entries) ===")
    all_pass = True
    for r in results:
        icon = OUTCOME_ICON.get(r.outcome, "?")
        detail = f" — {r.error_detail}" if r.error_detail else ""
        print(f"  [{icon}] entry={r.entry_id} outcome={r.outcome}{detail}")
        if r.outcome != "PASS":
            all_pass = False

    summary = "All entries PASS" if all_pass else "One or more entries FAIL/ERROR"
    print(f"  => {summary}")


def main() -> None:
    print("repeat-ai-stream-cert-v1 replay demo")
    print("======================================")
    demo_ledger("ledger_PASS.jsonl")
    demo_ledger("ledger_TAMPERED.jsonl")


if __name__ == "__main__":
    main()
