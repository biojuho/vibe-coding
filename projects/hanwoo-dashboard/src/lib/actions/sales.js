'use server';

import { requireAuthenticatedSession } from '@/lib/auth-guard';
import { validateSalesRecordInput } from '../action-validation.mjs';
import { prisma, createOutboxEvent, DASHBOARD_EVENT_TOPICS, recordCattleHistory, invalidateHomeCaches } from './_helpers';

// ============================================================
// Sales Actions
// ============================================================

export async function getSalesRecords() {
  await requireAuthenticatedSession();
  try {
    const sales = await prisma.salesRecord.findMany({
      orderBy: { saleDate: 'desc' }
    });
    return sales;
  } catch (error) {
    console.error("Failed to fetch sales:", error);
    throw new Error("Failed to fetch sales records.");
  }
}

export async function createSalesRecord(data) {
  await requireAuthenticatedSession();
  try {
    // cattleId 존재 검증
    const validation = validateSalesRecordInput(data);
    if (!validation.success) {
      return validation;
    }

    const payload = validation.data;
    if (payload.cattleId) {
      const cattle = await prisma.cattle.findUnique({ where: { id: payload.cattleId } });
      if (!cattle) return { success: false, message: "존재하지 않는 개체입니다." };
    }

    const created = await prisma.salesRecord.create({
      data: {
        saleDate: payload.saleDate,
        price: payload.price,
        purchaser: payload.purchaser,
        grade: payload.grade,
        cattleId: payload.cattleId,
      }
    });

    // 출하 이력
    if (payload.cattleId) {
      await recordCattleHistory(payload.cattleId, 'sale', payload.saleDate,
        `출하: ${parseInt(data.price).toLocaleString()}원 (등급: ${data.grade || '-'})`,
        { price: payload.price, grade: payload.grade, purchaser: payload.purchaser }
      );
    }

    await createOutboxEvent({ topic: DASHBOARD_EVENT_TOPICS.saleRecorded, aggregateId: payload.cattleId || null, payload: { price: payload.price, grade: payload.grade } });
    await invalidateHomeCaches({ summary: true, salesListPages: true });
    return { success: true, data: created };
  } catch (error) {
    console.error("Failed to create sales record:", error);
    return { success: false, message: error.message };
  }
}
