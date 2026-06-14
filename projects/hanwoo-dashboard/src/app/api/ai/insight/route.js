import { GoogleGenerativeAI } from "@google/generative-ai";

// Allow up to 60 s on Vercel Pro — the internal GEMINI_INSIGHT_TIMEOUT_MS guard
// (10 s) fires first; without maxDuration the platform kills at 10 s default
// before the heuristic fallback path can complete.
export const maxDuration = 60;

import {
	buildCacheKey,
	dropCachedInsight,
	loadCachedInsight,
	saveCachedInsight,
} from "@/lib/ai-insight-cache.mjs";
import {
	MAX_INSIGHTS,
	buildHeuristicInsights,
	buildInsightPrompt,
	parseInsightResponse,
} from "@/lib/ai-insight.mjs";
import { requireAuthenticatedSession } from "@/lib/auth-guard";
import { checkRateLimit } from "@/lib/rate-limit.mjs";
import { getSubscriptionStatus } from "@/lib/subscription-queries";

const SYSTEM_INSTRUCTION = `
당신은 한우 농가 운영자에게 매일 3개의 우선순위 행동을 권하는 Joolife AI 분석가입니다.
한국어로 응답하고, 제공된 농장 스냅샷 정보를 근거로 행동 가능한 인사이트를 주세요.
출력은 반드시 길이 3의 JSON 배열만이며, 각 원소는 title/body/priority 키를 가져야 합니다.
priority는 "high" | "medium" | "low" 중 하나로, 농장 정보 기반 위급도에 따라 결정해 주세요.
응급 질병이나 수의학 상황은 전문 수의사 상담 안내를 포함해 주세요.
`.trim();

const DEFAULT_HEURISTIC_REASON =
	"AI 분석 키가 설정되지 않아 기본 규칙 인사이트를 표시합니다.";

const METRIC_LOG_PREFIX = "[ai-insight-metric]";

/**
 * T-1199: structured 한 줄 JSON 메트릭 로그.
 * Vercel/CloudWatch 같은 로그 수집기에서 prefix 로 grep 해 hit rate / latency 추출.
 * PII 차단을 위해 userId / summary 내용은 절대 로그하지 않는다 (hasUserId 플래그만).
 * 로그 실패는 swallow — 절대 라우트 응답을 깨면 안 된다.
 */
function emitInsightMetric(payload) {
	try {
		const safePayload =
			payload && typeof payload === "object" && !Array.isArray(payload)
				? payload
				: {};
		console.log(METRIC_LOG_PREFIX, JSON.stringify(safePayload));
	} catch {}
}

const GEMINI_INSIGHT_TIMEOUT_MS = 10000;
const GEMINI_TIMEOUT_REASON =
	"AI 분석 응답이 지연되어 기본 규칙 인사이트로 전환했습니다.";

class InsightTimeoutError extends Error {
	constructor(timeoutMs) {
		super(`AI insight generation timed out after ${timeoutMs}ms.`);
		this.name = "InsightTimeoutError";
		this.timeoutMs = timeoutMs;
	}
}

async function readJsonBody(request) {
	try {
		return await request.json();
	} catch {
		return null;
	}
}

function normalizeGeminiInsightOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeInsightRequestBody(body) {
	return body && typeof body === "object" && !Array.isArray(body) ? body : {};
}

async function callGeminiForInsights(options = {}) {
	const { apiKey, prompt } = normalizeGeminiInsightOptions(options);
	const genAI = new GoogleGenerativeAI(apiKey);
	const model = genAI.getGenerativeModel({
		model: "gemini-2.0-flash",
		systemInstruction: SYSTEM_INSTRUCTION,
		generationConfig: {
			responseMimeType: "application/json",
			temperature: 0.4,
		},
	});
	const result = await model.generateContent(prompt);
	const response = await result.response;
	return response.text();
}

