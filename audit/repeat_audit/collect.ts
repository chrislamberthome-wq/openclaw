/**
 * REPEAT audit – evidence + state-binding collection.
 * Requires Node >= 20.0.0 (readdirSync with recursive option, added in Node 18.17).
 * Fallback logic in collectEvidenceFiles handles differences in the Dirent field
 * name across Node 20.x minor releases (see inline comment).
 */

import { existsSync, readdirSync } from "node:fs";
import { join, relative } from "node:path";

/**
 * Recursively list all files under `dir`.
 * Returns paths relative to `baseDir`, sorted lexicographically.
 * Returns an empty array when `dir` does not exist.
 */
export function collectEvidenceFiles(dir: string, baseDir: string): string[] {
  if (!existsSync(dir)) {
    return [];
  }

  const entries = readdirSync(dir, { withFileTypes: true, recursive: true });
  const files: string[] = [];

  for (const entry of entries) {
    if (!entry.isFile()) {
      continue;
    }
    // entry.parentPath is the standard field name in Node 20.12+ / 22+.
    // In earlier Node 20 minor releases the same field was exposed as entry.path.
    // We try parentPath first and fall back to path, then finally to the root dir.
    const parentPath =
      (entry as unknown as { parentPath?: string }).parentPath ??
      (entry as unknown as { path?: string }).path ??
      dir;
    const abs = join(parentPath, entry.name);
    files.push(relative(baseDir, abs));
  }

  return files.toSorted();
}
