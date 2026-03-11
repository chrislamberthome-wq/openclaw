"""
repeat-ai-stream-cert-v1 verifier package.

Fail-closed v1.0 streaming certificate verifier for AI inference receipts.

Public API:
  - canonicalize.canonical_json_bytes
  - hash_projection.hash_projection / compute_receipt_hash
  - verify_receipt.verify_receipt / VerificationResult
  - replay_ledger.verify_ledger
  - policy_eval.evaluate_policy
"""

from verifier.verify_receipt import VerificationResult, verify_receipt

__all__ = ["verify_receipt", "VerificationResult"]
__version__ = "1.0.0"
