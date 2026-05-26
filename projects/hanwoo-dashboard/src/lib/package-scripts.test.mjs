import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, "..", "..");

function readPackageJson() {
	return JSON.parse(
		readFileSync(path.join(PROJECT_ROOT, "package.json"), "utf8"),
	);
}

test("unit test script suppresses typeless package warnings without changing module semantics", () => {
	const pkg = readPackageJson();

	assert.equal(pkg.type, undefined);
	assert.match(
		pkg.scripts.test,
		/node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test "src\/\*\*\/\*\.test\.mjs"/,
	);
});
