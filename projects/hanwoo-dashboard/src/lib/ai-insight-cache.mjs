/**
 * AI 인사이트 일일 캐시 — 사용자별 + 농장 요약 해시별 + Asia/Seoul 날짜별로
 * Gemini 응답을 보관해 같은 입력의 중복 LLM 호출을 막는다.
 *
 * 백킹 스토어:
 * - REDIS_URL 이 설정된 경우: Redis (`ai-insight:<key>` 24h TTL) — 다중 인스턴스 hit.
 * - 그렇지 않으면: in-memory Map — 단일 프로세스 best-effort.
 * 휴리스틱 응답은 결정론적이므로 어느 쪽에서도 캐싱하지 않는다.
 *
 * Sync API (getCachedInsight/setCachedInsight) 는 in-memory 만 다룬다 (기존 테스트 호환).
 * Route 등 신규 호출자는 Redis-aware async API (loadCachedInsight/saveCachedInsight) 사용.
 */

import { createHash } from "node:crypto";

import { ensureRedisConnection, isRedisConfigured } from "./redis.js";

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

const REDIS_KEY_PREFIX = "ai-insight:";
const REDIS_TTL_SECONDS = 24 * 60 * 60;

function toRedisKey(key) {
	return `${REDIS_KEY_PREFIX}${key}`;
}

async function readFromRedis(key, now) {
	try {
		const redis = await ensureRedisConnection("cache");
		if (!redis) return null;
		const raw = await redis.get(toRedisKey(key));
		if (!raw) return null;
		const parsed = JSON.parse(raw);
		if (!parsed || typeof parsed !== "object") return null;
		if (!Array.isArray(parsed.insights)) return null;
		if (parsed.source !== "ai") return null;
		const safeNow = toSafeTimestamp(now);
		const safeGeneratedAt = toSafeTimestamp(parsed.generatedAt);
		return {
			insights: parsed.insights,
			source: "ai",
			reason: typeof parsed.reason === "string" ? parsed.reason : null,
			generatedAt: safeGeneratedAt,
			ageSeconds: Math.max(0, Math.floor((safeNow - safeGeneratedAt) / 1000)),
		};
	} catch (error) {
		console.error("[ai-insight-cache] redis read failed:", error);
		return null;
	}
}

async function writeToRedis(key, value, now) {
	try {
		const redis = await ensureRedisConnection("cache");
		if (!redis) return null;
		const safeNow = toSafeTimestamp(now);
		const payload = {
			insights: value.insights,
			source: "ai",
			reason: typeof value.reason === "string" ? value.reason : null,
			generatedAt: safeNow,
		};
		await redis.set(
			toRedisKey(key),
			JSON.stringify(payload),
			"EX",
			REDIS_TTL_SECONDS,
		);
		return {
			...payload,
			ageSeconds: 0,
		};
	} catch (error) {
		console.error("[ai-insight-cache] redis write failed:", error);
		return null;
	}
}

async function deleteFromRedis(key) {
	try {
		const redis = await ensureRedisConnection("cache");
		if (!redis) return false;
		const removed = await redis.del(toRedisKey(key));
		return removed > 0;
	} catch (error) {
		console.error("[ai-insight-cache] redis delete failed:", error);
		return false;
	}
}

/**
 * Redis 가 있으면 Redis, 없으면 in-memory Map 에서 캐시 조회.
 * route.js 등 신규 호출자가 사용하는 단일 엔트리.
 */
export async function loadCachedInsight(key, now = Date.now()) {
	if (typeof key !== "string" || key.length === 0) return null;
	if (isRedisConfigured()) {
		const hit = await readFromRedis(key, now);
		if (hit) return { ...hit, backend: "redis" };
		return null;
	}
	const memHit = getCachedInsight(key, now);
	return memHit ? { ...memHit, backend: "memory" } : null;
}

/**
 * Redis 가 있으면 Redis 에도 저장(24h TTL), 없으면 in-memory Map 에만 저장.
 * AI source 가 아닌 응답은 무시.
 */
export async function saveCachedInsight(key, value, now = Date.now()) {
	if (typeof key !== "string" || key.length === 0) return null;
	if (!value || typeof value !== "object") return null;
	if (!Array.isArray(value.insights)) return null;
	if (value.source !== "ai") return null;
	if (isRedisConfigured()) {
		const stored = await writeToRedis(key, value, now);
		return stored ? { ...stored, backend: "redis" } : null;
	}
	const stored = setCachedInsight(key, value, now);
	return stored ? { ...stored, backend: "memory" } : null;
}

/**
 * forceRefresh 경로에서 호출. Redis 가 있으면 Redis 키 삭제, 없으면 Map.
 */
export async function dropCachedInsight(key) {
	if (typeof key !== "string" || key.length === 0) return false;
	if (isRedisConfigured()) {
		return deleteFromRedis(key);
	}
	return clearCacheKey(key);
}

export function cacheSizeForTests() {
	return cacheStore.size;
}

export const __INTERNAL__ = {
	DEFAULT_MAX_ENTRIES,
	KOREA_TIME_ZONE,
};
