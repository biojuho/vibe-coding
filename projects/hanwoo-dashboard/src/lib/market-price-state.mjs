export const MARKET_PRICE_FRESH_TTL_MS = 60 * 60 * 1000;
export const MARKET_PRICE_UNAVAILABLE_MESSAGE =
	"지금은 한우 시세 정보를 확인할 수 없습니다. 잠시 후 다시 시도해 주세요.";

function parseStrictDateKey(value) {
	const parsed = new Date(`${value}T00:00:00.000Z`);
	return Number.isFinite(parsed.getTime()) &&
		parsed.toISOString().slice(0, 10) === value
		? parsed
		: null;
}

function toValidDate(value) {
	if (value instanceof Date && Number.isFinite(value.getTime())) {
		return value;
	}

	if (typeof value === "string" && /^\d{8}$/.test(value)) {
		const normalized = `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`;
		return parseStrictDateKey(normalized);
	}

	if (typeof value === "string" && /^\d{4}\.\d{2}\.\d{2}$/.test(value)) {
		return parseStrictDateKey(value.replace(/\./g, "-"));
	}

	if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
		return parseStrictDateKey(value);
	}

	if (!value) {
		return null;
	}

	const parsed = new Date(value);
	return Number.isFinite(parsed.getTime()) ? parsed : null;
}

function toIssueDateKey(value, fallbackNow) {
	const date = toValidDate(value) ?? fallbackNow;
	return date.toISOString().slice(0, 10);
}

function toDisplayDate(issueDateKey) {
	return issueDateKey.replace(/-/g, ".");
}

function normalizePriceSide(side) {
	if (!side || typeof side !== "object" || Array.isArray(side)) {
		return null;
	}

	const normalized = {
		grade1pp: Number(side.grade1pp),
		grade1p: Number(side.grade1p),
		grade1: Number(side.grade1),
	};

	if (
		Object.values(normalized).some(
			(value) => !Number.isFinite(value) || value <= 0,
		)
	) {
		return null;
	}

	return normalized;
}

function normalizeOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function createAvailableMarketPrice(options = {}) {
	const {
		bull,
		cow,
		fetchedAt,
		issueDate,
		source,
		sourceLabel,
		degraded,
		isRealtime,
		isStale,
		message = null,
	} = normalizeOptions(options);
	return {
		available: true,
		degraded,
		isRealtime,
		isStale,
		source,
		sourceLabel,
		message,
		fetchedAt: fetchedAt.toISOString(),
		issueDate,
		date: toDisplayDate(issueDate),
		bull,
		cow,
	};
}

export function normalizeCachedMarketPrice(snapshot, options = {}) {
	if (
		!snapshot ||
		typeof snapshot !== "object" ||
		Array.isArray(snapshot) ||
		snapshot.isRealtime !== true
	) {
		return null;
	}

	const safeOptions = normalizeOptions(options);

	const bull = normalizePriceSide({
		grade1pp: snapshot.bullGrade1pp,
		grade1p: snapshot.bullGrade1p,
		grade1: snapshot.bullGrade1,
	});
	const cow = normalizePriceSide({
		grade1pp: snapshot.cowGrade1pp,
		grade1p: snapshot.cowGrade1p,
		grade1: snapshot.cowGrade1,
	});

	if (!bull || !cow) {
		return null;
	}

	const now = safeOptions.now ?? new Date();
	const freshnessMs = safeOptions.freshnessMs ?? MARKET_PRICE_FRESH_TTL_MS;
	const fetchedAt = toValidDate(snapshot.fetchedAt) ?? now;
	const ageMs = now.getTime() - fetchedAt.getTime();
	const isStale = ageMs >= freshnessMs;
	const issueDate = toIssueDateKey(snapshot.issueDate, now);

	return createAvailableMarketPrice({
		bull,
		cow,
		fetchedAt,
		issueDate,
		source: isStale ? "cache-stale" : "kape-cache",
		sourceLabel: isStale ? "이전 저장값" : "저장된 KAPE",
		degraded: isStale,
		isRealtime: !isStale,
		isStale,
		message: isStale
			? "최신 시세를 불러오지 못해 마지막으로 확인한 KAPE 시세를 표시합니다."
			: null,
	});
}

export function normalizeLiveMarketPrice(payload, options = {}) {
	if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
		return null;
	}

	const safeOptions = normalizeOptions(options);

	const bull = normalizePriceSide(payload.bull);
	const cow = normalizePriceSide(payload.cow);

	if (!bull || !cow) {
		return null;
	}

	const now = safeOptions.now ?? new Date();
	const fetchedAt = toValidDate(payload.fetchedAt) ?? now;
	const issueDate = toIssueDateKey(payload.issueDate ?? payload.date, now);

	return createAvailableMarketPrice({
		bull,
		cow,
		fetchedAt,
		issueDate,
		source: "kape-live",
		sourceLabel: "실시간 KAPE",
		degraded: false,
		isRealtime: true,
		isStale: false,
	});
}

export function buildUnavailableMarketPrice(options = {}) {
	const safeOptions = normalizeOptions(options);
	const now = safeOptions.now ?? new Date();

	return {
		available: false,
		degraded: true,
		isRealtime: false,
		isStale: true,
		source: "unavailable",
		sourceLabel: "시세 확인 불가",
		message: safeOptions.message ?? MARKET_PRICE_UNAVAILABLE_MESSAGE,
		fetchedAt: now.toISOString(),
		issueDate: null,
		date: null,
		bull: null,
		cow: null,
	};
}

export function shouldPersistLiveMarketPrice(marketPrice) {
	return marketPrice?.available === true && marketPrice?.source === "kape-live";
}
