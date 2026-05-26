// 농가별 실측 메트릭(두당 월 사료비·증체율)을 산출하는 헬퍼.
//
// 출하 수익성 시뮬레이션(`profitability-service.js`)이 산업 평균 상수를 일률
// 적용하지 않도록, 농가의 최근 운영 데이터(사료/약품 비용, 출하 기록)로부터
// 실제 값을 계산하고, 데이터가 부족하면 호출자가 fallback 상수로 안전하게
// 떨어질 수 있도록 명시적 `sampleSize`를 함께 돌려준다.
//
// 함수 시그니처를 순수(pure)하게 유지해 단위 테스트가 외부 의존(prisma) 없이
// 검증할 수 있게 했다.

// Inlined to keep this module ESM-pure and free of the utils.js → constants
// chain (utils.js has an extension-less internal import that breaks under
// node:test ESM resolution). Same semantics as `lib/utils.js#toFiniteNumber`.
function toFiniteNumber(value) {
	if (value === null || value === undefined || value === "") return 0;
	const amount = Number(value);
	return Number.isFinite(amount) ? amount : 0;
}

const FEED_CATEGORY_KEYS = new Set([
	"feed",
	"feed-roughage",
	"feed-concentrate",
	"roughage",
	"concentrate",
	"hay",
]);

function toValidDate(value) {
	if (!value) return null;
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? null : date;
}

function monthsBetween(start, end) {
	const a = toValidDate(start);
	const b = toValidDate(end);
	if (!a || !b) return null;
	const diff = (b - a) / (1000 * 60 * 60 * 24 * 30.4375);
	return diff;
}

function isFeedExpense(record) {
	if (!record || typeof record !== "object") return false;
	const category =
		typeof record.category === "string" ? record.category.toLowerCase() : null;
	return category !== null && FEED_CATEGORY_KEYS.has(category);
}

function startOfMonth(date) {
	return new Date(date.getFullYear(), date.getMonth(), 1);
}

/**
 * Estimate per-head monthly feed cost from the farm's own expense ledger.
 *
 * Inputs:
 *  - expenseRecords: array of { date, category, amount }
 *  - activeCattleCount: number of currently active cattle
 *  - now: reference "today" (defaults to new Date())
 *  - windowMonths: how many months back to look (default 6)
 *
 * Returns:
 *  - { estimate, sampleSize, totalFeedSpend, monthsCovered }
 *    - estimate: number | null (per-head per-month feed spend; null if no data)
 *    - sampleSize: number of feed expense records included
 *    - totalFeedSpend: integer total feed spend over the window
 *    - monthsCovered: number of distinct months that had at least 1 feed record
 *
 * The estimate is intentionally conservative: divides total feed spend across
 * the full window (windowMonths × activeCattleCount), not just the months with
 * records, so sporadic logging doesn't inflate the per-head cost.
 */
export function estimateMonthlyFeedCostPerHead({
	expenseRecords = [],
	activeCattleCount = 0,
	now = new Date(),
	windowMonths = 6,
} = {}) {
	if (
		!Array.isArray(expenseRecords) ||
		expenseRecords.length === 0 ||
		!Number.isFinite(activeCattleCount) ||
		activeCattleCount <= 0
	) {
		return {
			estimate: null,
			sampleSize: 0,
			totalFeedSpend: 0,
			monthsCovered: 0,
		};
	}

	const windowStart = startOfMonth(
		new Date(now.getFullYear(), now.getMonth() - (windowMonths - 1), 1),
	);

	const includedMonths = new Set();
	let totalFeedSpend = 0;
	let sampleSize = 0;

	for (const record of expenseRecords) {
		if (!isFeedExpense(record)) continue;
		const date = toValidDate(record.date);
		if (!date || date < windowStart) continue;
		const amount = toFiniteNumber(record.amount);
		if (!Number.isFinite(amount) || amount < 0) continue;

		totalFeedSpend += amount;
		sampleSize += 1;
		includedMonths.add(
			`${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`,
		);
	}

	if (sampleSize === 0) {
		return {
			estimate: null,
			sampleSize: 0,
			totalFeedSpend: 0,
			monthsCovered: 0,
		};
	}

	const denominator = windowMonths * activeCattleCount;
	const estimate = Math.round(totalFeedSpend / denominator);

	return {
		estimate,
		sampleSize,
		totalFeedSpend: Math.round(totalFeedSpend),
		monthsCovered: includedMonths.size,
	};
}

