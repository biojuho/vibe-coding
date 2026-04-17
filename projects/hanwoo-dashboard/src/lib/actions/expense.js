'use server';

import { requireAuthenticatedSession } from '@/lib/auth-guard';
import { revalidatePath } from 'next/cache';
import { validateExpenseRecordInput } from '../action-validation.mjs';
import { prisma, createOutboxEvent, DASHBOARD_EVENT_TOPICS, invalidateHomeCaches } from './_helpers';

// ============================================================
// Expense Actions
// ============================================================

export async function getExpenseRecords(filters = {}) {
  await requireAuthenticatedSession();
  try {
    const where = {};
    if (filters.cattleId) where.cattleId = filters.cattleId;
    if (filters.buildingId) where.buildingId = filters.buildingId;
    if (filters.category) where.category = filters.category;
    if (filters.fromDate || filters.toDate) {
      where.date = {};
      if (filters.fromDate) where.date.gte = new Date(filters.fromDate);
      if (filters.toDate) where.date.lte = new Date(filters.toDate);
    }

    return await prisma.expenseRecord.findMany({
      where,
      orderBy: { date: 'desc' },
    });
  } catch (error) {
    console.error("Failed to fetch expenses:", error);
    return [];
  }
}

export async function createExpenseRecord(data) {
  await requireAuthenticatedSession();
  try {
    const validation = validateExpenseRecordInput(data);
    if (!validation.success) {
      return validation;
    }

    const payload = validation.data;
    if (!data.date || !data.category || !data.amount) {
      return { success: false, message: "날짜, 카테고리, 금액은 필수입니다." };
    }
    if (payload.cattleId) {
      const cattle = await prisma.cattle.findUnique({ where: { id: payload.cattleId } });
      if (!cattle) return { success: false, message: "존재하지 않는 개체입니다." };
    }
    if (payload.buildingId) {
      const building = await prisma.building.findUnique({ where: { id: payload.buildingId } });
      if (!building) return { success: false, message: "존재하지 않는 축사입니다." };
    }

    const created = await prisma.expenseRecord.create({
      data: {
        date: payload.date,
        cattleId: payload.cattleId,
        buildingId: payload.buildingId,
        category: payload.category,
        amount: payload.amount,
        description: payload.description,
      }
    });
    await createOutboxEvent({
      topic: DASHBOARD_EVENT_TOPICS.expenseRecorded,
      aggregateId: payload.cattleId || payload.buildingId || null,
      payload: { category: payload.category, amount: payload.amount },
    });
    await invalidateHomeCaches({ summary: true });
    revalidatePath('/');
    return { success: true, data: created };
  } catch (error) {
    console.error("Failed to create expense:", error);
    return { success: false, message: error.message };
  }
}

export async function getExpenseAggregation() {
  await requireAuthenticatedSession();
  try {
    const expenses = await prisma.expenseRecord.findMany();
    const byCategory = {};
    expenses.forEach(e => {
      byCategory[e.category] = (byCategory[e.category] || 0) + e.amount;
    });
    return byCategory;
  } catch (error) {
    console.error("Failed to aggregate expenses:", error);
    return {};
  }
}
