import prisma from '../db';
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
}

export { prisma, createOutboxEvent, DASHBOARD_EVENT_TOPICS };
