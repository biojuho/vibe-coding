import assert from "node:assert/strict";
import test from "node:test";

import {
	getApiErrorMessage,
	isDashboardDataPayload,
	isProductReadinessPayload,
	isQaQcPayload,
	isSkillLintPayload,
} from "./dashboard-payload.ts";

test("isDashboardDataPayload requires last_updated string and array fields", () => {
	assert.equal(
		isDashboardDataPayload({
			last_updated: "2026-06-04T00:00:00Z",
			github: [],
			notebooklm: [],
		}),
		true,
	);
	assert.equal(isDashboardDataPayload(null), false);
	assert.equal(
		isDashboardDataPayload({ last_updated: 1, github: [], notebooklm: [] }),
		false,
	);
	assert.equal(
		isDashboardDataPayload({
			last_updated: "x",
			github: {},
			notebooklm: [],
		}),
		false,
	);
});

const validQaQc = {
	timestamp: "2026-06-04T00:00:00Z",
	verdict: "APPROVED",
	elapsed_sec: 1,
	projects: {},
	total: { passed: 5, failed: 0 },
	ast_check: { total: 1, ok: 1, failures: [] },
	security_scan: { status: "CLEAR", issues: [] },
	infrastructure: {},
};

test("isQaQcPayload enforces the fields the panel dereferences", () => {
	assert.equal(isQaQcPayload(validQaQc), true);

	// total present but not numeric -> rejected (the old shallow guard let this through)
	assert.equal(
		isQaQcPayload({ ...validQaQc, total: {} }),
		false,
		"empty total must fail",
	);
	assert.equal(
		isQaQcPayload({ ...validQaQc, ast_check: { total: 1, ok: 1 } }),
		false,
		"ast_check without failures[] must fail",
	);
	assert.equal(
		isQaQcPayload({ ...validQaQc, security_scan: { status: "CLEAR" } }),
		false,
		"security_scan without issues[] must fail",
	);
	assert.equal(
		isQaQcPayload({ ...validQaQc, projects: [] as unknown }),
		true,
		"projects as array is still an object (Object.entries-safe)",
	);
	assert.equal(isQaQcPayload({ timestamp: "x", verdict: "y" }), false);
});

test("isProductReadinessPayload requires workspace_blockers array", () => {
	const base = {
		generated_at: "2026-06-04",
		overall: {
			score: 90,
			state: "ready",
			project_count: 4,
			blocked_count: 1,
			workspace_blocker_count: 0,
		},
		projects: [],
		next_actions: [],
		workspace_blockers: [],
	};
	assert.equal(isProductReadinessPayload(base), true);
	assert.equal(
		isProductReadinessPayload({ ...base, workspace_blockers: undefined }),
		false,
		"missing workspace_blockers must fail (panel reads .length)",
	);
	assert.equal(
		isProductReadinessPayload({ ...base, overall: "x" }),
		false,
	);
	assert.equal(
		isProductReadinessPayload({ ...base, overall: { score: 90, state: "ready" } }),
		false,
		"overall missing count fields must fail (renders them directly)",
	);
});

test("isSkillLintPayload validates summary object and issues array", () => {
	assert.equal(
		isSkillLintPayload({
			generated_at: "2026-06-04",
			summary: { status: "pass" },
			issues: [],
		}),
		true,
	);
	assert.equal(
		isSkillLintPayload({ generated_at: "x", summary: {}, issues: "no" }),
		false,
	);
});

test("KD-PLD002: isQaQcPayload requires ast_check.ok and ast_check.total as numbers", () => {
	// QaQcPanel.tsx line 273 renders data.ast_check.ok/total directly.
	// Missing or non-numeric values produce "/" string or NaN without this guard.
	assert.equal(
		isQaQcPayload({ ...validQaQc, ast_check: { total: 10, failures: [] } }),
		false,
		"missing ast_check.ok must fail",
	);
	assert.equal(
		isQaQcPayload({ ...validQaQc, ast_check: { ok: 10, failures: [] } }),
		false,
		"missing ast_check.total must fail",
	);
	assert.equal(
		isQaQcPayload({ ...validQaQc, ast_check: { ok: "ten", total: 10, failures: [] } }),
		false,
		"non-numeric ast_check.ok must fail",
	);
});

test("getApiErrorMessage extracts error string or falls back", () => {
	assert.equal(getApiErrorMessage({ error: "boom" }, "fallback"), "boom");
	assert.equal(getApiErrorMessage({ error: 1 }, "fallback"), "fallback");
	assert.equal(getApiErrorMessage(null, "fallback"), "fallback");
});
