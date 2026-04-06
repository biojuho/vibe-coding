import { ensureRedisConnection, isRedisConfigured } from '../redis.js';

export const DASHBOARD_CACHE_TTLS = Object.freeze({
  summary: 30,
  cattleList: 60,
  cattleHistory: 120,
  notifications: 15,
  salesList: 60,
  marketPriceLatest: 3600,
  marketPriceDay: 3600,
});

function normalizeSegment(value, fallback = 'all') {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }

  return String(value).trim();
}

export function buildDashboardSummaryKey(farmId = 'default') {
  return `dashboard:summary:v1:${normalizeSegment(farmId, 'default')}`;
}

export function buildCattleListKey(filters = {}) {
  const {
    farmId = 'default',
    buildingId,
    penNumber,
    status,
    cursor,
    limit = 50,
  } = filters;

  return [
    'dashboard:cattle:list:v1',
    normalizeSegment(farmId, 'default'),
    normalizeSegment(buildingId),
    normalizeSegment(penNumber),
    normalizeSegment(status),
    normalizeSegment(cursor),
    normalizeSegment(limit, '50'),
  ].join(':');
}

export function buildCattleListKeyPrefix(farmId = 'default') {
  return ['dashboard:cattle:list:v1', normalizeSegment(farmId, 'default')].join(':');
}

export function buildCattleHistoryKey(cattleId, cursor = 'start', limit = 20) {
  return [
    'dashboard:cattle:history:v1',
    normalizeSegment(cattleId, 'unknown'),
    normalizeSegment(cursor, 'start'),
    normalizeSegment(limit, '20'),
  ].join(':');
}

export function buildNotificationsKey(farmId = 'default') {
  return `dashboard:notifications:v1:${normalizeSegment(farmId, 'default')}`;
}

export function buildSalesListKey(filters = {}) {
  const {
    farmId = 'default',
    from = 'all',
    to = 'all',
    cursor = 'start',
    limit = 50,
  } = filters;

  return [
    'dashboard:sales:v1',
    normalizeSegment(farmId, 'default'),
    normalizeSegment(from),
    normalizeSegment(to),
    normalizeSegment(cursor, 'start'),
    normalizeSegment(limit, '50'),
  ].join(':');
}

export function buildSalesListKeyPrefix(farmId = 'default') {
  return ['dashboard:sales:v1', normalizeSegment(farmId, 'default')].join(':');
}

export function buildMarketPriceLatestKey() {
  return 'market-price:latest:v1';
}

export function buildMarketPriceDayKey(issueDate) {
  return `market-price:day:v1:${normalizeSegment(issueDate, 'unknown')}`;
}

export async function getCachedJson(key) {
  if (!isRedisConfigured()) {
    return null;
  }

  const redis = await ensureRedisConnection('cache');
  const rawValue = await redis.get(key);

  if (!rawValue) {
    return null;
  }

  return JSON.parse(rawValue);
}

export async function setCachedJson(key, value, ttlSeconds) {
  if (!isRedisConfigured()) {
    return value;
  }

  const redis = await ensureRedisConnection('cache');
  const serialized = JSON.stringify(value);

  if (ttlSeconds) {
    await redis.set(key, serialized, 'EX', ttlSeconds);
    return value;
  }

  await redis.set(key, serialized);
  return value;
}

export async function deleteCachedKeys(keys) {
  if (!isRedisConfigured()) {
    return 0;
  }

  const keyList = keys.filter(Boolean);
  if (keyList.length === 0) {
    return 0;
  }

  const redis = await ensureRedisConnection('cache');
  return redis.del(...keyList);
}

export async function deleteCachedKeysByPrefixes(prefixes) {
  if (!isRedisConfigured()) {
    return 0;
  }

  const prefixList = prefixes.filter(Boolean);
  if (prefixList.length === 0) {
    return 0;
  }

  const redis = await ensureRedisConnection('cache');
  let deleted = 0;

  for (const prefix of prefixList) {
    let cursor = '0';

    do {
      const [nextCursor, keys] = await redis.scan(cursor, 'MATCH', `${prefix}*`, 'COUNT', '100');
      cursor = nextCursor;

      if (keys.length > 0) {
        deleted += await redis.del(...keys);
      }
    } while (cursor !== '0');
  }

  return deleted;
}
