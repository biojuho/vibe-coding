import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("Next dev server allows browser QA loopback HMR origin", async () => {
	const source = await readFile(path.join(process.cwd(), "next.config.ts"), "utf8");

	assert.match(
		source,
		/allowedDevOrigins:\s*\[\s*"127\.0\.0\.1"\s*\]/,
		"Next dev HMR must accept the 127.0.0.1 browser QA origin",
	);
	assert.match(
		source,
		/"connect-src 'self'"/,
		"production CSP should stay same-origin while dev origins are handled by Next config",
	);
});
