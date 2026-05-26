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
			/const submitButtonText = isSaving\s*\?\s*["']개체 정보 저장 중\.\.\.["']\s*:\s*["']개체 정보 저장["'];?[\s\S]*?\{submitButtonText\}/,
		],
		[
			"components/tabs/CalvingTab.js",
			/const submitButtonText = isSaving\s*\?\s*["']분만 기록 저장 중\.\.\.["']\s*:\s*["']분만 완료 및 송아지 등록["'];?[\s\S]*?\{submitButtonText\}/,
		],
		[
			"components/tabs/ScheduleTab.js",
			/const submitButtonText = isSaving\s*\?\s*["']일정 등록 중\.\.\.["']\s*:\s*["']일정 등록하기["'];?[\s\S]*?\{submitButtonText\}/,
		],
		[
			"components/tabs/FeedTab.js",
			/const submitButtonText = isSaving\s*\?\s*["']급여 기록 저장 중\.\.\.["']\s*:\s*["']급여 기록 저장하기["'];?[\s\S]*?\{submitButtonText\}/,
		],
		[
			"components/tabs/InventoryTab.js",
			/const submitButtonText = isSaving\s*\?\s*["']재고 등록 중\.\.\.["']\s*:\s*["']재고 등록하기["'];?[\s\S]*?\{submitButtonText\}/,
		],
		[
			"components/tabs/SalesTab.js",
			/const submitButtonText = isSaving\s*\?\s*["']판매 기록 등록 중\.\.\.["']\s*:\s*["']판매 기록 등록하기["'];?[\s\S]*?\{submitButtonText\}/,
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
