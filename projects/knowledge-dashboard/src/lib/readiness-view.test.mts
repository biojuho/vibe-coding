import assert from "node:assert/strict";
import test from "node:test";

import {
	resolveReadinessState,
	resolveSkillStatusState,
} from "./readiness-view.ts";

test("resolveReadinessState passes known states and defaults unknown to at-risk", () => {
	assert.equal(resolveReadinessState("ready"), "ready");
	assert.equal(resolveReadinessState("needs-review"), "needs-review");
	assert.equal(resolveReadinessState("blocked"), "blocked");
	assert.equal(resolveReadinessState("at-risk"), "at-risk");
	assert.equal(resolveReadinessState("totally-unknown"), "at-risk");
	assert.equal(resolveReadinessState(undefined), "at-risk");
	assert.equal(resolveReadinessState(null), "at-risk");
});

test("resolveSkillStatusState maps pass/warn/fail and undefined", () => {
	assert.equal(resolveSkillStatusState(undefined), "needs-review");
	assert.equal(
		resolveSkillStatusState({ summary: { status: "pass" } }),
		"ready",
	);
	assert.equal(
		resolveSkillStatusState({ summary: { status: "warn" } }),
		"needs-review",
	);
	assert.equal(
		resolveSkillStatusState({ summary: { status: "fail" } }),
		"blocked",
	);
});
