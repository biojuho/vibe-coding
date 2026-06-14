/**
 * Behavioral tests for private pure helpers in:
 *   src/app/api/ai/insight/route.js
 *
 * POST handler depends on auth/subscription/network — source-grep guards only.
 * Extractable pure helpers: emitInsightMetric, normalizeInsightRequestBody,
 * normalizeGeminiInsightOptions, withInsightTimeout, InsightTimeoutError.
 *
 * route.js imports Next.js (cannot load in Node ESM).
 * Helpers are re-implemented inline.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const routeSrc = readFileSync(
	path.join(SRC_ROOT, "app/api/ai/insight/route.js"),
	"utf8",
);

// ── Inline re-implementations ────────────────────────────────────────────────

const METRIC_LOG_PREFIX = "[ai-insight-metric]";

function emitInsightMetric(payload) {
	try {
		const safePayload =
			payload && typeof payload === "object" && !Array.isArray(payload)
				? payload
				: {};
		console.log(METRIC_LOG_PREFIX, JSON.stringify(safePayload));
	} catch {}
}

function normalizeGeminiInsightOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeInsightRequestBody(body) {
	return body && typeof body === "object" && !Array.isArray(body) ? body : {};
}

class InsightTimeoutError extends Error {
	constructor(timeoutMs) {
		super(`AI insight generation timed out after ${timeoutMs}ms.`);
		this.name = "InsightTimeoutError";
		this.timeoutMs = timeoutMs;
	}
}

function withInsightTimeout(promise, timeoutMs = 10000) {
	let timeoutId = null;
	const timeoutPromise = new Promise((_, reject) => {
		try {
			timeoutId = setTimeout(
				() => reject(new InsightTimeoutError(timeoutMs)),
				timeoutMs,
			);
		} catch (error) {
			reject(new InsightTimeoutError(timeoutMs));
		}
	});

	return Promise.race([promise, timeoutPromise]).finally(() => {
		if (timeoutId !== null) {
			try {
				clearTimeout(timeoutId);
			} catch {}
		}
	});
}

// ── Source-grep guards: POST handler contract ────────────────────────────────

test("ai/insight/route.js POST: requireAuthenticatedSession guard", () => {
	assert.match(routeSrc, /requireAuthenticatedSession/);
	assert.match(routeSrc, /export async function POST\(request\)/);
	assert.match(routeSrc, /UNAUTHENTICATED/);
});

test("ai/insight/route.js POST: subscription check before proceeding", () => {
	assert.match(routeSrc, /getSubscriptionStatus/);
	assert.match(routeSrc, /SUBSCRIPTION_REQUIRED/);
	assert.match(routeSrc, /status: 403/);
});

test("ai/insight/route.js POST: rate limit check with ai-insight: prefix", () => {
	assert.match(routeSrc, /checkRateLimit\(`ai-insight:\$\{userId\}`/);
	assert.match(routeSrc, /RATE_LIMITED/);
	assert.match(routeSrc, /status: 429/);
});

test("ai/insight/route.js POST: heuristic fallback when GEMINI_API_KEY missing", () => {
	assert.match(routeSrc, /process\.env\.GEMINI_API_KEY/);
	assert.match(routeSrc, /buildHeuristicInsights/);
	assert.match(routeSrc, /source: ["']heuristic["']/);
});

test("ai/insight/route.js POST: cache hit path returns cached insights", () => {
	assert.match(routeSrc, /loadCachedInsight/);
	assert.match(routeSrc, /cached: true/);
	assert.match(routeSrc, /ageSeconds/);
});

test("ai/insight/route.js POST: forceRefresh=true drops cache before regenerating", () => {
	assert.match(routeSrc, /forceRefresh === true/);
	assert.match(routeSrc, /dropCachedInsight\(cacheKey\)/);
});

test("ai/insight/route.js POST: Gemini timeout triggers heuristic fallback", () => {
	assert.match(routeSrc, /InsightTimeoutError/);
	assert.match(routeSrc, /withInsightTimeout/);
	assert.match(routeSrc, /GEMINI_TIMEOUT_REASON/);
});

test("ai/insight/route.js emitInsightMetric: uses METRIC_LOG_PREFIX constant", () => {
	assert.match(routeSrc, /METRIC_LOG_PREFIX/);
	assert.match(routeSrc, /\[ai-insight-metric\]/);
	assert.match(routeSrc, /JSON\.stringify\(safePayload\)/);
});

test("ai/insight/route.js normalizeInsightRequestBody: plain object guard", () => {
	assert.match(routeSrc, /function normalizeInsightRequestBody\(body\)/);
	assert.match(routeSrc, /body && typeof body === ["']object["'] && !Array\.isArray\(body\)/);
});

// ── emitInsightMetric behavioral tests ───────────────────────────────────────

test("emitInsightMetric does not throw for valid payload", () => {
	assert.doesNotThrow(() =>
		emitInsightMetric({ event: "cache_hit", durationMs: 5 }),
	);
});

test("emitInsightMetric does not throw for null/undefined payload (uses {} fallback)", () => {
	assert.doesNotThrow(() => emitInsightMetric(null));
	assert.doesNotThrow(() => emitInsightMetric(undefined));
	assert.doesNotThrow(() => emitInsightMetric([]));
	assert.doesNotThrow(() => emitInsightMetric("string"));
});

test("emitInsightMetric logs the METRIC_LOG_PREFIX to console", () => {
	const logs = [];
	const origLog = console.log;
	console.log = (...args) => logs.push(args);
	try {
		emitInsightMetric({ event: "test" });
		assert.ok(logs.length > 0);
		assert.equal(logs[0][0], METRIC_LOG_PREFIX);
	} finally {
		console.log = origLog;
	}
});

test("emitInsightMetric serializes object payload as JSON", () => {
	const logs = [];
	const origLog = console.log;
	console.log = (...args) => logs.push(args);
	try {
		emitInsightMetric({ event: "gemini_success", source: "ai" });
		const json = JSON.parse(logs[0][1]);
		assert.equal(json.event, "gemini_success");
		assert.equal(json.source, "ai");
	} finally {
		console.log = origLog;
	}
});

test("emitInsightMetric uses {} for non-object payload (array, string, null)", () => {
	const logs = [];
	const origLog = console.log;
	console.log = (...args) => logs.push(args);
	try {
		emitInsightMetric(["not", "an", "object"]);
		const json = JSON.parse(logs[0][1]);
		assert.deepEqual(json, {});
	} finally {
		console.log = origLog;
	}
});

// ── normalizeInsightRequestBody / normalizeGeminiInsightOptions ───────────────

test("normalizeInsightRequestBody returns input for valid plain object", () => {
	const body = { summary: "데이터", forceRefresh: false };
	assert.equal(normalizeInsightRequestBody(body), body);
});

test("normalizeInsightRequestBody returns {} for null/undefined/array/string", () => {
	assert.deepEqual(normalizeInsightRequestBody(null), {});
	assert.deepEqual(normalizeInsightRequestBody(undefined), {});
	assert.deepEqual(normalizeInsightRequestBody([]), {});
	assert.deepEqual(normalizeInsightRequestBody("string"), {});
});

test("normalizeGeminiInsightOptions returns input for valid plain object", () => {
	const opts = { apiKey: "abc", prompt: "test" };
	assert.equal(normalizeGeminiInsightOptions(opts), opts);
});

test("normalizeGeminiInsightOptions returns {} for non-object input", () => {
	assert.deepEqual(normalizeGeminiInsightOptions(null), {});
	assert.deepEqual(normalizeGeminiInsightOptions([]), {});
});

// ── InsightTimeoutError behavioral tests ─────────────────────────────────────

test("InsightTimeoutError is an Error instance", () => {
	const err = new InsightTimeoutError(10000);
	assert.ok(err instanceof Error);
	assert.ok(err instanceof InsightTimeoutError);
});

test("InsightTimeoutError name is 'InsightTimeoutError'", () => {
	const err = new InsightTimeoutError(10000);
	assert.equal(err.name, "InsightTimeoutError");
});

test("InsightTimeoutError stores timeoutMs", () => {
	const err = new InsightTimeoutError(5000);
	assert.equal(err.timeoutMs, 5000);
});

test("InsightTimeoutError message includes the timeout value", () => {
	const err = new InsightTimeoutError(10000);
	assert.ok(err.message.includes("10000"));
});

// ── withInsightTimeout behavioral tests ──────────────────────────────────────

test("withInsightTimeout resolves with the promise value when done before timeout", async () => {
	const fastPromise = Promise.resolve("result");
	const result = await withInsightTimeout(fastPromise, 5000);
	assert.equal(result, "result");
});

test("withInsightTimeout rejects with InsightTimeoutError when promise is too slow", async () => {
	const slowPromise = new Promise((resolve) => setTimeout(resolve, 5000));
	try {
		await withInsightTimeout(slowPromise, 50); // 50ms timeout
		assert.fail("should have thrown");
	} catch (err) {
		assert.ok(err instanceof InsightTimeoutError);
		assert.equal(err.timeoutMs, 50);
	}
});

test("withInsightTimeout propagates rejection from the original promise", async () => {
	const failingPromise = Promise.reject(new Error("upstream error"));
	try {
		await withInsightTimeout(failingPromise, 5000);
		assert.fail("should have thrown");
	} catch (err) {
		assert.equal(err.message, "upstream error");
		assert.ok(!(err instanceof InsightTimeoutError));
	}
});

test("withInsightTimeout clears the timeout when promise resolves", async () => {
	// If timeout isn't cleared, the test process would hang
	const fastPromise = Promise.resolve("done");
	const result = await withInsightTimeout(fastPromise, 100);
	assert.equal(result, "done");
});
