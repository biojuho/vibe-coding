import prisma from '../db';
import {
  DASHBOARD_CACHE_TTLS,
  buildCattleListKey,
  buildSalesListKey,
  getCachedJson,
  setCachedJson,
} from './cache.js';

const DEFAULT_LIMIT = 50;
const MAX_LIMIT = 100;

export class DashboardQueryValidationError extends Error {
  constructor(message) {
    super(message);
    this.name = 'DashboardQueryValidationError';
  }
}

function normalizeOptionalString(value) {
  if (value === null || value === undefined) {
    return null;
  }

  const normalized = String(value).trim();
  return normalized === '' ? null : normalized;
}

function parseLimit(value) {
  if (value === null || value === undefined || value === '') {
    return DEFAULT_LIMIT;
  }

  const parsed = Number.parseInt(String(value), 10);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new DashboardQueryValidationError('`limit` must be a positive integer.');
  }

  return Math.min(parsed, MAX_LIMIT);
}

function parsePenNumber(value) {
  const normalized = normalizeOptionalString(value);
  if (normalized === null) {
    return null;
  }

  const parsed = Number.parseInt(normalized, 10);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new DashboardQueryValidationError('`penNumber` must be a positive integer.');
  }

  return parsed;
}

function parseDateParam(value, fieldName) {
  const normalized = normalizeOptionalString(value);
  if (normalized === null) {
    return null;
  }

  const parsed = new Date(`${normalized}T00:00:00.000Z`);
  if (Number.isNaN(parsed.getTime())) {
    throw new DashboardQueryValidationError(`\`${fieldName}\` must be a valid YYYY-MM-DD date.`);
  }

  return parsed;
}

function toDateKey(date) {
  return date.toISOString().slice(0, 10);
}

function endOfDay(date) {
  const value = new Date(date);
  value.setUTCHours(23, 59, 59, 999);
  return value;
}

function encodeCursor(payload) {
  return Buffer.from(JSON.stringify(payload)).toString('base64url');
}

function decodeCursor(cursor) {
  const normalized = normalizeOptionalString(cursor);
  if (normalized === null) {
    return null;
  }

  try {
    const parsed = JSON.parse(Buffer.from(normalized, 'base64url').toString('utf8'));
    if (!parsed?.id || !parsed?.sortValue) {
      throw new DashboardQueryValidationError('`cursor` is malformed.');
    }

    const sortDate = new Date(parsed.sortValue);
    if (Number.isNaN(sortDate.getTime())) {
      throw new DashboardQueryValidationError('`cursor` has an invalid timestamp.');
    }

    return {
      id: parsed.id,
      sortValue: sortDate,
    };
  } catch (error) {
    if (error instanceof DashboardQueryValidationError) {
      throw error;
    }

    throw new DashboardQueryValidationError('`cursor` is malformed.');
  }
}

function buildDescendingCursorWhere(fieldName, cursor) {
  if (!cursor) {
    return undefined;
  }

  return {
    OR: [
      {
        [fieldName]: {
          lt: cursor.sortValue,
        },
      },
      {
        AND: [
          {
            [fieldName]: cursor.sortValue,
          },
          {
            id: {
              lt: cursor.id,
            },
          },
        ],
      },
    ],
  };
}

function buildPageInfo(items, hasMore, limit, sortField) {
  if (!hasMore || items.length === 0) {
    return {
      hasMore: false,
      nextCursor: null,
      limit,
      returnedCount: items.length,
    };
  }

  const lastItem = items[items.length - 1];
  return {
    hasMore: true,
    nextCursor: encodeCursor({
      id: lastItem.id,
      sortValue: new Date(lastItem[sortField]).toISOString(),
    }),
    limit,
    returnedCount: items.length,
  };
}

export function parseCattleListQuery(searchParams) {
  return {
    buildingId: normalizeOptionalString(searchParams.get('buildingId')),
    penNumber: parsePenNumber(searchParams.get('penNumber')),
    status: normalizeOptionalString(searchParams.get('status')),
    cursor: normalizeOptionalString(searchParams.get('cursor')),
    limit: parseLimit(searchParams.get('limit')),
    fresh: searchParams.get('fresh') === '1',
  };
}

export function parseSalesListQuery(searchParams) {
  const from = parseDateParam(searchParams.get('from'), 'from');
  const to = parseDateParam(searchParams.get('to'), 'to');

  if (from && to && from > to) {
    throw new DashboardQueryValidationError('`from` must be before or equal to `to`.');
  }

  return {
    from,
    to,
    cursor: normalizeOptionalString(searchParams.get('cursor')),
    limit: parseLimit(searchParams.get('limit')),
    fresh: searchParams.get('fresh') === '1',
  };
}

