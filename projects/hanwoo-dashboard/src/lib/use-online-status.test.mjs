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

test("useOnlineStatus safely reads browser online state", () => {
	const source = readSource("lib/useOnlineStatus.js");

	assert.match(source, /function readNavigatorOnlineStatus\(\) \{/);
	assert.match(source, /if \(typeof navigator === "undefined"\) \{/);
	assert.match(source, /return true;/);
	assert.match(
		source,
		/try \{\s+return navigator\.onLine;\s+\} catch \{\s+return true;\s+\}/,
	);
	assert.match(source, /return readNavigatorOnlineStatus\(\);/);
	assert.doesNotMatch(
		source,
		/useState\(\(\) => \{[\s\S]*?return navigator\.onLine;/,
	);
});

test("useOnlineStatus tolerates browser event listener failures", () => {
	const source = readSource("lib/useOnlineStatus.js");

	assert.match(
		source,
		/useEffect\(\(\) => \{\s+if \(typeof window === "undefined"\) \{\s+return undefined;\s+\}/,
	);
	assert.match(
		source,
		/let registeredOnline = false;\s+let registeredOffline = false;/,
	);
	assert.match(
		source,
		/window\.addEventListener\("online", goOnline\);\s+registeredOnline = true;\s+window\.addEventListener\("offline", goOffline\);\s+registeredOffline = true;/,
	);
	assert.match(
		source,
		/catch \{\s+if \(registeredOnline\) \{\s+try \{\s+window\.removeEventListener\("online", goOnline\);/,
	);
	assert.match(
		source,
		/if \(registeredOffline\) \{\s+try \{\s+window\.removeEventListener\("offline", goOffline\);/,
	);
	assert.match(
		source,
		/return \(\) => \{\s+if \(registeredOnline\) \{\s+try \{\s+window\.removeEventListener\("online", goOnline\);/,
	);
	assert.doesNotMatch(
		source,
		/window\.addEventListener\("online", goOnline\);\s+window\.addEventListener\("offline", goOffline\);\s+return \(\) => \{/,
	);
	assert.doesNotMatch(
		source,
		/catch \{\s+return undefined;\s+\}/,
	);
});
