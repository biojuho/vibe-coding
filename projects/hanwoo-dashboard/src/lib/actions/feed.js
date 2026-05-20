'use server';

import { requireAuthenticatedSession } from '@/lib/auth-guard';
import { validateFeedRecordInput } from '../action-validation.mjs';
import { prisma } from './_helpers';

// ============================================================
// Feed Actions
// ============================================================

export async function getFeedStandards() {
  await requireAuthenticatedSession();
  try {
    return await prisma.feedStandard.findMany();
  } catch (error) {
    console.error("Failed to fetch feed standards:", error);
    return [];
  }
}

export async function recordFeed(data) {
  await requireAuthenticatedSession();
  try {
    const validation = validateFeedRecordInput(data);
    if (!validation.success) {
      return validation;
    }

    const payload = validation.data;
    const created = await prisma.feedRecord.create({
      data: {
        date: payload.date,
        buildingId: payload.buildingId,
        penNumber: payload.penNumber,
        roughage: payload.roughage,
        concentrate: payload.concentrate,
        note: payload.note,
      }
    });
    return { success: true, data: created };
  } catch (e) {
    console.error("Failed to record feed:", e);
    return { success: false, message: "급여 기록을 저장하지 못했습니다." };
  }
}

export async function getFeedHistory() {
  await requireAuthenticatedSession();
  try {
    return await prisma.feedRecord.findMany({
      orderBy: { date: 'desc' },
      take: 20,
    });
  } catch (e) {
    console.error("Failed to fetch feed history:", e);
    return [];
  }
}