export async function getCattleListPage(input = {}) {
  const {
    farmId = 'default',
    buildingId = null,
    penNumber = null,
    status = null,
    cursor = null,
    limit = DEFAULT_LIMIT,
    bypassCache = false,
  } = input;

  const cacheKey = buildCattleListKey({
    farmId,
    buildingId,
    penNumber,
    status,
    cursor,
    limit,
  });

  if (!bypassCache) {
    const cached = await getCachedJson(cacheKey);
    if (cached) {
      return {
        ...cached,
        meta: {
          ...(cached.meta ?? {}),
          source: 'cache',
        },
      };
    }
  }

  const decodedCursor = decodeCursor(cursor);
  const cursorWhere = buildDescendingCursorWhere('updatedAt', decodedCursor);
  const records = await prisma.cattle.findMany({
    where: {
      isArchived: false,
      ...(buildingId ? { buildingId } : {}),
      ...(penNumber ? { penNumber } : {}),
      ...(status ? { status } : {}),
      ...(cursorWhere ?? {}),
    },
    select: {
      id: true,
      tagNumber: true,
      name: true,
      birthDate: true,
      gender: true,
      status: true,
      weight: true,
      buildingId: true,
      penNumber: true,
      memo: true,
      geneticFather: true,
      geneticMother: true,
      geneticGrade: true,
      weightHistory: true,
      lastEstrus: true,
      pregnancyDate: true,
      purchasePrice: true,
      purchaseDate: true,
      createdAt: true,
      updatedAt: true,
      building: {
        select: {
          id: true,
          name: true,
        },
      },
    },
    orderBy: [{ updatedAt: 'desc' }, { id: 'desc' }],
    take: limit + 1,
  });

  const hasMore = records.length > limit;
  const items = hasMore ? records.slice(0, limit) : records;
  const response = {
    items,
    filters: {
      buildingId,
      penNumber,
      status,
    },
    pageInfo: buildPageInfo(items, hasMore, limit, 'updatedAt'),
    meta: {
      source: 'db',
      fetchedAt: new Date().toISOString(),
    },
  };

  await setCachedJson(cacheKey, response, DASHBOARD_CACHE_TTLS.cattleList);
  return response;
}

export async function getSalesListPage(input = {}) {
  const {
    farmId = 'default',
    from = null,
    to = null,
    cursor = null,
    limit = DEFAULT_LIMIT,
    bypassCache = false,
  } = input;

  const fromKey = from ? toDateKey(from) : null;
  const toKey = to ? toDateKey(to) : null;
  const cacheKey = buildSalesListKey({
    farmId,
    from: fromKey,
    to: toKey,
    cursor,
    limit,
  });

  if (!bypassCache) {
    const cached = await getCachedJson(cacheKey);
    if (cached) {
      return {
        ...cached,
        meta: {
          ...(cached.meta ?? {}),
          source: 'cache',
        },
      };
    }
  }

  const decodedCursor = decodeCursor(cursor);
  const cursorWhere = buildDescendingCursorWhere('saleDate', decodedCursor);
  const saleDateWhere = {};

  if (from) {
    saleDateWhere.gte = from;
  }

  if (to) {
    saleDateWhere.lte = endOfDay(to);
  }

  const records = await prisma.salesRecord.findMany({
    where: {
      ...(Object.keys(saleDateWhere).length > 0 ? { saleDate: saleDateWhere } : {}),
      ...(cursorWhere ?? {}),
    },
    select: {
      id: true,
      saleDate: true,
      price: true,
      purchaser: true,
      grade: true,
      cattleId: true,
      createdAt: true,
      updatedAt: true,
      cattle: {
        select: {
          id: true,
          name: true,
          tagNumber: true,
          purchasePrice: true,
        },
      },
    },
    orderBy: [{ saleDate: 'desc' }, { id: 'desc' }],
    take: limit + 1,
  });

  const hasMore = records.length > limit;
  const items = hasMore ? records.slice(0, limit) : records;
  const response = {
    items,
    filters: {
      from: fromKey,
      to: toKey,
    },
    pageInfo: buildPageInfo(items, hasMore, limit, 'saleDate'),
    meta: {
      source: 'db',
      fetchedAt: new Date().toISOString(),
    },
  };

  await setCachedJson(cacheKey, response, DASHBOARD_CACHE_TTLS.salesList);
  return response;
}
