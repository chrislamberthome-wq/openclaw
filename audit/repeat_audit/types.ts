/**
 * REPEAT/B4IU audit framework – type definitions.
 *
 * Level 3 (Receipt): cryptographic receipt of evidence files + state bindings.
 * Level 4 path: extend RepeatReceiptV1 with `provenance` field and signing metadata.
 */

/** SHA-256 hex digest, or null when the source file is absent. */
export type Sha256 = string;

/**
 * Level-3 REPEAT receipt stored at audit/out/openclaw/receipt.json.
 *
 * receipt_hash is the SHA-256 of the canonical (key-sorted) JSON of this
 * object with receipt_hash omitted – so the receipt is self-verifying.
 */
export interface RepeatReceiptV1 {
  schema: "repeat/receipt@1";
  level: 3;
  generated_at: string; // ISO-8601 UTC
  /** Glob pattern describing the evidence scope. */
  scope: string;
  /**
   * Checked-in state files whose hashes are captured as part of the receipt.
   * A null value means the file was absent at generation time (allowed).
   */
  state_bindings: Record<string, Sha256 | null>;
  /**
   * Relative paths (from repo root) → SHA-256 for every file matched by scope.
   * An empty object is valid when no evidence files exist yet.
   */
  evidence: Record<string, Sha256>;
  /** SHA-256 of canonical JSON of this receipt (this field excluded). */
  receipt_hash: Sha256;
}

/** Configuration passed to generateReceipt / verifyReceipt. */
export interface AuditConfig {
  /** Absolute path to the repository root. */
  repoRoot: string;
  /** Directory to scan for evidence files (relative to repoRoot). */
  scopeDir: string;
  /** Glob pattern label stored in the receipt. */
  scopeLabel: string;
  /** State-binding file paths (relative to repoRoot). Null if absent is ok. */
  stateBindingPaths: string[];
  /** Where to write / read receipt.json (absolute path). */
  outputPath: string;
}
