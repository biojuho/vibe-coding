function startOfCurrentMonth(now = new Date()) {
  return new Date(now.getFullYear(), now.getMonth(), 1);
}

function toDateKey(value) {
  return value.toISOString().slice(0, 10);
}

function normalizeStatusCounts(rows) {
  return rows.reduce((accumulator, row) => {
    accumulator[row.status] = row._count._all;
    return accumulator;
  }, {});
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

  const [activeHeadcount, statusCounts, buildings, cattlePerBuilding, salesThisMonth, expensesThisMonth, farmSettings] =
    await Promise.all([
      db.cattle.count({ where: { isArchived: false } }),
      db.cattle.groupBy({
        by: ['status'],
        where: { isArchived: false },
        _count: { _all: true },
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
      db.expenseRecord.aggregate({
        _sum: { amount: true },
        where: {
          date: {
            gte: monthStart,
          },
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

  return {
    farmId,
    generatedAt: generatedAt.toISOString(),
    headcount: {
      totalActive: activeHeadcount,
      byStatus: normalizeStatusCounts(statusCounts),
    },
    monthlyRollup: {
      monthStart: toDateKey(monthStart),
      salesTotal: monthlySalesTotal,
      expenseTotal: monthlyExpenseTotal,
      profitTotal: monthlySalesTotal - monthlyExpenseTotal,
    },
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
