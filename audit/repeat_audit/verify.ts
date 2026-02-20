/**
 * REPEAT audit – Level-3 receipt verification (fail-closed).
 *
 * Reads the committed receipt, re-hashes all evidence and state-binding files,
 * and reports any mismatches.  Exits with code 1 on any discrepancy.
 */

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { collectEvidenceFiles } from "./collect.ts";
import { sha256Canonical, sha256File } from "./hash.ts";
import type { AuditConfig, RepeatReceiptV1 } from "./types.ts";

export interface VerifyResult {
  ok: boolean;
  errors: string[];
}

/**
 * Verify the receipt at config.outputPath against the current working tree.
 * Returns a VerifyResult; does NOT call process.exit – that is the caller's job.
 */
export function verifyReceipt(config: AuditConfig): VerifyResult {
  const { repoRoot, scopeDir, outputPath } = config;
  const errors: string[] = [];

  // 1. Receipt must exist.
  if (!existsSync(outputPath)) {
    return {
      ok: false,
      errors: [`Receipt not found: ${outputPath}. Run 'pnpm audit:receipt' to generate it.`],
    };
  }

  let receipt: RepeatReceiptV1;
  try {
    receipt = JSON.parse(readFileSync(outputPath, "utf8")) as RepeatReceiptV1;
  } catch (err) {
    return { ok: false, errors: [`Failed to parse receipt: ${String(err)}`] };
  }

  // 2. receipt_hash integrity check (self-verifying).
  const { receipt_hash, ...body } = receipt;
  const expectedHash = sha256Canonical(body);
  if (receipt_hash !== expectedHash) {
    errors.push(
      `receipt_hash mismatch: stored=${receipt_hash} computed=${expectedHash}. ` +
        `Receipt may be corrupted or manually edited.`,
    );
  }

  // 3. Evidence files – check all files listed in receipt exist and hash correctly.
  for (const [rel, storedHash] of Object.entries(receipt.evidence)) {
    const abs = join(repoRoot, rel);
    if (!existsSync(abs)) {
      errors.push(`Missing evidence file: ${rel}`);
      continue;
    }
    const actual = sha256File(abs);
    if (actual !== storedHash) {
      errors.push(
        `Hash mismatch for evidence file: ${rel} (stored=${storedHash} actual=${actual})`,
      );
    }
  }

  // 4. No unexpected new files in scope (files present but not in receipt).
  const evidenceDir = join(repoRoot, scopeDir);
  const currentFiles = collectEvidenceFiles(evidenceDir, repoRoot);
  for (const rel of currentFiles) {
    if (!(rel in receipt.evidence)) {
      errors.push(
        `Unreceipted evidence file: ${rel}. Run 'pnpm audit:receipt' to update the receipt.`,
      );
    }
  }

  // 5. State bindings – verify hashes match (null = file was absent at generation time).
  for (const [bindingPath, storedHash] of Object.entries(receipt.state_bindings)) {
    const abs = join(repoRoot, bindingPath);
    const currentHash = existsSync(abs) ? sha256File(abs) : null;
    if (currentHash !== storedHash) {
      errors.push(
        `State binding changed: ${bindingPath} ` +
          `(stored=${storedHash ?? "null"} actual=${currentHash ?? "null"}). ` +
          `Run 'pnpm audit:receipt' to update the receipt.`,
      );
    }
  }

  return { ok: errors.length === 0, errors };
}
