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
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}`;
}

function normalizeStatusCounts(rows) {
  return rows.reduce((accumulator, row) => {
    accumulator[row.status] = row._count._all;
    return accumulator;
  }, {});
}

function buildFinancialSeries({ salesRecords = [], expenseRecords = [], months = 6, generatedAt = new Date() } = {}) {
  const series = [];
  const salesByMonth = new Map();
  const expensesByMonth = new Map();

  for (const record of salesRecords) {
    const monthKey = toMonthKey(new Date(record.saleDate));
    salesByMonth.set(monthKey, (salesByMonth.get(monthKey) ?? 0) + (record.price ?? 0));
  }

  for (const record of expenseRecords) {
    const monthKey = toMonthKey(new Date(record.date));
    expensesByMonth.set(monthKey, (expensesByMonth.get(monthKey) ?? 0) + (record.amount ?? 0));
  }

  for (let index = months - 1; index >= 0; index -= 1) {
    const date = new Date(generatedAt.getFullYear(), generatedAt.getMonth() - index, 1);
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
    throw new Error('buildDashboardSummaryPayload requires a Prisma client.');
  }

  return client;
}

export async function buildDashboardSummaryPayload({ farmId = 'default', client } = {}) {
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
  ] =
    await Promise.all([
      db.cattle.count({ where: { isArchived: false } }),
      db.cattle.groupBy({
        by: ['status'],
        where: { isArchived: false },
        _count: { _all: true },
      }),
      db.cattle.aggregate({
        where: { isArchived: false },
        _avg: { weight: true },
      }),
      db.building.findMany({
        orderBy: { name: 'asc' },
        select: {
          id: true,
          name: true,
          penCount: true,
        },
      }),
      db.cattle.groupBy({
        by: ['buildingId'],
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
    cattlePerBuilding.map((row) => [row.buildingId, row._count._all]),
  );
  const monthlySalesTotal = salesThisMonth._sum.price ?? 0;
  const monthlyExpenseTotal = expensesThisMonth._sum.amount ?? 0;
  const averageWeight = weightAggregate._avg.weight ? Number(weightAggregate._avg.weight.toFixed(1)) : 0;

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
    buildingCount: buildings.length,
    buildingOccupancy: buildings.map((building) => {
      const headcount = buildingCounts.get(building.id) ?? 0;
      const penCount = building.penCount || 0;

      return {
        buildingId: building.id,
        name: building.name,
        penCount,
        headcount,
        occupancyRate: penCount > 0 ? Number((headcount / penCount).toFixed(4)) : 0,
      };
    }),
    farmSettings,
  };
}
