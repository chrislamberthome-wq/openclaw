# delta_repeat_proof_v1

A verifiable execution primitive that proves a governed decision occurred,
execution followed constraints, the result is reproducible, and verification
is independent.

Delta is no longer asserting governance; it is emitting governed execution receipts.

---

## Artifact Layout

```
delta_repeat_proof_v1/
├── input/
│   └── cognitive_task.json      # Deterministic task definition
├── schemas/
│   ├── event.schema.json        # Five-stage trace event contract
│   ├── governance.schema.json   # Binary governance decision contract
│   └── receipt.schema.json      # Execution receipt contract
├── trace/
│   └── trace.jsonl              # Append-only, canonical, hash-chained trace
├── receipt/
│   └── receipt.json             # Signed execution receipt
├── verifier/
│   ├── canonical.py             # Canonical JSON serialisation
│   ├── replay.py                # Deterministic task replay
│   ├── receipt.py               # Receipt generation and validation
│   └── verify.py                # Independent verifier entry point
├── tests/
│   ├── test_canonical.py
│   ├── test_hash_chain.py
│   ├── test_governance.py
│   ├── test_replay.py
│   ├── test_receipt.py
│   └── test_adversarial.py      # Adversarial tamper suite
└── scripts/
    └── run_verification_matrix.py
```

---

## Verification Matrix (Contract)

| Check              | Expected exit | Expected receipt status |
|--------------------|---------------|-------------------------|
| Baseline           | `0`           | `PASS`                  |
| Repeated runs      | `0`           | Identical SHA-256 hashes |
| Hash-chain break   | `1`           | `FAIL`                  |
| Non-canonical JSON | `1` or `2`    | Never `PASS`            |
| Replay mismatch    | `1`           | `FAIL`                  |
| Governance DENY    | `1`           | `FAIL`                  |

---

## Reproduce

```bash
git clone https://github.com/chrislamberthome-wq/openclaw
cd openclaw/delta_repeat_proof_v1
python verifier/verify.py
```

Expected output:

```
PASS: {"cycle_id":"cycle-0001","governance_verdict":"ALLOW","replay_match":true,"status":"PASS","trace_sha256":"9ab7699970b13d0337fe9ff4a7beb5f1955ae1dc44a454f065a7cf4c7fd782b5"}
```

---

## Run the full verification matrix

```bash
cd delta_repeat_proof_v1
python scripts/run_verification_matrix.py
```

---

## Run tests

```bash
cd delta_repeat_proof_v1
pip install pytest
python -m pytest tests/ -v
```

---

## Acceptance Criteria (Binary)

A valid run MUST produce all of the following:

- Canonical trace (each line is sorted-key, compact JSON).
- Unbroken hash chain (each `prev_hash` is SHA-256 of the canonical previous event).
- `ALLOW` governance verdict.
- Successful deterministic replay (`expected_output` matches re-executed result).
- Receipt with `status = PASS`.

Any violation is `FAIL`. Any malformed input, tooling fault, or unreadable
data that prevents determination is `ERROR` (exit code 2).

---

## Five-Stage Cycle

```
reflect → plan → learn → regulate → govern
```

All five stages are required in order. Absence, reordering, or duplication is a verification failure.

---

## Invariants

- **DENY halts**: A governance verdict of `DENY` results in exit code 1 with receipt status `FAIL`.
- **Replay mismatch fails**: If re-executing the task produces a result different from `expected_output`, exit code is 1.
- **Non-canonical JSON fails**: Any trace line not in canonical form (UTF-8, keys sorted, no extra whitespace) exits 1 or 2 — never PASS.
- **No warnings that pass**: There is no partial-success state. The verifier is binary.
