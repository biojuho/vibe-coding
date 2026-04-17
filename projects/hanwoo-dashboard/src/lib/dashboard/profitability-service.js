import prisma from '../db';
import { normalizeCachedMarketPrice } from '../market-price-state.mjs';

const DEFAULT_CALF_COST = 3500000;
const MONTHLY_FEED_COST = 150000;
const MONTHLY_WEIGHT_GAIN = 30; // kg

/**
 * Get difference in months between two dates
 */
function diffMonths(d1, d2) {
  let months;
  months = (d2.getFullYear() - d1.getFullYear()) * 12;
  months -= d1.getMonth();
  months += d2.getMonth();
  return months <= 0 ? 0 : months;
}

export async function getProfitabilityEstimates() {
  try {
    // 1. Fetch latest market price snapshot
    const latestSnapshot = await prisma.marketPriceSnapshot.findFirst({
      orderBy: { issueDate: 'desc' },
    });

    if (!latestSnapshot) {
      throw new Error('No market price data available for profitability simulation.');
    }

    // Normalize market price state
    const priceData = normalizeCachedMarketPrice({
      ...latestSnapshot,
      fetchedAt: latestSnapshot.fetchedAt.toISOString(),
      issueDate: latestSnapshot.issueDate.toISOString(),
      isRealtime: true, // Force to be considered valid
    });

    if (!priceData || !priceData.bull || !priceData.cow) {
      throw new Error('Price data parsing failed');
    }

    // 2. Fetch active cattle approaching or in the slaughter window (e.g. older than 24 months, active)
    const activeCattle = await prisma.cattle.findMany({
      where: {
        status: 'ACTIVE',
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
        if (ageMonths < 24) return null;

        const baseCost = cattle.purchasePrice || DEFAULT_CALF_COST;
        const cumulativeCost = baseCost + ageMonths * MONTHLY_FEED_COST;

        // Use Grade 1 as baseline estimation
        const currentKgPrice =
          cattle.gender === 'FEMALE' ? priceData.cow.grade1 : priceData.bull.grade1;

        const currentRevenue = cattle.weight * currentKgPrice;
        const currentProfit = currentRevenue - cumulativeCost;

        // Future Projection (1 month later)
        const futureWeight = cattle.weight + MONTHLY_WEIGHT_GAIN;
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
          weight: cattle.weight,
          currentProfit: Math.round(currentProfit),
          marginalGain: Math.round(marginalGain),
          recommendShipment:
            marginalGain <= 0 || ageMonths >= 30, // Sell now if marginal gain is neg or animal is 30+ months
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
    console.error('getProfitabilityEstimates Error:', err);
    return {
      success: false,
      data: null,
      error: err.message,
    };
  }
}
