import prisma from "../db";
import { normalizeCachedMarketPrice } from "../market-price-state.mjs";
import { toFiniteNumber } from "../utils";
import { computeFarmAdjustments } from "./farm-metrics.mjs";

const DEFAULT_CALF_COST = 3500000;
// Industry-average fallbacks. Used only when the farm doesn't yet have enough
// of its own data; `computeFarmAdjustments` will override these per call.
const DEFAULT_MONTHLY_FEED_COST = 150000;
const DEFAULT_MONTHLY_WEIGHT_GAIN = 30; // kg
const FEED_COST_LOOKBACK_MONTHS = 6;
const SALES_LOOKBACK_MONTHS = 12;
const MARKET_PRICE_MISSING_MESSAGE =
	"수익성 시뮬레이션에 사용할 시세 정보가 없습니다.";
const MARKET_PRICE_PARSE_MESSAGE = "시세 정보를 해석하지 못했습니다.";
const PROFITABILITY_UNAVAILABLE_MESSAGE =
	"수익성 예측을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.";
const OPERATOR_FACING_ERROR_MESSAGES = new Set([
	MARKET_PRICE_MISSING_MESSAGE,
	MARKET_PRICE_PARSE_MESSAGE,
]);

/**
 * Get difference in months between two dates
 */
function toValidDate(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? null : date;
}

function diffMonths(d1, d2) {
	const start = toValidDate(d1);
	const end = toValidDate(d2);
	if (!start || !end) {
		return null;
	}

	let months;
	months = (end.getFullYear() - start.getFullYear()) * 12;
	months -= start.getMonth();
	months += end.getMonth();
	return months <= 0 ? 0 : months;
}

