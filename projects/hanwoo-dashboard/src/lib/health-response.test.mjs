import assert from "node:assert/strict";
import test from "node:test";

import {
	buildHealthResponse,
	normalizeHealthWarning,
} from "./health-response.mjs";

const TIMESTAMP = "2026-06-06T00:00:00.000Z";

test("buildHealthResponse reports connected runtime health as healthy", () => {
	const response = buildHealthResponse({
		connected: true,
		timestamp: TIMESTAMP,
	});

	assert.deepEqual(response, {
		body: {
			status: "healthy",
			database: "connected",
			timestamp: TIMESTAMP,
		},
		init: { status: 200 },
	});
});

test("buildHealthResponse keeps build-phase checks green but explicit", () => {
	const response = buildHealthResponse({
		skipped: true,
		timestamp: TIMESTAMP,
	});

	assert.deepEqual(response, {
		body: {
			status: "healthy",
			database: "disconnected",
			warning: "health check skipped during build",
			timestamp: TIMESTAMP,
		},
		init: { status: 200 },
	});
});

test("buildHealthResponse marks runtime database failures as degraded", () => {
	const response = buildHealthResponse({
		connected: false,
		warning: new Error("pooler unavailable"),
		timestamp: TIMESTAMP,
	});

	assert.deepEqual(response, {
		body: {
			status: "degraded",
			database: "disconnected",
			warning: "pooler unavailable",
			timestamp: TIMESTAMP,
		},
		init: { status: 503 },
	});
});

test("normalizeHealthWarning handles malformed warning input", () => {
	assert.equal(normalizeHealthWarning("  custom warning  "), "custom warning");
	assert.equal(normalizeHealthWarning({}), "Database connectivity issue");
	assert.equal(normalizeHealthWarning([]), "Database connectivity issue");
});