function withInsightTimeout(promise, timeoutMs = GEMINI_INSIGHT_TIMEOUT_MS) {
	let timeoutId = null;
	const timeoutPromise = new Promise((_, reject) => {
		try {
			timeoutId = setTimeout(
				() => reject(new InsightTimeoutError(timeoutMs)),
				timeoutMs,
			);
		} catch (error) {
			console.error("AI insight timeout scheduling failed:", error);
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

export async function POST(request) {
	const startedAt = Date.now();
	let session = null;
	try {
		session = await requireAuthenticatedSession();
	} catch {
		emitInsightMetric({
			event: "unauthenticated",
			durationMs: Date.now() - startedAt,
		});
		return Response.json(
			{ error: "인증이 필요합니다.", code: "UNAUTHENTICATED" },
			{ status: 401 },
		);
	}
	if (!session) {
		emitInsightMetric({
			event: "unauthenticated",
			durationMs: Date.now() - startedAt,
		});
		return Response.json(
			{ error: "인증이 필요합니다.", code: "UNAUTHENTICATED" },
			{ status: 401 },
		);
	}

	const subscriptionStatus = await getSubscriptionStatus(session.user?.id).catch(
		() => ({ status: "INACTIVE" }),
	);
	if (subscriptionStatus.status === "INACTIVE") {
		emitInsightMetric({
			event: "subscription_required",
			durationMs: Date.now() - startedAt,
		});
		return Response.json(
			{ error: "프리미엄 구독이 필요한 기능입니다.", code: "SUBSCRIPTION_REQUIRED" },
			{ status: 403 },
		);
	}

	const userId =
		session && session.user && typeof session.user.id === "string"
			? session.user.id
			: null;

	if (userId) {
		const rateResult = checkRateLimit(`ai-insight:${userId}`, { maxRequests: 20, windowMs: 3600000 });
		if (!rateResult.allowed) {
			emitInsightMetric({ event: "rate_limited", durationMs: Date.now() - startedAt });
			return Response.json(
				{ error: "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.", code: "RATE_LIMITED" },
				{ status: 429, headers: { "Retry-After": String(rateResult.retryAfterSeconds ?? 3600) } },
			);
		}
	}

	const body = await readJsonBody(request);
	const safeBody = normalizeInsightRequestBody(body);
	const summary = safeBody.summary ?? null;
	const forceRefresh = Boolean(safeBody.forceRefresh === true);

	const apiKey = process.env.GEMINI_API_KEY;
	if (!apiKey) {
		emitInsightMetric({
			event: "heuristic_no_api_key",
			source: "heuristic",
			forceRefresh,
			durationMs: Date.now() - startedAt,
		});
		return Response.json({
			insights: buildHeuristicInsights(summary),
			source: "heuristic",
			reason: DEFAULT_HEURISTIC_REASON,
			cached: false,
		});
	}

	const hasUserId = userId !== null;
	const cacheKey = userId
		? buildCacheKey({ userId, summary })
		: null;

	if (cacheKey && !forceRefresh) {
		const hit = await loadCachedInsight(cacheKey);
		if (hit && Array.isArray(hit.insights) && hit.insights.length === MAX_INSIGHTS) {
			emitInsightMetric({
				event: "cache_hit",
				source: "ai",
				cacheBackend: hit.backend ?? "memory",
				ageSeconds: hit.ageSeconds,
				hasUserId,
				durationMs: Date.now() - startedAt,
			});
			return Response.json({
				insights: hit.insights,
				source: "ai",
				cached: true,
				cachedAt: new Date(hit.generatedAt).toISOString(),
				ageSeconds: hit.ageSeconds,
				cacheBackend: hit.backend ?? "memory",
			});
		}
	}

	if (cacheKey && forceRefresh) {
		await dropCachedInsight(cacheKey);
	}

	const prompt = buildInsightPrompt(summary);
	try {
		const raw = await withInsightTimeout(
			callGeminiForInsights({ apiKey, prompt }),
		);
		const parsed = parseInsightResponse(raw);
		if (!parsed || parsed.length !== MAX_INSIGHTS) {
			emitInsightMetric({
				event: "gemini_parse_failure",
				source: "heuristic",
				forceRefresh,
				hasUserId,
				durationMs: Date.now() - startedAt,
			});
			return Response.json({
				insights: buildHeuristicInsights(summary),
				source: "heuristic",
				reason: "AI 응답을 해석하지 못해 기본 규칙으로 대체했습니다.",
				cached: false,
			});
		}
		if (cacheKey) {
			await saveCachedInsight(cacheKey, { insights: parsed, source: "ai" });
		}
		emitInsightMetric({
			event: "gemini_success",
			source: "ai",
			forceRefresh,
			hasUserId,
			cached: false,
			durationMs: Date.now() - startedAt,
		});
		return Response.json({ insights: parsed, source: "ai", cached: false });
	} catch (error) {
		if (error instanceof InsightTimeoutError) {
			console.error("AI insight generation timed out:", error);
			emitInsightMetric({
				event: "gemini_timeout",
				source: "heuristic",
				forceRefresh,
				hasUserId,
				timeoutMs: error.timeoutMs ?? GEMINI_INSIGHT_TIMEOUT_MS,
				durationMs: Date.now() - startedAt,
			});
			return Response.json({
				insights: buildHeuristicInsights(summary),
				source: "heuristic",
				reason: GEMINI_TIMEOUT_REASON,
				cached: false,
			});
		}
		console.error("AI 인사이트 생성 실패:", error);
		emitInsightMetric({
			event: "gemini_error",
			source: "heuristic",
			forceRefresh,
			hasUserId,
			errorName: error?.name ?? "Unknown",
			durationMs: Date.now() - startedAt,
		});
		return Response.json({
			insights: buildHeuristicInsights(summary),
			source: "heuristic",
			reason: "AI 분석 호출 중 오류가 발생해 기본 규칙으로 대체했습니다.",
			cached: false,
		});
	}
}
