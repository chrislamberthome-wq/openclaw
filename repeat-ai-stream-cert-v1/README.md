# repeat-ai-stream-cert-v1

**Version:** 1.0.0  
**Status:** Frozen (fail-closed)

---

## Purpose

This package certifies that a recorded AI inference event is **reproducible** from the declared input bindings, artifact bindings, preprocessing contract, and policy contract.

It does **not** prove that a model is correct in the real world.  
It is a **deterministic audit envelope**, not a truth oracle.

---

## What this package does

`repeat-ai-stream-cert-v1` provides:

1. **Receipt schema** — the legal field set, types, required keys, and forbidden ambiguity for an `ai_inference_receipt`.
2. **Canonicalization rules** — a deterministic specification for how a JSON object becomes bytes before hashing.
3. **Hash projection rules** — which receipt fields are included in `receipt_hash` computation and which are excluded as derived or observational.
4. **Replay verifier** — deterministic `PASS / FAIL / ERROR` classification for schema validity, hash recomputation, ledger continuity, policy reproduction, and artifact binding.

---

## Verification outcomes

| Outcome | Meaning |
|---------|---------|
| `PASS`  | Schema-valid, hash-valid, ledger linkage valid, declared policy reproduces, all required artifacts bound correctly. |
| `FAIL`  | Schema-valid, but a business or governance rule does not hold (e.g. policy decision differs from recorded decision). |
| `ERROR` | Receipt is malformed, hash mismatches, ledger chain breaks, required artifact digest is missing, or replay cannot be performed under the declared contract. |

The verifier is **fail-closed**: any ambiguity resolves to `ERROR`, never to `PASS`.

---

## Limitations

- This package does not execute models; it verifies recorded receipts.
- It does not verify that a model's output was "correct" in any ground-truth sense.
- It does not manage cryptographic key infrastructure; `signature` field validation is out of scope for v1.0.
- It is scoped to single-chain sequential ledgers; distributed or branching ledgers are out of scope.

---

## Quick start

```bash
pip install repeat-ai-stream-cert-v1
```

```python
from verifier.verify_receipt import verify_receipt
import json

with open("tests/fixtures/receipt_PASS.json") as f:
    receipt = json.load(f)

result = verify_receipt(receipt, prior_receipt_hash=None)
print(result.outcome)   # "PASS"
print(result.message)
```

---

## Repository layout

```
repeat-ai-stream-cert-v1/
├─ schemas/                 # JSON Schema definitions (frozen v1)
├─ docs/                    # Specification documents
├─ verifier/                # Python verifier library
├─ tests/                   # pytest suite + fixtures
├─ examples/                # Runnable demonstration scripts
└─ .github/workflows/       # CI configuration
```

---

## Running tests

```bash
make test
```

or directly:

```bash
pytest tests/ -v
```

---

## Key contracts (v1.0, frozen)

- Schema: `schemas/ai_inference_receipt.schema.json`
- Canonicalization: `docs/CANONICALIZATION.md` / `verifier/canonicalize.py`
- Hash projection: `docs/HASH_PROJECTION.md` / `verifier/hash_projection.py`
- Replay verifier: `verifier/verify_receipt.py`
- Governance: `docs/GOVERNANCE.md`

Changes to any of these contracts require a new major version. v1.0 is frozen.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
