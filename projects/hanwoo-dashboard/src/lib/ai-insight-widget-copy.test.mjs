import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

function readSource(relativePath) {
	return readFileSync(path.join(SRC_ROOT, relativePath), "utf8");
}

test("AIInsightWidget constants have correct values for timeout and messages", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");
	assert.match(source, /const AI_INSIGHT_TIMEOUT_MS = 12000;/);
	assert.match(source, /AI 분석 응답이 지연되어 기본 규칙 인사이트로 전환했습니다/);
	assert.match(source, /AI 분석 대신 기본 규칙 인사이트로 표시합니다/);
});

test("AIInsightWidget normalizeAIInsightBadgeOptions guards against non-object input", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");
	assert.match(source, /function normalizeAIInsightBadgeOptions\(options\) \{/);
	assert.match(source, /options && typeof options === ["']object["'] && !Array\.isArray\(options\)/);
});

test("AIInsightWidget formatCacheAgeLabel handles time thresholds", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");
	assert.match(source, /function formatCacheAgeLabel\(ageSeconds\) \{/);
	assert.match(source, /Number\.isFinite\(seconds\)/);
	assert.match(source, /방금 분석/);
	assert.match(source, /분 전 캐시/);
	assert.match(source, /시간 전 캐시/);
	assert.match(source, /오늘 분석 결과/);
});

test("AIInsightWidget deferAIInsightTask uses queueMicrotask with Promise fallback", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");
	assert.match(source, /function deferAIInsightTask\(callback\) \{/);
	assert.match(source, /queueMicrotask\(callback\)/);
	assert.match(source, /Promise\.resolve\(\)\.then\(callback\)/);
});

test("AIInsightWidget refresh button has accessible label and loading state", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");
	assert.match(source, /refreshButtonLabel/);
	assert.match(source, /AI 인사이트 새로고침 중/);
	assert.match(source, /AI 인사이트 새로고침/);
	assert.match(source, /aria-label=\{refreshButtonLabel\}/);
	assert.match(source, /title=\{refreshButtonLabel\}/);
});

test("AIInsightWidget non-premium path shows heuristic insights via deferAIInsightTask", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");
	assert.match(source, /if \(!isPremium\) \{/);
	assert.match(source, /deferAIInsightTask/);
	assert.match(source, /buildHeuristicInsights\(stableSummary\)/);
	assert.match(source, /규칙 기반 인사이트입니다\. 프리미엄 구독 시 AI 인사이트로 전환됩니다\./);
});

test("AIInsightWidget timeout fires fallback after AI_INSIGHT_TIMEOUT_MS", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");
	assert.match(source, /AI_INSIGHT_TIMEOUT_MS/);
	assert.match(source, /window\.setTimeout/);
	assert.match(source, /controller\.abort\(\)/);
	assert.match(source, /AI_INSIGHT_TIMEOUT_REASON/);
});

test("AIInsightWidget CacheBadge has data-testid for automated testing", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");
	assert.match(source, /data-testid="ai-insight-cache-badge"/);
	assert.match(source, /동일 농장 데이터에 대한 캐시된 AI 분석 결과입니다\./);
});
