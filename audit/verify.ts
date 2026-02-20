#!/usr/bin/env -S node --import tsx
/**
 * audit/verify.ts – verify the committed REPEAT Level-3 receipt (fail-closed).
 *
 * Usage:  pnpm audit:verify
 * Exits with code 1 when the current working tree diverges from the receipt.
 */

import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { verifyReceipt } from "./repeat_audit/index.ts";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const outputPath = join(repoRoot, "audit", "out", "openclaw", "receipt.json");

const result = verifyReceipt({
  repoRoot,
  scopeDir: "scratch/shared",
  scopeLabel: "scratch/shared/**",
  stateBindingPaths: ["data/settings.json", "devplan.md"],
  outputPath,
});

if (result.ok) {
  console.log("audit:verify  ✓  receipt matches working tree");
  process.exit(0);
} else {
  console.error("audit:verify  ✗  receipt verification FAILED:");
  for (const err of result.errors) {
    console.error(`  • ${err}`);
  }
  process.exit(1);
}
