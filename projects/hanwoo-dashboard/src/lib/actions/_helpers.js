import prisma from '../db';
import { revalidateTag } from 'next/cache';
import { createOutboxEvent, DASHBOARD_EVENT_TOPICS } from '../dashboard/events';
import { invalidateDashboardCaches } from '../dashboard/read-models';

// ============================================================
// Shared Helpers — used across multiple action domains
// ============================================================

/**
 * Record a CattleHistory entry. Failures are logged but never
 * propagate to the caller so caller operations remain atomic.
 */
export async function recordCattleHistory(cattleId, eventType, eventDate, description, metadata = null) {
  try {
    await prisma.cattleHistory.create({
      data: {
        cattleId,
        eventType,
        eventDate: new Date(eventDate),
        description,
        metadata: metadata ? JSON.stringify(metadata) : null,
      }
    });
  } catch (error) {
    console.error("Failed to record cattle history:", error);
  }
}

/**
 * Invalidate dashboard read-model caches for the default farm.
 * Also invalidates Next.js framework-level "use cache" entries
 * via revalidateTag() so both cache layers stay consistent.
 */
export async function invalidateHomeCaches(options = {}) {
  try {
    await invalidateDashboardCaches({
      farmId: 'default',
      ...options,
    });
  } catch (error) {
    console.error('Failed to invalidate dashboard caches:', error);
  }

  // Invalidate Next.js "use cache" tags based on mutation scope
  try {
    revalidateTag('dashboard-summary');

    if (options.cattleListPages) {
      revalidateTag('cattle-list');
    }

    if (options.salesListPages) {
      revalidateTag('sales-list');
    }
  } catch (error) {
    console.error('Failed to revalidate cache tags:', error);
  }
}

export { prisma, createOutboxEvent, DASHBOARD_EVENT_TOPICS };

