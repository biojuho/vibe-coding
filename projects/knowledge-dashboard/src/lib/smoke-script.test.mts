import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("smoke script uses an isolated port unless explicitly configured", async () => {
	const source = await readFile(path.join(process.cwd(), "scripts/smoke.mjs"), "utf8");

	assert.match(source, /from "node:net"/, "smoke must be able to ask the OS for a free port");
	assert.match(source, /server\.listen\(0, HOST, resolve\)/, "smoke must reserve a free local port");
	assert.match(source, /process\.env\.SMOKE_PORT/, "operators must still be able to override the port");
	assert.doesNotMatch(source, /SMOKE_PORT \?\? "3102"/, "smoke must not default to a shared fixed port");
	assert.doesNotMatch(source, /\bBASE_URL\b/, "smoke must use the resolved per-run base URL everywhere");
});
