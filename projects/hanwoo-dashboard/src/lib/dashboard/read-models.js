import prisma from '../db';
import {
  DASHBOARD_CACHE_TTLS,
  buildCattleListKeyPrefix,
  buildDashboardSummaryKey,
  buildMarketPriceDayKey,
  buildMarketPriceLatestKey,
  buildNotificationsKey,
  buildSalesListKeyPrefix,
  deleteCachedKeys,
  deleteCachedKeysByPrefixes,
  getCachedJson,
  setCachedJson,
} from './cache.js';

function normalizeDate(value) {
  if (value instanceof Date) {
    return value;
  }

  if (!value) {
    return new Date();
  }

  if (typeof value === 'string' && /^\d{8}$/.test(value)) {
    return new Date(`${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}T00:00:00.000Z`);
  }

  return new Date(value);
}

function toIssueDateKey(issueDate) {
  const date = normalizeDate(issueDate);
  return date.toISOString().slice(0, 10);
}

export async function getDashboardSummarySnapshot(farmId = 'default', options = {}) {
  const cacheKey = buildDashboardSummaryKey(farmId);

  if (!options.bypassCache) {
    const cached = await getCachedJson(cacheKey);
    if (cached) {
      return cached;
    }
  }

  const snapshot = await prisma.dashboardSnapshot.findUnique({
    where: { key: cacheKey },
  });

  if (!snapshot) {
    return null;
  }

  await setCachedJson(cacheKey, snapshot, DASHBOARD_CACHE_TTLS.summary);
  return snapshot;
}

export async function saveDashboardSummarySnapshot(input) {
  const cacheKey = buildDashboardSummaryKey(input.farmId);
  const snapshot = await prisma.dashboardSnapshot.upsert({
    where: { key: cacheKey },
    update: {
      payload: input.payload,
      staleAt: input.staleAt,
      version: input.version ?? 1,
      generatedAt: new Date(),
    },
    create: {
      key: cacheKey,
      payload: input.payload,
      staleAt: input.staleAt,
      version: input.version ?? 1,
    },
  });

  await setCachedJson(cacheKey, snapshot, DASHBOARD_CACHE_TTLS.summary);
  return snapshot;
}

export async function getNotificationSummary(farmId = 'default', options = {}) {
  const cacheKey = buildNotificationsKey(farmId);

  if (!options.bypassCache) {
    const cached = await getCachedJson(cacheKey);
    if (cached) {
      return cached;
    }
  }

  const summary = await prisma.notificationSummary.findUnique({
    where: { key: cacheKey },
  });

  if (!summary) {
    return null;
  }

  await setCachedJson(cacheKey, summary, DASHBOARD_CACHE_TTLS.notifications);
  return summary;
}

export async function saveNotificationSummary(input) {
  const cacheKey = buildNotificationsKey(input.farmId);
  const summary = await prisma.notificationSummary.upsert({
    where: { key: cacheKey },
    update: {
      payload: input.payload,
      generatedAt: new Date(),
    },
    create: {
      key: cacheKey,
      payload: input.payload,
    },
  });

  await setCachedJson(cacheKey, summary, DASHBOARD_CACHE_TTLS.notifications);
  return summary;
}

export async function getLatestMarketPriceSnapshot(options = {}) {
  const latestKey = buildMarketPriceLatestKey();

  if (!options.bypassCache) {
    const cached = await getCachedJson(latestKey);
    if (cached) {
      return cached;
    }
  }

  const snapshot = await prisma.marketPriceSnapshot.findFirst({
    orderBy: [
      { issueDate: 'desc' },
      { fetchedAt: 'desc' },
    ],
  });

  if (!snapshot) {
    return null;
  }

  await setCachedJson(latestKey, snapshot, DASHBOARD_CACHE_TTLS.marketPriceLatest);
  await setCachedJson(
    buildMarketPriceDayKey(toIssueDateKey(snapshot.issueDate)),
    snapshot,
    DASHBOARD_CACHE_TTLS.marketPriceDay,
  );

  return snapshot;
}

export async function saveMarketPriceSnapshot(input) {
  const issueDate = normalizeDate(input.issueDate ?? input.date);
  const issueDateKey = toIssueDateKey(issueDate);

  const snapshot = await prisma.marketPriceSnapshot.upsert({
    where: { issueDate },
    update: {
      isRealtime: input.isRealtime ?? false,
      bullGrade1pp: input.bull.grade1pp,
      bullGrade1p: input.bull.grade1p,
      bullGrade1: input.bull.grade1,
      cowGrade1pp: input.cow.grade1pp,
      cowGrade1p: input.cow.grade1p,
      cowGrade1: input.cow.grade1,
      source: input.source ?? 'KAPE',
      fetchedAt: new Date(),
    },
    create: {
      issueDate,
      isRealtime: input.isRealtime ?? false,
      bullGrade1pp: input.bull.grade1pp,
      bullGrade1p: input.bull.grade1p,
      bullGrade1: input.bull.grade1,
      cowGrade1pp: input.cow.grade1pp,
      cowGrade1p: input.cow.grade1p,
      cowGrade1: input.cow.grade1,
      source: input.source ?? 'KAPE',
    },
  });

  await setCachedJson(buildMarketPriceLatestKey(), snapshot, DASHBOARD_CACHE_TTLS.marketPriceLatest);
  await setCachedJson(buildMarketPriceDayKey(issueDateKey), snapshot, DASHBOARD_CACHE_TTLS.marketPriceDay);

  return snapshot;
}

export async function invalidateDashboardCaches(input = {}) {
  const farmId = input.farmId ?? 'default';
  const keys = [
    input.summary ? buildDashboardSummaryKey(farmId) : null,
    input.notifications ? buildNotificationsKey(farmId) : null,
    input.marketPriceLatest ? buildMarketPriceLatestKey() : null,
    input.marketPriceDay ? buildMarketPriceDayKey(input.marketPriceDay) : null,
  ];
  const prefixes = [
    input.cattleListPages ? buildCattleListKeyPrefix(farmId) : null,
    input.salesListPages ? buildSalesListKeyPrefix(farmId) : null,
  ];

  const snapshotDeletes = [];

  if (input.summary) {
    snapshotDeletes.push(
      prisma.dashboardSnapshot.delete({
        where: { key: buildDashboardSummaryKey(farmId) },
      }).catch((error) => {
        if (error?.code !== 'P2025') {
          throw error;
        }
      }),
    );
  }

  if (input.notifications) {
    snapshotDeletes.push(
      prisma.notificationSummary.delete({
        where: { key: buildNotificationsKey(farmId) },
      }).catch((error) => {
        if (error?.code !== 'P2025') {
          throw error;
        }
      }),
    );
  }

  const [exactDeletes, prefixDeletes] = await Promise.all([
    deleteCachedKeys(keys),
    deleteCachedKeysByPrefixes(prefixes),
    ...snapshotDeletes,
  ]);

  return {
    exactDeletes,
    prefixDeletes,
  };
}
