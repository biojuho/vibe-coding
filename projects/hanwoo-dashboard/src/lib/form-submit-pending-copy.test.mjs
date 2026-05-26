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

test("primary data-entry submit buttons show pending copy while saving", () => {
	const expectations = [
		[
			"components/forms/CattleForm.js",
			/\{isSaving\s*\?\s*["']저장 중\.\.\.["']\s*:\s*["']저장하기["']\s*\}/,
		],
		[
			"components/tabs/CalvingTab.js",
			/\{isSaving\s*\?\s*["']분만 기록 저장 중\.\.\.["']\s*:\s*["']분만 완료 및 송아지 등록["']\s*\}/,
		],
		[
			"components/tabs/ScheduleTab.js",
			/\{isSaving\s*\?\s*["']일정 등록 중\.\.\.["']\s*:\s*["']일정 등록하기["']\s*\}/,
		],
		[
			"components/tabs/FeedTab.js",
			/\{isSaving\s*\?\s*["']급여 기록 저장 중\.\.\.["']\s*:\s*["']급여 기록 저장하기["']\s*\}/,
		],
		[
			"components/tabs/InventoryTab.js",
			/\{isSaving\s*\?\s*["']재고 등록 중\.\.\.["']\s*:\s*["']등록하기["']\s*\}/,
		],
		[
			"components/tabs/SalesTab.js",
			/\{isSaving\s*\?\s*["']판매 기록 등록 중\.\.\.["']\s*:\s*["']등록하기["']\s*\}/,
		],
	];

	for (const [relativePath, pattern] of expectations) {
		const source = readSource(relativePath);

		assert.match(
			source,
			pattern,
			`${relativePath} should expose pending submit copy`,
		);
	}
});
