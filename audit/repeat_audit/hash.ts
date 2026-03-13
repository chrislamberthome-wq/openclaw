/**
 * REPEAT audit – SHA-256 hashing utilities (Node built-ins only).
 */

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

/** Compute SHA-256 hex digest of a file's raw bytes. */
export function sha256File(filePath: string): string {
  const data = readFileSync(filePath);
  return createHash("sha256").update(data).digest("hex");
}

/**
 * Compute SHA-256 hex digest of a canonical (key-sorted) JSON representation.
 * Used to produce the self-verifying receipt_hash.
 */
export function sha256Canonical(obj: unknown): string {
  return createHash("sha256").update(canonicalize(obj), "utf8").digest("hex");
}

/**
 * Deterministic JSON serialisation: objects with lexicographically sorted keys,
 * arrays with recursively canonicalized elements. No extra whitespace.
 */
export function canonicalize(value: unknown): string {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map(canonicalize).join(",")}]`;
  }
  const obj = value as Record<string, unknown>;
  const keys = Object.keys(obj).toSorted();
  const pairs = keys.map((k) => `${JSON.stringify(k)}:${canonicalize(obj[k])}`);
  return `{${pairs.join(",")}}`;
}
