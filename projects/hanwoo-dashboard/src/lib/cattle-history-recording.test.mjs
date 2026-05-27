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

test("cattle history recording tolerates unserializable optional metadata", () => {
	const source = readSource("lib/actions/_helpers.js");

	assert.match(source, /function serializeCattleHistoryMetadata\(metadata\) \{/);
	assert.match(source, /return JSON\.stringify\(metadata\);/);
	assert.match(
		source,
		/console\.error\("Failed to serialize cattle history metadata:", error\);/,
	);
	assert.match(source, /return null;/);
	assert.match(
		source,
		/metadata: serializeCattleHistoryMetadata\(metadata\),/,
	);
	assert.doesNotMatch(source, /metadata: metadata \? JSON\.stringify\(metadata\) : null,/);
});

test("cattle history recording falls back for malformed event dates", () => {
	const source = readSource("lib/actions/_helpers.js");

	assert.match(source, /function normalizeCattleHistoryEventDate\(value\) \{/);
	assert.match(
		source,
		/const date = value instanceof Date \? value : new Date\(value\);/,
	);
	assert.match(source, /return Number\.isNaN\(date\.getTime\(\)\) \? new Date\(\) : date;/);
	assert.match(
		source,
		/eventDate: normalizeCattleHistoryEventDate\(eventDate\),/,
	);
	assert.doesNotMatch(source, /eventDate: new Date\(eventDate\),/);
});
