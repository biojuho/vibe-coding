/* global process */
// Guards against a known Windows failure mode: Vite builds can choke on
// non-ASCII characters in the absolute project path. We warn rather than
// fail so CI on ASCII paths is unaffected.
import path from "node:path";

const cwd = process.cwd();
const normalized = path.normalize(cwd);
const hasNonAscii = Array.from(normalized).some(
	(char) => char.codePointAt(0) > 127,
);

if (hasNonAscii) {
	console.warn("[WARN] Non-ASCII characters detected in project path.");
	console.warn(`[WARN] Current path: ${normalized}`);
	console.warn(
		"[WARN] Vite build on Windows may fail on non-ASCII paths. " +
			"If the build fails, move the project to an ASCII-only path.",
	);
}
