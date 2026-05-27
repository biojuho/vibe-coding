/**
 * AI 인사이트 일일 캐시 — 사용자별 + 농장 요약 해시별 + Asia/Seoul 날짜별로
 * Gemini 응답을 in-memory에 보관해 같은 입력의 중복 LLM 호출을 막는다.
 *
 * 단일 프로세스(Map) 기준의 best-effort 캐시이며, 다중 인스턴스 배포에서는
 * 인스턴스별로 독립이다. 휴리스틱 응답은 결정론적이므로 캐싱하지 않는다.
 */

import { createHash } from "node:crypto";

const KOREA_TIME_ZONE = "Asia/Seoul";
const DEFAULT_MAX_ENTRIES = 256;

const dayKeyFormatter = new Intl.DateTimeFormat("en-CA", {
	timeZone: KOREA_TIME_ZONE,
	year: "numeric",
	month: "2-digit",
	day: "2-digit",
});

export function buildDayKey(date = new Date()) {
	const safeDate =
		date instanceof Date && !Number.isNaN(date.getTime()) ? date : new Date();
	return dayKeyFormatter.format(safeDate);
}

function isPlainObject(value) {
	return (
		value !== null &&
		typeof value === "object" &&
		!Array.isArray(value)
	);
}

function toSafeTimestamp(value) {
	const timestamp = typeof value === "number" ? value : Number(value);
	return Number.isFinite(timestamp) ? timestamp : Date.now();
}

function toSafeMaxEntries(value) {
	const entries = typeof value === "number" ? value : Number(value);
	return Number.isInteger(entries) && entries > 0 ? entries : DEFAULT_MAX_ENTRIES;
}

function stableStringify(value, seen = new WeakSet()) {
	if (value === null || value === undefined) {
		return "null";
	}
	if (typeof value !== "object") {
		return JSON.stringify(value) ?? "null";
	}
	if (seen.has(value)) return "\"[Circular]\"";
	seen.add(value);
	if (Array.isArray(value)) {
		return `[${value.map((item) => stableStringify(item, seen)).join(",")}]`;
	}
	const keys = Object.keys(value).sort();
	const entries = keys.map(
		(key) => `${JSON.stringify(key)}:${stableStringify(value[key], seen)}`,
	);
	return `{${entries.join(",")}}`;
}

export function summaryHash(summary) {
	const canonical = stableStringify(summary ?? null);
	return createHash("sha256").update(canonical).digest("hex").slice(0, 16);
}

export function buildCacheKey(input = {}) {
	const safeInput = isPlainObject(input) ? input : {};
	const { userId, summary, dayKey } = safeInput;
	const safeUserId =
		typeof userId === "string" && userId.trim().length > 0
			? userId.trim()
			: "anon";
	const safeDay =
		typeof dayKey === "string" && dayKey.trim().length > 0
			? dayKey.trim()
			: buildDayKey();
	return `${safeUserId}:${safeDay}:${summaryHash(summary)}`;
}

const cacheStore = new Map();

function pruneCacheStore(maxEntries = DEFAULT_MAX_ENTRIES) {
	const safeMaxEntries = toSafeMaxEntries(maxEntries);
	if (cacheStore.size <= safeMaxEntries) return;
	const overflow = cacheStore.size - safeMaxEntries;
	const iterator = cacheStore.keys();
	for (let i = 0; i < overflow; i += 1) {
		const oldest = iterator.next().value;
		if (oldest === undefined) break;
		cacheStore.delete(oldest);
	}
}

export function getCachedInsight(key, now = Date.now()) {
	if (typeof key !== "string" || key.length === 0) return null;
	const entry = cacheStore.get(key);
	if (!entry) return null;
	const safeNow = toSafeTimestamp(now);
	const safeGeneratedAt = toSafeTimestamp(entry.generatedAt);
	return {
		insights: entry.insights,
		source: entry.source,
		reason: entry.reason ?? null,
		generatedAt: safeGeneratedAt,
		ageSeconds: Math.max(0, Math.floor((safeNow - safeGeneratedAt) / 1000)),
	};
}

export function setCachedInsight(
	key,
	value,
	now = Date.now(),
	options = {},
) {
	if (typeof key !== "string" || key.length === 0) return null;
	if (!value || typeof value !== "object") return null;
	if (!Array.isArray(value.insights)) return null;
	if (value.source !== "ai") return null;
	const safeOptions = isPlainObject(options) ? options : {};
	const safeNow = toSafeTimestamp(now);
	cacheStore.set(key, {
		insights: value.insights,
		source: "ai",
		reason: typeof value.reason === "string" ? value.reason : null,
		generatedAt: safeNow,
	});
	pruneCacheStore(safeOptions.maxEntries);
	return getCachedInsight(key, safeNow);
}

export function clearCacheKey(key) {
	if (typeof key !== "string" || key.length === 0) return false;
	return cacheStore.delete(key);
}

export function resetCacheStoreForTests() {
	cacheStore.clear();
}

export function cacheSizeForTests() {
	return cacheStore.size;
}

export const __INTERNAL__ = {
	DEFAULT_MAX_ENTRIES,
	KOREA_TIME_ZONE,
};
