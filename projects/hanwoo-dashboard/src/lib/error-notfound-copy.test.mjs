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

test("RouteError normalizes options and reset with safe defaults", () => {
	const source = readSource("app/error.js");
	assert.match(source, /function normalizeRouteErrorOptions\(options\) \{/);
	assert.match(source, /options && typeof options === ["']object["'] && !Array\.isArray\(options\)/);
	assert.match(source, /function normalizeRouteErrorReset\(reset\) \{/);
	assert.match(source, /typeof reset === ["']function["'] \? reset : \(\) => \{\}/);
});

test("RouteError reset button is type=button with accessible label", () => {
	const source = readSource("app/error.js");
	assert.match(source, /type="button"/);
	assert.match(source, /화면 다시 불러오기/);
	assert.match(source, /aria-label=\{resetButtonLabel\}/);
	assert.match(source, /title=\{resetButtonLabel\}/);
	assert.match(source, /safeReset\(\)/);
});

test("RouteError uses document navigation for dashboard recovery link", () => {
	const source = readSource("app/error.js");
	assert.match(source, /href="\/"/);
	assert.match(source, /aria-label="대시보드로 돌아가기"/);
	assert.match(source, /auth proxy owns protected redirects/);
});

test("RouteError has accessible heading labeled with aria-labelledby", () => {
	const source = readSource("app/error.js");
	assert.match(source, /aria-labelledby="route-error-title"/);
	assert.match(source, /id="route-error-title"/);
	assert.match(source, /잠시 문제가 발생했습니다/);
});

test("NotFound has accessible title and metadata for SEO", () => {
	const source = readSource("app/not-found.js");
	assert.match(source, /export const metadata = \{/);
	assert.match(source, /페이지를 찾을 수 없습니다 · Joolife/);
	assert.match(source, /aria-labelledby="not-found-title"/);
	assert.match(source, /id="not-found-title"/);
});

test("NotFound uses document navigation with auth proxy comment", () => {
	const source = readSource("app/not-found.js");
	assert.match(source, /href="\/"/);
	assert.match(source, /auth proxy owns protected redirects/);
	assert.match(source, /aria-label="대시보드로 돌아가기"/);
});

test("NotFound copy mentions 사육/재고/출하 for cattle dashboard context", () => {
	const source = readSource("app/not-found.js");
	assert.match(source, /사육/);
	assert.match(source, /재고/);
	assert.match(source, /출하/);
});
