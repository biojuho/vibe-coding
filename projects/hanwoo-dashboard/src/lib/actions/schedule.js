'use server';

import { requireAuthenticatedSession } from '@/lib/auth-guard';
import { prisma } from './_helpers';

// ============================================================
// Schedule Actions
// ============================================================

export async function getScheduleEvents() {
  await requireAuthenticatedSession();
  try {
    return await prisma.scheduleEvent.findMany({ orderBy: { date: 'asc' } });
  } catch (e) {
    console.error("Failed to fetch schedule:", e);
    return [];
  }
}

export async function createScheduleEvent(data) {
  await requireAuthenticatedSession();
  try {
    const created = await prisma.scheduleEvent.create({
      data: {
        title: data.title,
        date: new Date(data.date),
        type: data.type,
        cattleId: data.cattleId || null,
      }
    });
    return { success: true, data: created };
  } catch (e) {
    return { success: false, message: e.message };
  }
}

export async function toggleEventCompletion(id, isCompleted) {
  await requireAuthenticatedSession();
  try {
    const updated = await prisma.scheduleEvent.update({
      where: { id },
      data: { isCompleted }
    });
    return { success: true, data: updated };
  } catch (e) {
    return { success: false, message: e.message };
  }
}
