# Governance — v1.0

**Version:** 1.0.0  
**Status:** Frozen

---

## Scope

This document defines the governance rules for the `repeat-ai-stream-cert-v1` package: what may change, what may not, and how changes are decided.

---

## Frozen contracts

The following are frozen at v1.0 and **must not** change without a new major version:

1. `schemas/ai_inference_receipt.schema.json` — the legal field set, required keys, types, and `additionalProperties: false` constraint.
2. `docs/CANONICALIZATION.md` rules C1–C10 and the reference implementation in `verifier/canonicalize.py`.
3. `docs/HASH_PROJECTION.md` included/excluded field sets and the reference implementation in `verifier/hash_projection.py`.
4. The `PASS / FAIL / ERROR` classification logic in `verifier/verify_receipt.py` and documented in `docs/SPEC.md`.

---

## Non-breaking changes (permitted without version bump)

The following changes may be made to v1.0 without a version bump:

- Adding new **optional** fields to the schema (backward-compatible; old verifiers skip unknown fields).
- Adding new test cases to `tests/` that do not change the classification logic.
- Clarifying documentation language where the normative intent is unambiguous.
- Bug fixes to the verifier that make it **more strictly** enforce the existing spec (i.e. correctly classify inputs that were previously misclassified but whose correct classification is unambiguous under the spec).

---

## Breaking changes (require new major version)

The following changes require a new major version (e.g. `repeat-ai-stream-cert-v2`):

- Any change to the set of required fields in the receipt schema.
- Any change to the hash projection included/excluded field set.
- Any change to the canonicalization rules (C1–C10).
- Any change to `PASS / FAIL / ERROR` classification conditions.
- Removing `additionalProperties: false` from the receipt schema.
- Any change that would cause a previously `PASS` receipt to become `FAIL` or `ERROR`, or vice versa.

---

## Change process

1. Proposed changes are submitted as pull requests against the main branch.
2. Any change touching a frozen contract must include:
   - Updated schema or documentation
   - Updated reference implementation
   - Updated test matrix with new test vectors
   - A version bump in `pyproject.toml`
3. Breaking changes require creation of a new `repeat-ai-stream-cert-v{N}` package. The v1.0 package remains importable and frozen.

---

## Fail-closed policy

The verifier is fail-closed by design:

- Any ambiguity in a receipt resolves to `ERROR`, not `PASS`.
- Any exception raised during verification produces `ERROR`.
- A `PASS` outcome requires **all** checks to explicitly succeed.

This policy is normative and applies to all versions derived from v1.0.

---

## Audit and compliance notes

- This package provides **reproducibility certification** only.
- It does not assert model correctness, safety, fairness, or compliance with any regulatory standard.
- Integrators are responsible for ensuring that their model registry, policy engine, and input hashing conform to the contracts defined here.
- Receipts that pass verification are evidence that the recorded inference is **reproducible**; they are not evidence that the inference was **appropriate** for the use case.
