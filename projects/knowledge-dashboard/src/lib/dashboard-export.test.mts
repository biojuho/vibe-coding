import assert from "node:assert/strict";
import test from "node:test";

import {
	buildNotebooksCsv,
	buildReposCsv,
	buildSummaryText,
	csvCell,
	toCsv,
} from "./dashboard-export.ts";

test("csvCell quotes and escapes cells with commas, quotes, newlines", () => {
	assert.equal(csvCell("plain"), "plain");
	assert.equal(csvCell("a,b"), '"a,b"');
	assert.equal(csvCell('he said "hi"'), '"he said ""hi"""');
	assert.equal(csvCell("line1\nline2"), '"line1\nline2"');
	assert.equal(csvCell(null), "");
	assert.equal(csvCell(42), "42");
});

test("toCsv joins headers and rows with CRLF", () => {
	const csv = toCsv(["a", "b"], [[1, 2], [3, 4]]);
	assert.equal(csv, "a,b\r\n1,2\r\n3,4");
});

test("buildReposCsv emits a header and escapes commas in descriptions", () => {
	const csv = buildReposCsv([
		{
			id: 1,
			name: "repo",
			description: "does a, b, c",
			html_url: "https://x",
			language: "TS",
			stargazers_count: 9,
			updated_at: "2026-06-04",
		},
	]);
	const lines = csv.split("\r\n");
	assert.equal(lines[0], "name,language,stars,updated_at,url,description");
	assert.ok(lines[1].includes('"does a, b, c"'));
	assert.ok(lines[1].includes("https://x"));
});

test("buildNotebooksCsv emits expected columns", () => {
	const csv = buildNotebooksCsv([
		{ id: "n1", title: "T", source_count: 3, url: "u", ownership: "owned" },
	]);
	const lines = csv.split("\r\n");
	assert.equal(lines[0], "title,source_count,ownership,url");
	assert.equal(lines[1], "T,3,owned,u");
});

test("buildSummaryText includes counts and optional qaqc/readiness", () => {
	const text = buildSummaryText({
		last_updated: "2026-06-04T00:00:00Z",
		github: [
			{ id: 1, name: "a", description: "", html_url: "", language: "TS", stargazers_count: 0, updated_at: "" },
		],
		notebooklm: [
			{ id: "n", title: "x", source_count: 4, url: "", ownership: "owned" },
		],
		qaqc: {
			timestamp: "",
			verdict: "APPROVED",
			elapsed_sec: 1,
			projects: {},
			total: { passed: 10, failed: 0 },
			ast_check: { total: 1, ok: 1, failures: [] },
			security_scan: { status: "CLEAR", issues: [] },
			infrastructure: {},
		},
	});
	assert.ok(text.includes("저장소 1개"));
	assert.ok(text.includes("노트북 1개"));
	assert.ok(text.includes("참조 소스: 4개"));
	assert.ok(text.includes("APPROVED"));
});
