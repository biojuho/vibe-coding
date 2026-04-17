'use server';

import { requireAuthenticatedSession } from '@/lib/auth-guard';
import { getNotificationSummary, saveNotificationSummary } from '../dashboard/read-models';
import { buildNotifications } from '../notifications';
import { prisma } from './_helpers';

// ============================================================
// Notification Actions
// ============================================================

export async function getNotifications() {
  await requireAuthenticatedSession();
  try {
    // Try pre-computed read model first
    const cached = await getNotificationSummary('default');
    if (cached?.payload) {
      const age = Date.now() - new Date(cached.generatedAt).getTime();
      if (age < 60 * 1000) {
        return cached.payload;
      }
    }
  } catch {
    // Fall through to live computation
  }

  try {
    const cattle = await prisma.cattle.findMany({ where: { isArchived: false } });
    const notifications = buildNotifications(cattle);

    // Persist for future cache hits
    try {
      await saveNotificationSummary({ farmId: 'default', payload: notifications });
    } catch {
      // Non-fatal: cache write failure
    }

    return notifications;
  } catch (error) {
    console.error("Failed to get notifications:", error);
    return [];
  }
}
