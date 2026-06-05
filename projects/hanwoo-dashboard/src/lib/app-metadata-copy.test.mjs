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

test("app metadata and PWA manifest use product-ready Korean copy", () => {
	const layoutSource = readProjectFile("src/app/layout.js");
	const manifest = JSON.parse(readProjectFile("public/manifest.json"));

	assert.match(layoutSource, /Joolife 한우 농장 관리/);
	assert.match(
		layoutSource,
		/한우 농장의 개체, 번식, 출하, 재고, 일정을 한곳에서 관리하는 운영 대시보드/,
	);
	assert.match(layoutSource, /Joolife 한우/);
	assert.doesNotMatch(layoutSource, /Joolife Dashboard/);
	assert.doesNotMatch(layoutSource, /Premium Hanwoo Farm Management System/);
	assert.match(layoutSource, /function normalizeRootLayoutOptions\(options\) \{/);
	assert.match(
		layoutSource,
		/return options && typeof options === ["']object["'] && !Array\.isArray\(options\)\s*\?\s*options\s*:\s*\{\s*\}\s*;?/,
	);
	assert.match(
		layoutSource,
		/export default function RootLayout\(options = \{\}\) \{/,
	);
	assert.match(
		layoutSource,
		/const \{ children \} = normalizeRootLayoutOptions\(options\);/,
	);
	assert.match(layoutSource, /data-scroll-behavior=["']smooth["']/);
	assert.doesNotMatch(
		layoutSource,
		/export default function RootLayout\(\{ children \}\)/,
	);

	assert.equal(manifest.name, "Joolife 한우 농장 관리");
	assert.equal(manifest.short_name, "Joolife 한우");
	assert.equal(
		manifest.description,
		"한우 농장의 개체, 번식, 출하, 재고, 일정을 한곳에서 관리하는 운영 대시보드",
	);
});

test("proxy leaves public health and PWA assets outside auth redirects", () => {
	const proxySource = readProjectFile("src/proxy.js");

	assert.match(proxySource, /api\/health/);
	assert.match(proxySource, /manifest\.json/);
	assert.match(proxySource, /api\/auth/);
});
