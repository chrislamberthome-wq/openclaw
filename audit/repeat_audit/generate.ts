/**
 * REPEAT audit – Level-3 receipt generation.
 */

import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { collectEvidenceFiles } from "./collect.ts";
import { sha256Canonical, sha256File } from "./hash.ts";
import type { AuditConfig, RepeatReceiptV1, Sha256 } from "./types.ts";

/**
 * Generate a Level-3 REPEAT receipt and write it to config.outputPath.
 * Returns the receipt object.
 */
export function generateReceipt(config: AuditConfig): RepeatReceiptV1 {
  const { repoRoot, scopeDir, scopeLabel, stateBindingPaths, outputPath } = config;

  // --- Evidence ---
  const evidence: Record<string, Sha256> = {};
  const evidenceDir = join(repoRoot, scopeDir);
  const relPaths = collectEvidenceFiles(evidenceDir, repoRoot);
  for (const rel of relPaths) {
    evidence[rel] = sha256File(join(repoRoot, rel));
  }

  // --- State bindings ---
  const stateBindings: Record<string, Sha256 | null> = {};
  for (const bindingPath of stateBindingPaths) {
    const abs = join(repoRoot, bindingPath);
    stateBindings[bindingPath] = existsSync(abs) ? sha256File(abs) : null;
  }

  // --- Receipt body (without receipt_hash) ---
  const body = {
    schema: "repeat/receipt@1" as const,
    level: 3 as const,
    generated_at: new Date().toISOString(),
    scope: scopeLabel,
    state_bindings: stateBindings,
    evidence,
  };

  const receipt_hash = sha256Canonical(body);

  const receipt: RepeatReceiptV1 = { ...body, receipt_hash };

  // --- Write output ---
  const outDir = dirname(outputPath);
  if (!existsSync(outDir)) {
    mkdirSync(outDir, { recursive: true });
  }
  writeFileSync(outputPath, JSON.stringify(receipt, null, 2) + "\n", "utf8");

  return receipt;
}