/**
 * Estimate average monthly weight gain (kg) from completed sales records.
 *
 * Inputs:
 *  - salesRecords: array of { cattleId, saleDate, ... }
 *  - cattleById: Map or object keyed by cattle id → { birthDate, weight, purchasePrice, purchaseDate?, purchaseWeight? }
 *  - now: reference "today" (defaults to new Date())
 *  - windowMonths: how many months back of sales to consider (default 12)
 *
 * Returns: { estimate, sampleSize }
 *   - estimate: kg/month gain across the sample, null if insufficient data
 *   - sampleSize: how many sales contributed
 *
 * If we have a `purchaseWeight` + `purchaseDate` we use that (true ADG); otherwise
 * we approximate gain as (saleWeight − birth-weight reference 40kg) over the
 * cattle's full life span, which is a coarse but conservative proxy.
 */
export function estimateMonthlyWeightGainPerHead({
	salesRecords = [],
	cattleById = new Map(),
	now = new Date(),
	windowMonths = 12,
	birthWeightKg = 40,
} = {}) {
	if (!Array.isArray(salesRecords) || salesRecords.length === 0) {
		return { estimate: null, sampleSize: 0 };
	}

	const lookup =
		cattleById instanceof Map
			? cattleById
			: new Map(
					Object.entries(cattleById ?? {}).filter(
						([, value]) => value && typeof value === "object",
					),
				);

	const windowStart = startOfMonth(
		new Date(now.getFullYear(), now.getMonth() - (windowMonths - 1), 1),
	);

	const monthlyGains = [];
	for (const sale of salesRecords) {
		if (!sale || typeof sale !== "object") continue;
		const saleDate = toValidDate(sale.saleDate);
		if (!saleDate || saleDate < windowStart) continue;
		const cattle = lookup.get(sale.cattleId);
		if (!cattle) continue;

		const saleWeight = toFiniteNumber(sale.weight ?? cattle.weight);
		if (!Number.isFinite(saleWeight) || saleWeight <= 0) continue;

		const purchaseDate = toValidDate(cattle.purchaseDate);
		const purchaseWeight = toFiniteNumber(cattle.purchaseWeight);
		const birthDate = toValidDate(cattle.birthDate);

		let startReferenceDate = purchaseDate ?? birthDate;
		let startReferenceWeight =
			Number.isFinite(purchaseWeight) && purchaseWeight > 0
				? purchaseWeight
				: birthWeightKg;
		if (!startReferenceDate) continue;

		const months = monthsBetween(startReferenceDate, saleDate);
		if (!Number.isFinite(months) || months <= 0) continue;

		const gain = saleWeight - startReferenceWeight;
		if (gain <= 0) continue;

		monthlyGains.push(gain / months);
	}

	if (monthlyGains.length === 0) {
		return { estimate: null, sampleSize: 0 };
	}

	const sum = monthlyGains.reduce((acc, value) => acc + value, 0);
	const estimate = Math.round((sum / monthlyGains.length) * 10) / 10;

	return { estimate, sampleSize: monthlyGains.length };
}

/**
 * Combine the two estimators above and expose a single "did we learn?" flag the
 * UI can use to label whether the projection used farm-specific data.
 *
 * Returns: { feedCostPerHead, weightGainPerHead, isCustomized, dataAge }
 */
export function computeFarmAdjustments({
	expenseRecords = [],
	salesRecords = [],
	cattleById = new Map(),
	activeCattleCount = 0,
	now = new Date(),
	defaults: { defaultMonthlyFeedCost, defaultMonthlyWeightGain } = {},
} = {}) {
	const feedCost = estimateMonthlyFeedCostPerHead({
		expenseRecords,
		activeCattleCount,
		now,
	});
	const weightGain = estimateMonthlyWeightGainPerHead({
		salesRecords,
		cattleById,
		now,
	});

	const usedFeedCost = Number.isFinite(feedCost.estimate)
		? feedCost.estimate
		: defaultMonthlyFeedCost;
	const usedWeightGain = Number.isFinite(weightGain.estimate)
		? weightGain.estimate
		: defaultMonthlyWeightGain;

	const isCustomized =
		Number.isFinite(feedCost.estimate) ||
		Number.isFinite(weightGain.estimate);

	return {
		feedCostPerHead: usedFeedCost,
		weightGainPerHead: usedWeightGain,
		isCustomized,
		evidence: {
			feedCost,
			weightGain,
		},
	};
}
