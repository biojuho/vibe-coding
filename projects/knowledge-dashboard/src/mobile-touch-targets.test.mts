import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const SRC_DIR = path.dirname(fileURLToPath(import.meta.url));

const readSource = (relativePath: string) =>
	readFileSync(path.join(SRC_DIR, relativePath), "utf8");

test("dashboard buttons and inputs keep mobile-safe touch targets", () => {
	const buttonSource = readSource(path.join("components", "ui", "button.tsx"));
	const inputSource = readSource(path.join("components", "ui", "input.tsx"));

	assert.match(buttonSource, /default:\s+"min-h-11 px-4 py-2"/);
	assert.match(buttonSource, /icon:\s+"h-11 w-11"/);
	assert.doesNotMatch(buttonSource, /default:\s+"h-9 px-4 py-2"/);
	assert.doesNotMatch(buttonSource, /icon:\s+"h-9 w-9"/);

	assert.match(inputSource, /"flex min-h-11 w-full/);
	assert.doesNotMatch(inputSource, /"flex h-9 w-full/);
});

test("dashboard tab and export menu actions keep mobile-safe touch targets", () => {
	const pageSource = readSource(path.join("app", "page.tsx"));
	const exportMenuSource = readSource(
		path.join("components", "ExportMenu.tsx"),
	);

	assert.match(pageSource, /flex min-h-11 items-center gap-2/);
	assert.match(pageSource, /flex min-w-11 items-center justify-center/);
	assert.match(exportMenuSource, /flex min-h-11 w-full items-center/);
});
