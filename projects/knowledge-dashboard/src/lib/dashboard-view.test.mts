import assert from "node:assert/strict";
import test from "node:test";

import type { GithubRepo } from "./dashboard-types.ts";
import {
	computeLanguageStats,
	filterDashboard,
	formatRelativeTime,
	formatTimestamp,
	getDataFreshness,
	getGithubRepoDisplayName,
	getTags,
} from "./dashboard-view.ts";

test("getTags maps bilingual keywords and caps at 3", () => {
	// "study"+"연구" -> research, "app"/"web" -> dev, "회의" -> plan, "논문" -> docs.
	// Four rules match but the result is capped at the first 3 (research/dev/plan).
	const repo = {
		id: 1,
		name: "study-app-web",
		description: "연구 회의 논문",
		html_url: "https://x",
		language: "TypeScript",
		stargazers_count: 0,
		updated_at: "2026-01-01",
	};
	const labels = getTags(repo).map((t) => t.label);
	assert.ok(labels.includes("연구 (Research)"));
	assert.ok(labels.includes("개발 (Dev)"));
	assert.ok(labels.includes("기획 (Plan)"));
	assert.equal(getTags(repo).length, 3, "max 3 tags");

	const empty = getTags({
		id: 2,
		name: "zzz",
		description: "",
		html_url: "",
		language: null,
		stargazers_count: 0,
		updated_at: "",
	});
	assert.deepEqual(empty, []);
});

test("getTags reads notebook title + source titles", () => {
	const notebook = {
		id: "n1",
		title: "pdf 자료 모음",
		source_count: 2,
		url: "",
		ownership: "owned",
		sources: [{ id: "s1", title: "meeting notes" }],
	};
	const labels = getTags(notebook).map((t) => t.label);
	assert.ok(labels.includes("자료 (Docs)"));
	assert.ok(labels.includes("기획 (Plan)"));
});

test("filterDashboard is case-insensitive over name/description/language and notebook title", () => {
	const data = {
		github: [
			{
				id: 1,
				name: "Alpha",
				description: "first",
				html_url: "",
				language: "Python",
				stargazers_count: 0,
				updated_at: "",
			},
			{
				id: 2,
				name: "Beta",
				description: "second",
				html_url: "",
				language: "Go",
				stargazers_count: 0,
				updated_at: "",
			},
		],
		notebooklm: [
			{ id: "n1", title: "Alpha notes", source_count: 1, url: "", ownership: "owned" },
		],
	};

	assert.equal(filterDashboard(data, "").github.length, 2, "empty term -> all");
	assert.equal(filterDashboard(data, "alpha").github.length, 1);
	assert.equal(filterDashboard(data, "alpha").notebooklm.length, 1);
	assert.equal(filterDashboard(data, "go").github.length, 1, "language match");
	assert.equal(filterDashboard(data, "zzz").github.length, 0);
	assert.deepEqual(filterDashboard(null, "x"), { github: [], notebooklm: [] });
});

test("repo display name falls back before rendering or filtering", () => {
	const repo = {
		id: 3,
		name: undefined,
		description: "",
		html_url: "https://github.com/acme/recovered-name",
		language: null,
		stargazers_count: 0,
		updated_at: "",
	} as unknown as GithubRepo;

	assert.equal(getGithubRepoDisplayName(repo), "recovered-name");
	assert.equal(
		filterDashboard({ github: [repo], notebooklm: [] }, "recovered").github.length,
		1,
	);
	assert.doesNotThrow(() => getTags(repo));
});

test("computeLanguageStats uses classified count, not total repos", () => {
	const github = [
		{ id: 1, name: "", description: "", html_url: "", language: "TS", stargazers_count: 0, updated_at: "" },
		{ id: 2, name: "", description: "", html_url: "", language: "TS", stargazers_count: 0, updated_at: "" },
		{ id: 3, name: "", description: "", html_url: "", language: null, stargazers_count: 0, updated_at: "" },
	];
	const stats = computeLanguageStats(github, [
		{ id: "n", title: "x", source_count: 4, url: "", ownership: "owned" },
	]);
	assert.equal(stats.classifiedCount, 2, "null-language repo excluded from denominator");
	assert.deepEqual(stats.sortedLangs, [["TS", 2]]);
	assert.equal(stats.totalSources, 4);
});

test("formatTimestamp guards invalid/empty input", () => {
	assert.equal(formatTimestamp(""), "—");
	assert.equal(formatTimestamp("not-a-date"), "—");
	assert.equal(formatTimestamp(null), "—");
	assert.notEqual(formatTimestamp("2026-06-04T00:00:00Z"), "—");
});

test("formatRelativeTime buckets by minute/hour/day", () => {
	const now = new Date("2026-06-04T12:00:00Z").getTime();
	assert.equal(formatRelativeTime("2026-06-04T11:59:30Z", now), "방금");
	assert.equal(formatRelativeTime("2026-06-04T11:30:00Z", now), "30분 전");
	assert.equal(formatRelativeTime("2026-06-04T09:00:00Z", now), "3시간 전");
	assert.equal(formatRelativeTime("2026-06-01T12:00:00Z", now), "3일 전");
	assert.equal(formatRelativeTime("", now), "—");
});

test("getDataFreshness classifies tone by age", () => {
	const now = new Date("2026-06-04T12:00:00Z").getTime();
	assert.equal(getDataFreshness("2026-06-04T11:30:00Z", now).tone, "fresh");
	assert.equal(getDataFreshness("2026-06-04T01:00:00Z", now).tone, "recent");
	assert.equal(getDataFreshness("2026-06-01T00:00:00Z", now).tone, "stale");
	assert.equal(getDataFreshness("garbage", now).tone, "stale");
	assert.equal(getDataFreshness("garbage", now).label, "동기화 필요");
});
