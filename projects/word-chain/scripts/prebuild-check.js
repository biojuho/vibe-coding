/* global process */
import path from "node:path";

const cwd = process.cwd();
const normalized = path.normalize(cwd);
const hasNonAscii = Array.from(normalized).some((char) => char.codePointAt(0) > 127);

if (hasNonAscii) {
  console.warn("[WARN] Non-ASCII characters detected in project path.");
  console.warn(`[WARN] Current path: ${normalized}`);
  console.warn(
    "[WARN] Vite build on Windows may have issues with non-ASCII paths. If build fails, consider moving to an ASCII-only path."
  );
}
