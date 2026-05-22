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

test("shared dialog close control uses Korean screen-reader copy", () => {
	const source = readSource("components/ui/dialog.js");

	assert.match(source, /<span className="sr-only">닫기<\/span>/);
	assert.doesNotMatch(source, /<span className="sr-only">Close<\/span>/);
});
