#!/usr/bin/env -S node --import tsx
/**
 * audit/run.ts – generate a REPEAT Level-3 receipt.
 *
 * Usage:  pnpm audit:receipt
 * Output: audit/out/openclaw/receipt.json
 */

import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { generateReceipt } from "./repeat_audit/index.ts";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const outputPath = join(repoRoot, "audit", "out", "openclaw", "receipt.json");

const receipt = generateReceipt({
  repoRoot,
  scopeDir: "scratch/shared",
  scopeLabel: "scratch/shared/**",
  stateBindingPaths: ["data/settings.json", "devplan.md"],
  outputPath,
});

const evidenceCount = Object.keys(receipt.evidence).length;
console.log(`audit:receipt  level=3  evidence=${evidenceCount} file(s)  → ${outputPath}`);
