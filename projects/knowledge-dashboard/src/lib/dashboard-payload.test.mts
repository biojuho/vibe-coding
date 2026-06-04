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
		overall: { score: 90, state: "ready" },
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

test("getApiErrorMessage extracts error string or falls back", () => {
	assert.equal(getApiErrorMessage({ error: "boom" }, "fallback"), "boom");
	assert.equal(getApiErrorMessage({ error: 1 }, "fallback"), "fallback");
	assert.equal(getApiErrorMessage(null, "fallback"), "fallback");
});
