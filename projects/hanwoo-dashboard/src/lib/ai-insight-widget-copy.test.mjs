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

test("AI insight widget normalizes malformed top-level props before rendering", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");

	assert.match(source, /function normalizeAIInsightWidgetOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === "object" && !Array\.isArray\(options\)/,
	);
	assert.match(source, /export default function AIInsightWidget\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ summary \} = normalizeAIInsightWidgetOptions\(options\);/,
	);
	assert.match(
		source,
		/\(\) =>\s+summary && typeof summary === "object" && !Array\.isArray\(summary\)\s+\? summary\s+:\s+\{\}/,
	);
	assert.doesNotMatch(source, /export default function AIInsightWidget\(\{ summary \}\)/);
});

test("AI insight badge helpers normalize malformed options before rendering", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");

	assert.match(source, /function normalizeAIInsightBadgeOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === "object" && !Array\.isArray\(options\)/,
	);
	assert.match(source, /function PriorityBadge\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ priority \} = normalizeAIInsightBadgeOptions\(options\);/,
	);
	assert.match(source, /function SourceBadge\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ source \} = normalizeAIInsightBadgeOptions\(options\);/,
	);
	assert.match(source, /function CacheBadge\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ ageSeconds \} = normalizeAIInsightBadgeOptions\(options\);/,
	);
	assert.match(
		source,
		/const style = PRIORITY_STYLE\[priority\] \?\? PRIORITY_STYLE\.medium;/,
	);
	assert.doesNotMatch(source, /function PriorityBadge\(\{ priority \}\)/);
	assert.doesNotMatch(source, /function SourceBadge\(\{ source \}\)/);
	assert.doesNotMatch(source, /function CacheBadge\(\{ ageSeconds \}\)/);
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
	assert.match(route, /function normalizeGeminiInsightOptions\(options\) \{/);
	assert.match(
		route,
		/options && typeof options === ["']object["'] && !Array\.isArray\(options\)/,
	);
	assert.match(route, /function normalizeInsightRequestBody\(body\) \{/);
	assert.match(
		route,
		/body && typeof body === ["']object["'] && !Array\.isArray\(body\)/,
	);
	assert.match(route, /async function callGeminiForInsights\(options = \{\}\) \{/);
	assert.match(
		route,
		/const \{ apiKey, prompt \} = normalizeGeminiInsightOptions\(options\);/,
	);
	assert.doesNotMatch(
		route,
		/async function callGeminiForInsights\(\{\s*apiKey,\s*prompt\s*\}\)/,
	);
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
	assert.match(route, /reject\(new InsightTimeoutError\(timeoutMs\)\);/);
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
		/const forceRefresh = refreshNonce > 0;\s+fetch\(["']\/api\/ai\/insight["'][\s\S]*?body: JSON\.stringify\(\{ summary: stableSummary, forceRefresh \}\)/,
	);
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

test("AI insight widget renders cache metadata only for cached AI responses", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");

	assert.match(source, /function formatCacheAgeLabel\(ageSeconds\) \{/);
	assert.match(source, /function CacheBadge\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ ageSeconds \} = normalizeAIInsightBadgeOptions\(options\);/,
	);
	assert.match(source, /data-testid="ai-insight-cache-badge"/);
	assert.match(source, /const \[cacheMeta,\s*setCacheMeta\] = useState\(null\)/);
	assert.match(source, /setCacheMeta\(null\)/);
	assert.match(source, /if \(payload\.cached === true\) \{/);
	assert.match(source, /const ageSeconds = Number\(payload\.ageSeconds\)/);
	assert.match(
		source,
		/setCacheMeta\(\{\s+cached: true,\s+ageSeconds: Number\.isFinite\(ageSeconds\) \? ageSeconds : 0,\s+\}\)/,
	);
	assert.match(source, /setCacheMeta\(\{ cached: false, ageSeconds: 0 \}\)/);
	assert.match(
		source,
		/source === "ai" && cacheMeta\?\.cached === true \?\s*\(\s*<CacheBadge ageSeconds=\{cacheMeta\.ageSeconds\} \/>/,
	);
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

	assert.match(source, /function deferAIInsightTask\(callback\) \{/);
	assert.match(
		source,
		/try \{\s+queueMicrotask\(callback\);\s+\} catch \{\s+Promise\.resolve\(\)\.then\(callback\);/,
	);
	assert.match(
		source,
		/deferAIInsightTask\(\(\) => \{[\s\S]*?setInsights\(buildHeuristicInsights\(stableSummary\)\)[\s\S]*?setSource\(["']heuristic["']\)[\s\S]*?setIsLoading\(true\)[\s\S]*?setReason\(null\)/,
	);
});

test("AI insight widget aborts in-flight requests on unmount/summary change", () => {
	const source = readSource("components/widgets/AIInsightWidget.js");

	assert.match(source, /let cancelled = false/);
	assert.match(
		source,
		/deferAIInsightTask\(\(\) => \{\s+if \(!cancelled && !controller\.signal\.aborted\) \{/,
	);
	assert.doesNotMatch(
		source,
		/queueMicrotask\(\(\) => \{\s+if \(!cancelled && !controller\.signal\.aborted\) \{/,
	);
	assert.match(
		source,
		/const payload = await res\.json\(\);\s+if \(cancelled \|\| controller\.signal\.aborted\) \{\s+return;\s+\}/,
	);
	assert.match(source, /\.catch\(\(error\) => \{\s+if \(cancelled\) return;/);
	assert.match(
		source,
		/if \(!cancelled && \(!controller\.signal\.aborted \|\| didTimeout\)\) \{\s+setIsLoading\(false\);/,
	);
	assert.match(
		source,
		/return\s*\(\)\s*=>\s*\{[\s\S]*?cancelled = true;[\s\S]*?controller\.abort\(\)/,
	);
	assert.doesNotMatch(source, /if \(!controller\.signal\.aborted\) \{\s+setInsights/);
	assert.doesNotMatch(
		source,
		/if \(!controller\.signal\.aborted \|\| didTimeout\) \{\s+setIsLoading\(false\);/,
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
	assert.match(source, /data-testid="ai-insight-refresh-button"/);
	assert.match(source, /className="[^"]*min-h-11 min-w-11[^"]*"/);
	assert.doesNotMatch(source, /className="[^"]*h-7 w-7[^"]*"/);
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
		/didTimeout = true;\s+controller\.abort\(\);/,
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

test("AI insight API route reuses same-day cached AI insights unless force refreshed", () => {
	const route = readSource("app/api/ai/insight/route.js");

	assert.match(route, /buildCacheKey/);
	assert.match(route, /loadCachedInsight/);
	assert.match(route, /dropCachedInsight/);
	assert.match(route, /saveCachedInsight/);
	assert.match(
		route,
		/const safeBody = normalizeInsightRequestBody\(body\);/,
	);
	assert.match(route, /const summary = safeBody\.summary \?\? null;/);
	assert.match(
		route,
		/const forceRefresh = Boolean\(safeBody\.forceRefresh === true\);/,
	);
	assert.match(route, /const userId =[\s\S]*?typeof session\.user\.id === "string"/);
	assert.match(
		route,
		/userId\s+\?\s+buildCacheKey\(\{ userId, summary \}\)\s+:\s+null/,
	);
	assert.match(route, /if \(cacheKey && !forceRefresh\) \{/);
	assert.match(route, /const hit = await loadCachedInsight\(cacheKey\)/);
	assert.match(
		route,
		/hit && Array\.isArray\(hit\.insights\) && hit\.insights\.length === MAX_INSIGHTS/,
	);
	assert.match(route, /cached:\s*true/);
	assert.match(route, /cachedAt:\s*new Date\(hit\.generatedAt\)\.toISOString\(\)/);
	assert.match(route, /ageSeconds:\s*hit\.ageSeconds/);
	assert.match(route, /cacheBackend:\s*hit\.backend \?\? ["']memory["']/);
	assert.match(
		route,
		/if \(cacheKey && forceRefresh\) \{\s+await dropCachedInsight\(cacheKey\);/,
	);
	assert.match(
		route,
		/await saveCachedInsight\(cacheKey, \{ insights: parsed, source: "ai" \}\)/,
	);
	assert.match(
		route,
		/return Response\.json\(\{ insights: parsed, source: "ai", cached: false \}\)/,
	);
	assert.match(route, /cached:\s*false/);
	assert.doesNotMatch(route, /const hit = getCachedInsight\(cacheKey\)/);
	assert.doesNotMatch(route, /clearCacheKey\(cacheKey\);/);
	assert.doesNotMatch(route, /setCachedInsight\(cacheKey, \{ insights: parsed, source: "ai" \}\)/);
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

test("AI insight API route emits structured metric logs on every return path", () => {
	const route = readSource("app/api/ai/insight/route.js");

	// Helper + prefix
	assert.match(route, /const METRIC_LOG_PREFIX = "\[ai-insight-metric\]"/);
	assert.match(route, /function emitInsightMetric\(payload\)/);
	assert.match(route, /console\.log\(METRIC_LOG_PREFIX, JSON\.stringify\(safePayload\)\)/);
	// emitInsightMetric must be wrapped in try/catch so logging failures can't break the route
	assert.match(
		route,
		/function emitInsightMetric\(payload\) \{\s+try \{[\s\S]*?\} catch \{\}\s*\}/,
	);

	// All 6 return-path event names present
	assert.match(route, /event:\s*"unauthenticated"/);
	assert.match(route, /event:\s*"heuristic_no_api_key"/);
	assert.match(route, /event:\s*"cache_hit"/);
	assert.match(route, /event:\s*"gemini_success"/);
	assert.match(route, /event:\s*"gemini_parse_failure"/);
	assert.match(route, /event:\s*"gemini_timeout"/);
	assert.match(route, /event:\s*"gemini_error"/);

	// Latency tracked from a single startedAt anchor at the top of POST
	assert.match(route, /const startedAt = Date\.now\(\)/);
	assert.match(route, /durationMs:\s*Date\.now\(\) - startedAt/);

	// Cache hit log surfaces backend + age so monitoring can split redis vs memory hit rate
	assert.match(
		route,
		/event:\s*"cache_hit"[\s\S]*?cacheBackend:[\s\S]*?ageSeconds:/,
	);

	// PII protection: metric payloads must NOT carry userId or summary contents.
	// We allow `hasUserId` (boolean) but reject any property literally named `userId:`
	// inside an emitInsightMetric(...) call.
	const metricBlocks = [...route.matchAll(/emitInsightMetric\(\{[\s\S]*?\}\)/g)].map(
		(match) => match[0],
	);
	assert.ok(metricBlocks.length >= 6, "expected at least 6 emitInsightMetric calls");
	for (const block of metricBlocks) {
		assert.doesNotMatch(
			block,
			/\buserId:/,
			`metric payload must not include userId (PII): ${block}`,
		);
		assert.doesNotMatch(
			block,
			/\bsummary:/,
			`metric payload must not include summary (PII): ${block}`,
		);
	}
});
