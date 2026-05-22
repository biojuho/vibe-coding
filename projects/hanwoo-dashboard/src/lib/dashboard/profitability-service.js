import prisma from "../db";
import { normalizeCachedMarketPrice } from "../market-price-state.mjs";
import { toFiniteNumber } from "../utils";

const DEFAULT_CALF_COST = 3500000;
const MONTHLY_FEED_COST = 150000;
const MONTHLY_WEIGHT_GAIN = 30; // kg
const MARKET_PRICE_MISSING_MESSAGE =
	"수익성 시뮬레이션에 사용할 시세 데이터가 없습니다.";
const MARKET_PRICE_PARSE_MESSAGE = "시세 데이터를 해석하지 못했습니다.";
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

export async function getProfitabilityEstimates() {
	try {
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
		const activeCattle = await prisma.cattle.findMany({
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
			},
		});

		const now = new Date();

		const estimates = activeCattle
			.map((cattle) => {
				const ageMonths = diffMonths(cattle.birthDate, now);

				// Limit simulation strictly to cattle likely in shipping window (>= 24 months)
				if (ageMonths === null || ageMonths < 24) return null;

				const baseCost =
					toFiniteNumber(cattle.purchasePrice) || DEFAULT_CALF_COST;
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
		};
	} catch (err) {
		console.error("수익성 추정 오류:", err);
		const errorMessage = OPERATOR_FACING_ERROR_MESSAGES.has(err?.message)
			? err.message
			: PROFITABILITY_UNAVAILABLE_MESSAGE;

		return {
			success: false,
			data: null,
			error: errorMessage,
		};
	}
}