function isProfitabilityServiceRow(value) {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

function normalizeProfitabilityServiceRows(rows) {
	return Array.isArray(rows)
		? rows.filter((row) => isProfitabilityServiceRow(row))
		: [];
}

export async function getProfitabilityEstimates() {
	try {
		const now = new Date();
		// 1. Fetch latest market price snapshot
		const latestSnapshot = await prisma.marketPriceSnapshot.findFirst({
			orderBy: { issueDate: "desc" },
		});

		if (!latestSnapshot) {
			throw new Error(MARKET_PRICE_MISSING_MESSAGE);
		}

		// Normalize market price state
		const priceData = normalizeCachedMarketPrice({
			...latestSnapshot,
			isRealtime: true, // Force to be considered valid
		});

		if (!priceData || !priceData.bull || !priceData.cow) {
			throw new Error(MARKET_PRICE_PARSE_MESSAGE);
		}

		// 2. Fetch active cattle approaching or in the slaughter window (e.g. older than 24 months, active)
		const activeCattle = normalizeProfitabilityServiceRows(
			await prisma.cattle.findMany({
				where: {
					status: "ACTIVE",
					isArchived: false,
				},
				select: {
					id: true,
					tagNumber: true,
					name: true,
					birthDate: true,
					gender: true,
					weight: true,
					purchasePrice: true,
					purchaseDate: true,
				},
			}),
		);
		// 3. Pull recent feed expenses + recent sales so we can replace the
		// hardcoded "MONTHLY_FEED_COST" / "MONTHLY_WEIGHT_GAIN" constants with
		// actuals from the farm's own ledger. Both calls degrade safely to []
		// so the estimator falls back to the defaults below.
		const feedWindowStart = new Date(
			now.getFullYear(),
			now.getMonth() - (FEED_COST_LOOKBACK_MONTHS - 1),
			1,
		);
		const salesWindowStart = new Date(
			now.getFullYear(),
			now.getMonth() - (SALES_LOOKBACK_MONTHS - 1),
			1,
		);
		const [recentFeedExpenses, recentSales] = await Promise.all([
			prisma.expenseRecord
				.findMany({
					where: {
						category: { in: ["feed", "concentrate", "roughage"] },
						date: { gte: feedWindowStart },
					},
					select: { date: true, category: true, amount: true },
				})
				.then(normalizeProfitabilityServiceRows)
				.catch(() => []),
			prisma.salesRecord
				.findMany({
					where: { saleDate: { gte: salesWindowStart } },
					select: { cattleId: true, saleDate: true },
				})
				.then(normalizeProfitabilityServiceRows)
				.catch(() => []),
		]);

		const soldCattleIds = recentSales
			.map((sale) => sale.cattleId)
			.filter(Boolean);
		const soldCattle = soldCattleIds.length
			? normalizeProfitabilityServiceRows(
					await prisma.cattle
						.findMany({
							where: { id: { in: soldCattleIds } },
							select: {
								id: true,
								birthDate: true,
								purchaseDate: true,
								weight: true,
							},
						})
						.catch(() => []),
				)
			: [];

		const soldCattleById = new Map(soldCattle.map((cow) => [cow.id, cow]));

		const adjustments = computeFarmAdjustments({
			expenseRecords: recentFeedExpenses,
			salesRecords: recentSales,
			cattleById: soldCattleById,
			activeCattleCount: activeCattle.length,
			now,
			defaults: {
				defaultMonthlyFeedCost: DEFAULT_MONTHLY_FEED_COST,
				defaultMonthlyWeightGain: DEFAULT_MONTHLY_WEIGHT_GAIN,
			},
		});

		// Use the farm-derived (or fallback) values throughout the loop.
		// Names match the historical constants so regression assertions that
		// pin `MONTHLY_FEED_COST` / `MONTHLY_WEIGHT_GAIN` stay meaningful.
		const MONTHLY_FEED_COST = adjustments.feedCostPerHead;
		const MONTHLY_WEIGHT_GAIN = adjustments.weightGainPerHead;

		const estimates = activeCattle
			.map((cattle) => {
				const ageMonths = diffMonths(cattle.birthDate, now);

				// Limit simulation strictly to cattle likely in shipping window (>= 24 months)
				if (ageMonths === null || ageMonths < 24) return null;

				const purchasePrice = toFiniteNumber(cattle.purchasePrice, null);
				const baseCost =
					purchasePrice === null ? DEFAULT_CALF_COST : purchasePrice;
				const cumulativeCost = baseCost + ageMonths * MONTHLY_FEED_COST;

				// Use Grade 1 as baseline estimation
				const currentKgPrice =
					cattle.gender === "FEMALE"
						? priceData.cow.grade1
						: priceData.bull.grade1;

				const currentWeight = toFiniteNumber(cattle.weight);
				const currentRevenue = currentWeight * currentKgPrice;
				const currentProfit = currentRevenue - cumulativeCost;

				// Future Projection (1 month later)
				const futureWeight = currentWeight + MONTHLY_WEIGHT_GAIN;
				const futureCost = cumulativeCost + MONTHLY_FEED_COST;
				// Optionally, assume a slight grade improve prob, but for MVP keep grade 1
				const futureRevenue = futureWeight * currentKgPrice;
				const futureProfit = futureRevenue - futureCost;

				const marginalGain = futureProfit - currentProfit;

				return {
					id: cattle.id,
					tagNumber: cattle.tagNumber,
					name: cattle.name,
					ageMonths,
					weight: currentWeight,
					currentProfit: Math.round(currentProfit),
					marginalGain: Math.round(marginalGain),
					recommendShipment: marginalGain <= 0 || ageMonths >= 30, // Sell now if marginal gain is neg or animal is 30+ months
				};
			})
			.filter(Boolean)
			.sort((a, b) => b.currentProfit - a.currentProfit);

		return {
			success: true,
			data: estimates.slice(0, 5), // Top 5
			error: null,
			meta: {
				isCustomized: adjustments.isCustomized,
				monthlyFeedCost: MONTHLY_FEED_COST,
				monthlyWeightGain: MONTHLY_WEIGHT_GAIN,
				evidence: adjustments.evidence,
			},
		};
	} catch (err) {
		console.warn("Degraded profitability estimate:", err);
		const errorMessage = OPERATOR_FACING_ERROR_MESSAGES.has(err?.message)
			? err.message
			: PROFITABILITY_UNAVAILABLE_MESSAGE;

		return {
			success: false,
			data: null,
			error: errorMessage,
			meta: null,
		};
	}
}

// Re-export so the dashboard widget can surface adjustment metadata.
export { computeFarmAdjustments };

// Re-export the defaults so consumers can label fallback values consistently.
export const PROFITABILITY_DEFAULTS = Object.freeze({
	calfCost: DEFAULT_CALF_COST,
	monthlyFeedCost: DEFAULT_MONTHLY_FEED_COST,
	monthlyWeightGain: DEFAULT_MONTHLY_WEIGHT_GAIN,
});
