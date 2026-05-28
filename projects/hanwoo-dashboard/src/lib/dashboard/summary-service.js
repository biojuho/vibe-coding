import { toFiniteNumber } from "../utils";

function startOfCurrentMonth(now = new Date()) {
	return new Date(now.getFullYear(), now.getMonth(), 1);
}

function startOfRecentMonthWindow(monthCount, now = new Date()) {
	return new Date(now.getFullYear(), now.getMonth() - (monthCount - 1), 1);
}

function toDateKey(value) {
	return value.toISOString().slice(0, 10);
}

function toMonthKey(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	if (Number.isNaN(date.getTime())) {
		return null;
	}

	if (typeof value === "string") {
		const dateKey = value.trim().slice(0, 10);
		if (/^\d{4}-\d{2}-\d{2}$/.test(dateKey)) {
			const strictDate = new Date(`${dateKey}T00:00:00.000Z`);
			if (
				Number.isNaN(strictDate.getTime()) ||
				strictDate.toISOString().slice(0, 10) !== dateKey
			) {
				return null;
			}
		}
	}

	return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function normalizeSummaryOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeSummaryRows(rows) {
	return Array.isArray(rows)
		? rows.filter(
				(row) => row && typeof row === "object" && !Array.isArray(row),
			)
		: [];
}

function resolveGeneratedAt(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);

	return Number.isNaN(date.getTime()) ? new Date() : date;
}

function resolveFinancialSeriesMonthCount(value) {
	return Number.isSafeInteger(value) && value > 0 ? Math.min(value, 24) : 6;
}

function normalizeStatusCounts(rows) {
	return normalizeSummaryRows(rows).reduce((accumulator, row) => {
		if (typeof row.status !== "string" || row.status.length === 0) {
			return accumulator;
		}

		accumulator[row.status] = toFiniteNumber(row._count?._all);
		return accumulator;
	}, {});
}

function buildFinancialSeries(options = {}) {
	const {
		salesRecords = [],
		expenseRecords = [],
		months = 6,
		generatedAt = new Date(),
	} = normalizeSummaryOptions(options);
	const series = [];
	const salesByMonth = new Map();
	const expensesByMonth = new Map();
	const safeSalesRecords = normalizeSummaryRows(salesRecords);
	const safeExpenseRecords = normalizeSummaryRows(expenseRecords);
	const safeGeneratedAt = resolveGeneratedAt(generatedAt);
	const monthCount = resolveFinancialSeriesMonthCount(months);

	for (const record of safeSalesRecords) {
		const monthKey = toMonthKey(record.saleDate);
		if (!monthKey) continue;
		salesByMonth.set(
			monthKey,
			(salesByMonth.get(monthKey) ?? 0) + toFiniteNumber(record.price),
		);
	}

	for (const record of safeExpenseRecords) {
		const monthKey = toMonthKey(record.date);
		if (!monthKey) continue;
		expensesByMonth.set(
			monthKey,
			(expensesByMonth.get(monthKey) ?? 0) + toFiniteNumber(record.amount),
		);
	}

	for (let index = monthCount - 1; index >= 0; index -= 1) {
		const date = new Date(
			safeGeneratedAt.getFullYear(),
			safeGeneratedAt.getMonth() - index,
			1,
		);
		const monthKey = toMonthKey(date);
		const revenue = salesByMonth.get(monthKey) ?? 0;
		const expense = expensesByMonth.get(monthKey) ?? 0;

		series.push({
			month: monthKey,
			revenue,
			expense,
			profit: revenue - expense,
		});
	}

	return series;
}

function resolveClient(client) {
	if (!client) {
		throw new Error("buildDashboardSummaryPayload requires a Prisma client.");
	}

	return client;
}

export async function buildDashboardSummaryPayload(options = {}) {
	const { farmId = "default", client } = normalizeSummaryOptions(options);
	const db = resolveClient(client);
	const generatedAt = new Date();
	const monthStart = startOfCurrentMonth(generatedAt);
	const recentWindowStart = startOfRecentMonthWindow(6, generatedAt);

	const [
		activeHeadcount,
		statusCounts,
		weightAggregate,
		buildings,
		cattlePerBuilding,
		salesThisMonth,
		salesCountThisMonth,
		expensesThisMonth,
		recentSales,
		recentExpenses,
		farmSettings,
	] = await Promise.all([
		db.cattle.count({ where: { isArchived: false } }),
		db.cattle.groupBy({
			by: ["status"],
			where: { isArchived: false },
			_count: { _all: true },
		}),
		db.cattle.aggregate({
			where: { isArchived: false },
			_avg: { weight: true },
		}),
		db.building.findMany({
			orderBy: { name: "asc" },
			select: {
				id: true,
				name: true,
				penCount: true,
			},
		}),
		db.cattle.groupBy({
			by: ["buildingId"],
			where: { isArchived: false },
			_count: { _all: true },
		}),
		db.salesRecord.aggregate({
			_sum: { price: true },
			where: {
				saleDate: {
					gte: monthStart,
				},
			},
		}),
		db.salesRecord.count({
			where: {
				saleDate: {
					gte: monthStart,
				},
			},
		}),
		db.expenseRecord.aggregate({
			_sum: { amount: true },
			where: {
				date: {
					gte: monthStart,
				},
			},
		}),
		db.salesRecord.findMany({
			where: {
				saleDate: {
					gte: recentWindowStart,
				},
			},
			select: {
				saleDate: true,
				price: true,
			},
		}),
		db.expenseRecord.findMany({
			where: {
				date: {
					gte: recentWindowStart,
				},
			},
			select: {
				date: true,
				amount: true,
			},
		}),
		db.farmSettings.findUnique({
			where: { id: farmId },
			select: {
				id: true,
				name: true,
				location: true,
				latitude: true,
				longitude: true,
				updatedAt: true,
			},
		}),
	]);

	const buildingCounts = new Map(
		normalizeSummaryRows(cattlePerBuilding).map((row) => [
			row.buildingId,
			toFiniteNumber(row._count?._all),
		]),
	);
	const monthlySalesTotal = toFiniteNumber(salesThisMonth?._sum?.price);
	const monthlyExpenseTotal = toFiniteNumber(expensesThisMonth?._sum?.amount);
	const averageWeight = weightAggregate?._avg?.weight
		? Number(weightAggregate._avg.weight.toFixed(1))
		: 0;
	const safeBuildings = normalizeSummaryRows(buildings);

	return {
		farmId,
		generatedAt: generatedAt.toISOString(),
		headcount: {
			totalActive: activeHeadcount,
			byStatus: normalizeStatusCounts(statusCounts),
			averageWeight,
		},
		monthlyRollup: {
			monthStart: toDateKey(monthStart),
			salesCount: salesCountThisMonth,
			salesTotal: monthlySalesTotal,
			expenseTotal: monthlyExpenseTotal,
			profitTotal: monthlySalesTotal - monthlyExpenseTotal,
		},
		financialSeries: buildFinancialSeries({
			salesRecords: recentSales,
			expenseRecords: recentExpenses,
			generatedAt,
		}),
		buildingCount: safeBuildings.length,
		buildingOccupancy: safeBuildings.map((building) => {
			const headcount = buildingCounts.get(building.id) ?? 0;
			const penCount = building.penCount || 0;

			return {
				buildingId: building.id,
				name: building.name,
				penCount,
				headcount,
				occupancyRate:
					penCount > 0 ? Number((headcount / penCount).toFixed(4)) : 0,
			};
		}),
		farmSettings,
	};
}
