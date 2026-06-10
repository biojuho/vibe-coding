import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import {
	COPY_RETRY_ATTEMPTS,
	isMissingSourceDuringCopy,
} from "../../scripts/start-standalone.mjs";

test("smoke script uses an isolated port unless explicitly configured", async () => {
	const source = await readFile(path.join(process.cwd(), "scripts/smoke.mjs"), "utf8");

	assert.match(source, /from "node:net"/, "smoke must be able to ask the OS for a free port");
	assert.match(
		source,
		/resolveStandaloneServer/,
		"smoke must start the standalone server directly instead of leaking a wrapper process",
	);
	assert.match(source, /server\.listen\(0, HOST, resolve\)/, "smoke must reserve a free local port");
	assert.match(source, /process\.env\.SMOKE_PORT/, "operators must still be able to override the port");
	assert.match(
		source,
		/KNOWLEDGE_DASHBOARD_DATA_DIR: DATA_DIR/,
		"smoke must point the standalone server at the root fixture data directory",
	);
	assert.doesNotMatch(source, /SMOKE_PORT \?\? "3102"/, "smoke must not default to a shared fixed port");
	assert.doesNotMatch(source, /\bBASE_URL\b/, "smoke must use the resolved per-run base URL everywhere");
	assert.doesNotMatch(
		source,
		/\.next",\s*"standalone"/,
		"smoke fixtures must not write into Next standalone build output",
	);
});

test("standalone launcher repairs traced SWC helper dependency gaps", async () => {
	const source = await readFile(
		path.join(process.cwd(), "scripts/start-standalone.mjs"),
		"utf8",
	);

	assert.match(
		source,
		/prepareRuntimeDependencies/,
		"standalone startup must prepare runtime dependency fallbacks",
	);
	assert.match(
		source,
		/path\.join\(projectRoot,\s*"node_modules",\s*"@swc",\s*"helpers"\)/,
		"standalone startup must copy the local @swc/helpers package when tracing omits it",
	);
	assert.match(
		source,
		/path\.join\(serverDir,\s*"node_modules",\s*"@swc",\s*"helpers"\)/,
		"@swc/helpers must be copied inside the standalone server directory",
	);
});

test("standalone launcher repairs traced Next dist lib dependency gaps", async () => {
	const source = await readFile(
		path.join(process.cwd(), "scripts/start-standalone.mjs"),
		"utf8",
	);

	assert.match(
		source,
		/path\.join\(projectRoot,\s*"node_modules",\s*"next",\s*"dist",\s*"lib"\)/,
		"standalone startup must copy Next dist/lib when tracing omits runtime constants",
	);
	assert.match(
		source,
		/path\.join\(serverDir,\s*"node_modules",\s*"next",\s*"dist",\s*"lib"\)/,
		"Next dist/lib must be copied inside the standalone server directory",
	);
});

test("standalone launcher repairs traced Next environment dependency gaps", async () => {
	const source = await readFile(
		path.join(process.cwd(), "scripts/start-standalone.mjs"),
		"utf8",
	);

	assert.match(
		source,
		/path\.join\(projectRoot,\s*"node_modules",\s*"@next",\s*"env"\)/,
		"standalone startup must copy @next/env when tracing omits it",
	);
	assert.match(
		source,
		/path\.join\(serverDir,\s*"node_modules",\s*"@next",\s*"env"\)/,
		"@next/env must be copied inside the standalone server directory",
	);
});

test("standalone launcher retries transient static copy misses", async () => {
	assert.equal(COPY_RETRY_ATTEMPTS, 3);
	assert.equal(isMissingSourceDuringCopy({ code: "ENOENT" }), true);
	assert.equal(isMissingSourceDuringCopy({ code: "EACCES" }), false);
	assert.equal(isMissingSourceDuringCopy(null), false);
});
