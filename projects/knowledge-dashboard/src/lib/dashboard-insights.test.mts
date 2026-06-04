import assert from "node:assert/strict";
import test from "node:test";

import { buildDashboardInsights } from "./dashboard-insights.ts";

test("treats unspecified languages as a metadata gap instead of a dominant stack", () => {
	const insights = buildDashboardInsights(
		[
			{ language: null },
			{ language: null },
			{ language: null },
			{ language: "TypeScript" },
		],
		[],
	);

	assert.equal(insights.summary.dominantLanguage, "TypeScript");
	assert.equal(insights.summary.unspecifiedLanguageCount, 3);
	assert.equal(insights.summary.unspecifiedLanguageShare, 75);
	assert.ok(insights.badges.some((badge) => badge.title === "메타데이터 누락"));
	assert.ok(
		insights.actions.some(
			(action) => action.title === "저장소 메타데이터 보완",
		),
	);
});

test("flags shallow notebooks and empty references with actionable recommendations", () => {
	const insights = buildDashboardInsights(
		[{ language: "TypeScript" }, { language: "Python" }],
		[
			{ title: "Empty notebook", source_count: 0 },
			{ title: "Thin notebook", source_count: 1 },
			{ title: "Healthy notebook", source_count: 4 },
		],
	);

	assert.equal(insights.summary.zeroSourceNotebookCount, 1);
	assert.equal(insights.summary.sourceCoverageRatio, 66.7);
	assert.ok(
		insights.actions.some(
			(action) => action.title === "빈 노트북에 소스 연결",
		),
	);
	assert.ok(
		insights.actions.some(
			(action) => action.title === "노트북 커버리지 향상",
		),
	);
	assert.ok(insights.badges.some((badge) => badge.title === "커버리지 부족"));
});

test("returns a safe, zeroed summary for an empty portfolio", () => {
	const insights = buildDashboardInsights([], []);

	assert.equal(insights.summary.repoCount, 0);
	assert.equal(insights.summary.notebookCount, 0);
	assert.equal(insights.summary.healthScore, 0);
	assert.equal(insights.summary.dominantLanguage, null);
	assert.equal(insights.summary.totalSources, 0);
	assert.deepEqual(insights.badges, []);
	// Always surfaces at least a maintenance recommendation so the panel is never blank.
	assert.ok(insights.actions.length >= 1);
	assert.equal(insights.actions[0].title, "현재 균형 유지");
});

test("tolerates nullish inputs without throwing", () => {
	const insights = buildDashboardInsights(
		null as unknown as Parameters<typeof buildDashboardInsights>[0],
		undefined as unknown as Parameters<typeof buildDashboardInsights>[1],
	);

	assert.equal(insights.summary.repoCount, 0);
	assert.equal(insights.summary.notebookCount, 0);
	assert.deepEqual(insights.languageData, []);
	assert.deepEqual(insights.notebookData, []);
});

test("adds focus-mode messaging when analytics are filtered by query", () => {
	const insights = buildDashboardInsights(
		[{ language: "TypeScript" }, { language: "Python" }, { language: "Go" }],
		[{ title: "Query scoped notebook", source_count: 3 }],
		"python",
	);

	assert.ok(insights.badges.some((badge) => badge.title === "집중 모드"));
	assert.ok(
		insights.actions.some(
			(action) => action.title === "필터된 범위 검토",
		),
	);
});

test("diversity, dominant share, and health score pin the penalty math (50/50)", () => {
	const insights = buildDashboardInsights(
		[{ language: "TypeScript" }, { language: "Python" }],
		[],
	);
	// Max-entropy 2-language split -> diversity 100.
	assert.equal(insights.summary.diversityScore, 100);
	assert.equal(insights.summary.dominantLanguageShare, 50);
	// health = diversity(100) - concentrationPenalty((50-45)*1.4=7) = 93.
	assert.equal(insights.summary.healthScore, 93);
});

test("median source depth handles odd and even notebook counts", () => {
	const odd = buildDashboardInsights(
		[],
		[
			{ title: "a", source_count: 1 },
			{ title: "b", source_count: 3 },
			{ title: "c", source_count: 2 },
		],
	);
	assert.equal(odd.summary.medianSourcesPerNotebook, 2);

	const even = buildDashboardInsights(
		[],
		[
			{ title: "a", source_count: 1 },
			{ title: "b", source_count: 2 },
			{ title: "c", source_count: 3 },
			{ title: "d", source_count: 4 },
		],
	);
	assert.equal(even.summary.medianSourcesPerNotebook, 2.5);
});

test("languages beyond the top 5 collapse into an 'Other' bucket", () => {
	const insights = buildDashboardInsights(
		[
			{ language: "TypeScript" },
			{ language: "Python" },
			{ language: "Go" },
			{ language: "Rust" },
			{ language: "Java" },
			{ language: "C" },
		],
		[],
	);
	assert.equal(insights.languageData.length, 6);
	const other = insights.languageData[insights.languageData.length - 1];
	assert.equal(other.name, "Other");
	assert.equal(other.value, 1);
	assert.equal(insights.summary.languageCount, 6);
});
