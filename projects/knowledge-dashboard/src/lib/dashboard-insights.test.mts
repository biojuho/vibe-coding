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
  assert.ok(insights.actions.some((action) => action.title === "Backfill repository metadata"));
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
  assert.ok(insights.actions.some((action) => action.title === "Attach sources to empty notebooks"));
  assert.ok(insights.actions.some((action) => action.title === "Raise notebook coverage"));
  assert.ok(insights.badges.some((badge) => badge.title === "Coverage gap"));
});

test("adds focus-mode messaging when analytics are filtered by query", () => {
  const insights = buildDashboardInsights(
    [{ language: "TypeScript" }, { language: "Python" }, { language: "Go" }],
    [{ title: "Query scoped notebook", source_count: 3 }],
    "python",
  );

  assert.ok(insights.badges.some((badge) => badge.title === "Focus mode"));
  assert.ok(insights.actions.some((action) => action.title === "Review this filtered slice"));
});
