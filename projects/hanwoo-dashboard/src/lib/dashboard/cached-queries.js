'use cache';

import { cacheLife, cacheTag } from 'next/cache';
import prisma from '../db';
import { buildDashboardSummaryPayload } from './summary-service';

// ============================================================
// Cached Read-Only Query Wrappers
//
// These functions use the stable Next.js 16 "use cache" directive
// to enable framework-level data caching with automatic
// invalidation via revalidateTag().
//
// Existing Redis caching inside the underlying functions remains
// intact — it acts as a secondary layer. Over time the Redis
// layer can be removed once the framework cache proves stable.
// ============================================================

/**
 * Cached dashboard summary (30-second TTL).
 * Invalidated by tag: "dashboard-summary".
 */
export async function getCachedDashboardSummary(farmId = 'default') {
  cacheLife('seconds');
  cacheTag('dashboard-summary');

  return buildDashboardSummaryPayload({ client: prisma, farmId });
}

/**
 * Cached cattle list page (60-second TTL).
 * Invalidated by tag: "cattle-list".
 */
export async function getCachedCattleList(filters = {}) {
  cacheLife('minutes');
  cacheTag('cattle-list');

  // Dynamic import to avoid circular dep at module-level
  const { getCattleListPage } = await import('./list-queries');
  return getCattleListPage(filters);
}

/**
 * Cached sales list page (60-second TTL).
 * Invalidated by tag: "sales-list".
 */
export async function getCachedSalesList(filters = {}) {
  cacheLife('minutes');
  cacheTag('sales-list');

  const { getSalesListPage } = await import('./list-queries');
  return getSalesListPage(filters);
}
