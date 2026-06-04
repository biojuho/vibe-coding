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
	assert.ok(insights.badges.some((badge) => badge.title === "Metadata gap"));
	assert.ok(
		insights.actions.some(
			(action) => action.title === "Backfill repository metadata",
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
			(action) => action.title === "Attach sources to empty notebooks",
		),
	);
	assert.ok(
		insights.actions.some(
			(action) => action.title === "Raise notebook coverage",
		),
	);
	assert.ok(insights.badges.some((badge) => badge.title === "Coverage gap"));
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
	assert.equal(insights.actions[0].title, "Maintain the current balance");
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

	assert.ok(insights.badges.some((badge) => badge.title === "Focus mode"));
	assert.ok(
		insights.actions.some(
			(action) => action.title === "Review this filtered slice",
		),
	);
});
