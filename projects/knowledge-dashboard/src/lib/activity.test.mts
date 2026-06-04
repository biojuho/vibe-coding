import assert from "node:assert/strict";
import test from "node:test";

import {
	getToolColor,
	getVerdictKind,
	groupSessionsByDate,
} from "./activity.ts";

test("getToolColor matches known tools and falls back to slate", () => {
	assert.match(getToolColor("Claude Opus 4.8"), /orange/);
	assert.match(getToolColor("Gemini 3.5"), /blue/);
	assert.match(getToolColor("Codex"), /green/);
	assert.match(getToolColor("Cursor"), /purple/);
	assert.match(getToolColor("Antigravity"), /blue/);
	assert.match(getToolColor("UnknownTool"), /slate/);
});

test("getVerdictKind handles Korean and English, conditional before approved", () => {
	assert.equal(getVerdictKind("APPROVED"), "approved");
	assert.equal(getVerdictKind("승인"), "approved");
	// "조건부 승인" contains 승인 but must resolve to conditional.
	assert.equal(getVerdictKind("조건부 승인"), "conditional");
	assert.equal(getVerdictKind("CONDITIONALLY_APPROVED"), "conditional");
	assert.equal(getVerdictKind("반려"), "rejected");
	assert.equal(getVerdictKind("REJECTED"), "rejected");
	assert.equal(getVerdictKind(undefined), null);
	assert.equal(getVerdictKind("기타"), null);
});

test("groupSessionsByDate groups and sorts dates descending", () => {
	const grouped = groupSessionsByDate([
		{ date: "2026-06-01", tool: "a", summary: "s1" },
		{ date: "2026-06-03", tool: "b", summary: "s2" },
		{ date: "2026-06-01", tool: "c", summary: "s3" },
	]);
	assert.deepEqual(
		grouped.map(([date]) => date),
		["2026-06-03", "2026-06-01"],
	);
	assert.equal(grouped[1][1].length, 2, "two sessions on 2026-06-01");
	assert.deepEqual(groupSessionsByDate(null), []);
	assert.deepEqual(groupSessionsByDate(undefined), []);
});
