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

test("AI insight widget exposes Korean copy and accessibility landmarks", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");

	assert.match(source, /오늘의 AI 인사이트/);
	assert.match(source, /농장 기록을 기반으로 우선순위 3가지 행동을 정리/);
	assert.doesNotMatch(source, /농장 데이터를 기반으로 우선순위 3가지 행동을 정리/);
	assert.doesNotMatch(source, /우선순위 3가지 행동을 제안/);
	assert.match(source, /aria-label="AI 인사이트 목록"/);
	assert.match(source, /aria-busy=\{isLoading\}/);
	assert.match(source, /aria-live="polite"/);
	assert.match(source, /aria-relevant="additions text"/);
	assert.match(
		source,
		/role="status"[\s\S]*?aria-live="polite"[\s\S]*?aria-atomic="true"[\s\S]*?aria-busy=\{isLoading\}[\s\S]*?>[\s\S]*?AI 인사이트 분석 중…/,
	);
	assert.match(source, /aria-hidden="true"/);
	assert.match(source, /buildHeuristicInsights/);
	assert.match(source, /parseInsightResponse/);
});

test("AI insight API route bounds slow Gemini calls with a deterministic fallback", () => {
	const route = readSource("app/api/ai/insight/route.js");

	assert.match(route, /GEMINI_INSIGHT_TIMEOUT_MS\s*=\s*10000/);
	assert.match(route, /제공된 농장 스냅샷 정보를 근거로/);
	assert.match(route, /농장 정보 기반 위급도/);
	assert.match(route, /위급도에 따라 결정해 주세요/);
	assert.match(route, /전문 수의사 상담 안내를 포함해 주세요/);
	assert.doesNotMatch(route, /농장 스냅샷 데이터를 근거로/);
	assert.doesNotMatch(route, /데이터 기반 위급도/);
	assert.doesNotMatch(route, /위급도로 결정하세요/);
	assert.doesNotMatch(route, /전문 수의사 상담 안내를 포함하세요/);
	assert.match(route, /class InsightTimeoutError extends Error/);
	assert.match(route, /function withInsightTimeout/);
	assert.match(route, /Promise\.race\(\[promise,\s*timeoutPromise\]\)/);
	assert.match(
		route,
		/try \{\s+timeoutId = setTimeout\(\s+\(\) => reject\(new InsightTimeoutError\(timeoutMs\)\),\s+timeoutMs,\s+\);\s+\} catch \(error\) \{/,
	);
	assert.match(
		route,
		/console\.error\("AI insight timeout scheduling failed:", error\);/,
	);
	assert.match(
		route,
		/if \(timeoutId !== null\) \{\s+try \{\s+clearTimeout\(timeoutId\);\s+\} catch \{\}/,
	);
	assert.doesNotMatch(route, /timeoutId = setTimeout\(\s+\(\) => reject\(new InsightTimeoutError\(timeoutMs\)\),\s+timeoutMs,\s+\);\s+\}\);/);
	assert.doesNotMatch(route, /if \(timeoutId\) \{\s+clearTimeout\(timeoutId\);/);
	assert.match(route, /withInsightTimeout\(\s*callGeminiForInsights/);
	assert.match(route, /reason:\s*GEMINI_TIMEOUT_REASON/);
	assert.match(
		route,
		/try\s*\{[\s\S]*?withInsightTimeout\([\s\S]*?\}\s*catch\s*\(\s*error\s*\)\s*\{[\s\S]*?error instanceof InsightTimeoutError[\s\S]*?reason:\s*GEMINI_TIMEOUT_REASON/,
	);
	const authCatch = route.match(
		/session = await requireAuthenticatedSession\(\);\s*\}\s*catch\s*(?:\(\s*error\s*\))?\s*\{([\s\S]*?)\n\t\}/,
	);
	assert.ok(authCatch, "auth catch block should be present");
	assert.doesNotMatch(authCatch[1], /InsightTimeoutError/);
	assert.doesNotMatch(authCatch[1], /buildHeuristicInsights\(summary\)/);
});

test("AI insight widget calls /api/ai/insight and falls back to heuristics", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");

	assert.match(source, /fetch\(["']\/api\/ai\/insight["']/);
	assert.match(source, /method:\s*["']POST["']/);
	assert.match(
		source,
		/setInsights\(buildHeuristicInsights\(stableSummary\)\)/,
	);
	assert.match(source, /MAX_INSIGHTS/);
	assert.match(source, /!parsed \|\| parsed\.length !== MAX_INSIGHTS/);
	assert.match(source, /setSource\(["']heuristic["']\)/);
	assert.match(source, /signal: controller\.signal/);
	assert.match(source, /AbortController\(\)/);
});

test("AI insight widget normalizes heuristic reasons and clears stale AI reasons", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");

	assert.match(source, /AI_INSIGHT_HEURISTIC_REASON/);
	assert.match(source, /const nextSource = payload\.source === ["']ai["'] \? ["']ai["'] : ["']heuristic["']/);
	assert.match(source, /if \(nextSource === ["']heuristic["']\)/);
	assert.match(source, /payload\.reason\.trim\(\)\.length > 0/);
	assert.match(source, /: AI_INSIGHT_HEURISTIC_REASON/);
	assert.match(source, /setReason\(null\)/);
});

test("AI insight widget resets visible fallback cards when the summary changes", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");

	assert.match(
		source,
		/queueMicrotask\(\(\) => \{[\s\S]*?setInsights\(buildHeuristicInsights\(stableSummary\)\)[\s\S]*?setSource\(["']heuristic["']\)[\s\S]*?setIsLoading\(true\)[\s\S]*?setReason\(null\)/,
	);
});

test("AI insight widget aborts in-flight requests on unmount/summary change", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");

	assert.match(
		source,
		/return\s*\(\)\s*=>\s*\{[\s\S]*?controller\.abort\(\)/,
	);
	assert.doesNotMatch(source, /if\s*\(\s*error\.name\s*===\s*["']AbortError["']\s*\)\s*throw/);
});

test("AI insight widget exposes a busy-safe manual refresh control", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");

	assert.match(source, /RefreshCw/);
	assert.match(source, /const \[refreshNonce,\s*setRefreshNonce\]/);
	assert.match(source, /\[stableSummary,\s*refreshNonce\]/);
	assert.match(source, /onClick=\{\(\) => setRefreshNonce\(\(current\) => current \+ 1\)\}/);
	assert.match(source, /disabled=\{isLoading\}/);
	assert.match(source, /aria-busy=\{isLoading\}/);
	assert.match(source, /aria-label=\{refreshButtonLabel\}/);
	assert.match(source, /title=\{refreshButtonLabel\}/);
	assert.match(source, /aria-hidden="true"/);
	assert.doesNotMatch(source, /aria-label="Refresh"/);
});

test("AI insight widget bounds slow requests and announces fallback reasons", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");

	assert.match(source, /AI_INSIGHT_TIMEOUT_MS\s*=\s*12000/);
	assert.match(source, /AI_INSIGHT_TIMEOUT_REASON/);
	assert.match(source, /let didTimeout = false/);
	assert.match(source, /let timeoutId = null;/);
	assert.match(
		source,
		/try \{\s+timeoutId = window\.setTimeout\(\(\) => \{\s*didTimeout = true;\s*controller\.abort\(\);/,
	);
	assert.match(
		source,
		/console\.error\("Failed to schedule AI insight timeout:", error\);/,
	);
	assert.match(
		source,
		/if \(timeoutId !== null\) \{\s+try \{\s+window\.clearTimeout\(timeoutId\);\s+\} catch \{\}/,
	);
	assert.match(source, /error\.name === ["']AbortError["'] && !didTimeout/);
	assert.match(source, /setReason\(AI_INSIGHT_TIMEOUT_REASON\)/);
	assert.match(source, /role="status"/);
	assert.match(source, /aria-live="polite"/);
	assert.match(source, /aria-atomic="true"/);
	assert.doesNotMatch(source, /const timeoutId = window\.setTimeout/);
	assert.doesNotMatch(source, /finally\(\(\) => \{\s+window\.clearTimeout\(timeoutId\);/);
});

test("AI insight widget is registered, wired into DashboardClient, and supports REST POST", () => {
	const widgetSettings = readSource("lib/hooks/useWidgetSettings.js");
	const dashboard = readSource("components/DashboardClient.js");
	const route = readSource("app/api/ai/insight/route.js");

	assert.match(
		widgetSettings,
		/id:\s*["']aiInsight["'][\s\S]*?label:\s*["']AI 인사이트["'][\s\S]*?icon:\s*["']🤖["'][\s\S]*?defaultOn:\s*false[\s\S]*?description:\s*["']켜면 농장 요약 정보를 AI 분석 API로 전송합니다\.["']/,
	);
	assert.doesNotMatch(widgetSettings, /농장 요약 데이터를 AI 분석 API로 전송/);
	assert.match(
		dashboard,
		/const AIInsightWidget = dynamic\(\s*\(\)\s*=>\s*import\(["']@\/components\/widgets\/AIInsightWidget["']\)/,
	);
	assert.match(dashboard, /widgetSettings\.visible\.aiInsight/);
	assert.match(dashboard, /<AIInsightWidget/);
	assert.match(dashboard, /const aiInsightSummary = useMemo\(/);
	assert.match(dashboard, /<AIInsightWidget summary=\{aiInsightSummary\} \/>/);
	assert.doesNotMatch(dashboard, /<AIInsightWidget\s+summary=\{\{/);
	assert.match(route, /export async function POST/);
	assert.match(route, /requireAuthenticatedSession/);
	assert.match(route, /buildHeuristicInsights/);
	assert.match(route, /parseInsightResponse/);
	assert.match(route, /MAX_INSIGHTS/);
	assert.match(route, /!parsed \|\| parsed\.length !== MAX_INSIGHTS/);
});

test("AI insight API route surfaces Korean fallback reasons and never throws to the client", () => {
	const route = readSource("app/api/ai/insight/route.js");

	assert.match(route, /AI 분석 키가 설정되지 않아/);
	assert.match(route, /AI 응답을 해석하지 못해/);
	assert.match(route, /AI 분석 호출 중 오류가 발생해/);
	assert.match(route, /source:\s*["']ai["']/);
	assert.match(route, /source:\s*["']heuristic["']/);
	assert.match(route, /catch\s*\(\s*error\s*\)/);
});
