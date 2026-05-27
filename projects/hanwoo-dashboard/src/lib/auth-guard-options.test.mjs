import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

function readSource(relativePath) {
	return readFileSync(path.join(SRC_ROOT, relativePath), "utf8");
}

test("auth guard normalizes malformed options before destructuring", () => {
	const source = readSource("lib/auth-guard.js");

	assert.match(
		source,
		/function normalizeObject\(value\) \{\s+return value && typeof value === "object" \? value : \{\};\s+\}/,
	);
	assert.match(
		source,
		/const \{ redirectToLogin = false \} = normalizeObject\(options\);/,
	);
	assert.doesNotMatch(
		source,
		/const \{ redirectToLogin = false \} = options;/,
	);
});
