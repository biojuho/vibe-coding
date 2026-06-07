import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, "..", "..");

function readProjectFile(relativePath) {
	return readFileSync(path.join(PROJECT_ROOT, relativePath), "utf8");
}

test("outbox worker notification copy is valid Korean text", () => {
	const source = readProjectFile("scripts/outbox-worker.mjs");

	assert.doesNotMatch(source, /\uFFFD/);
	assert.match(
		source,
		/message: `\$\{cow\.name\} \(\$\{cow\.tagNumber\}\) 발정 예정일이 \$\{daysLeft\}일 남았습니다\.`/,
	);
	assert.match(
		source,
		/message: `\$\{cow\.name\} \(\$\{cow\.tagNumber\}\) 분만 예정일이 \$\{daysLeft\}일 남았습니다\.`/,
	);
	assert.doesNotMatch(source, /諛쒖젙|遺꾨쭔|덉젙|⑥븯|듬땲/);
	assert.doesNotMatch(source, /���|��/);
});
