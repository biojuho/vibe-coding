'use server';

import { requireAuthenticatedSession } from '@/lib/auth-guard';
import prisma from './db';
import { revalidatePath } from 'next/cache';
import { isEstrusAlert, isCalvingAlert, getDaysUntilEstrus, getDaysUntilCalving } from './utils';
import { fetchMarketPrice } from './kape';
import { createOutboxEvent, DASHBOARD_EVENT_TOPICS } from './dashboard/events';
import { getLatestMarketPriceSnapshot, saveMarketPriceSnapshot, getNotificationSummary, saveNotificationSummary, invalidateDashboardCaches } from './dashboard/read-models';
import {
  buildUnavailableMarketPrice,
  normalizeCachedMarketPrice,
  normalizeLiveMarketPrice,
  shouldPersistLiveMarketPrice,
} from './market-price-state.mjs';
import {
  validateCattleMutationInput,
  validateExpenseRecordInput,
  validateFarmSettingsInput,
  validateFeedRecordInput,
  validateInventoryItemInput,
  validateInventoryQuantityInput,
  validateSalesRecordInput,
} from './action-validation.mjs';

// ============================================================
// Helper: CattleHistory 기록 (실패해도 부모 작업 중단 안 함)
// ============================================================

async function recordCattleHistory(cattleId, eventType, eventDate, description, metadata = null) {
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

async function invalidateHomeCaches(options = {}) {
  try {
    await invalidateDashboardCaches({
      farmId: 'default',
      ...options,
    });
  } catch (error) {
    console.error('Failed to invalidate dashboard caches:', error);
  }
}

// ============================================================
// Cattle Actions
// ============================================================

export async function getCattleList() {
  await requireAuthenticatedSession();
  try {
    const cattle = await prisma.cattle.findMany({
      where: { isArchived: false },
      orderBy: { updatedAt: 'desc' }
    });
    return cattle;
  } catch (error) {
    console.error("Failed to fetch cattle:", error);
    throw new Error("Failed to fetch cattle data.");
  }
}

export async function getArchivedCattle() {
  await requireAuthenticatedSession();
  try {
    return await prisma.cattle.findMany({
      where: { isArchived: true },
      orderBy: { archivedAt: 'desc' }
    });
  } catch (error) {
    console.error("Failed to fetch archived cattle:", error);
    return [];
  }
}

export async function createCattle(data) {
  await requireAuthenticatedSession();
  try {
    if (!data.tagNumber || !data.name) {
      return { success: false, message: "이름과 이력번호는 필수입니다." };
    }

    const validation = validateCattleMutationInput(data);
    if (!validation.success) {
      return validation;
    }

    const payload = validation.data;
    const created = await prisma.cattle.create({
      data: {
        tagNumber: payload.tagNumber,
        name: payload.name,
        birthDate: payload.birthDate,
        gender: payload.gender,
        status: payload.status,
        weight: payload.weight,
        buildingId: payload.buildingId,
        penNumber: payload.penNumber,
        memo: payload.memo,
        geneticFather: payload.geneticInfo.father,
        geneticMother: payload.geneticInfo.mother,
        geneticGrade: payload.geneticInfo.grade,
        lastEstrus: payload.lastEstrus,
        pregnancyDate: payload.pregnancyDate,
        purchasePrice: payload.purchasePrice,
        purchaseDate: payload.purchaseDate,
      }
    });

    await recordCattleHistory(created.id, 'purchase', new Date(), `신규 등록: ${data.name} (${data.tagNumber})`, {
      purchasePrice: payload.purchasePrice,
    });

    await createOutboxEvent({ topic: DASHBOARD_EVENT_TOPICS.cattleCreated, aggregateId: created.id, payload: { tagNumber: payload.tagNumber, name: payload.name } });
    await invalidateHomeCaches({ summary: true, notifications: true, cattleListPages: true });
    return { success: true, data: created };
  } catch (error) {
    console.error("Failed to create cattle:", error);
    return { success: false, message: error.message };
  }
}

export async function updateCattle(id, data) {
  await requireAuthenticatedSession();
  try {
    // 변경 전 기존값 조회 (이력 비교용)
    const validation = validateCattleMutationInput(data);
    if (!validation.success) {
      return validation;
    }

    const payload = validation.data;
    const existing = await prisma.cattle.findUnique({ where: { id } });

    const updated = await prisma.cattle.update({
      where: { id },
      data: {
        tagNumber: payload.tagNumber,
        name: payload.name,
        birthDate: payload.birthDate,
        gender: payload.gender,
        status: payload.status,
        weight: payload.weight,
        buildingId: payload.buildingId,
        penNumber: payload.penNumber,
        memo: payload.memo,
        geneticFather: payload.geneticInfo.father,
        geneticMother: payload.geneticInfo.mother,
        geneticGrade: payload.geneticInfo.grade,
        lastEstrus: payload.lastEstrus,
        pregnancyDate: payload.pregnancyDate,
        purchasePrice: payload.purchasePrice,
        purchaseDate: payload.purchaseDate,
      }
    });

    // 상태 변경 이력
    if (existing && existing.status !== payload.status) {
      await recordCattleHistory(id, 'status_change', new Date(), `상태 변경: ${existing.status} → ${data.status}`, {
        from: existing.status, to: payload.status,
      });
    }
    // 체중 변경 이력
    if (existing && existing.weight !== payload.weight) {
      await recordCattleHistory(id, 'weight', new Date(), `체중 변경: ${existing.weight}kg → ${data.weight}kg`, {
        from: existing.weight, to: payload.weight,
      });
    }
    // 이동 이력
    if (existing && (existing.buildingId !== payload.buildingId || existing.penNumber !== payload.penNumber)) {
      await recordCattleHistory(id, 'movement', new Date(), `이동: ${existing.buildingId} ${existing.penNumber}번 → ${data.buildingId} ${data.penNumber}번`, {
        fromBuilding: existing.buildingId, fromPen: existing.penNumber,
        toBuilding: payload.buildingId, toPen: payload.penNumber,
      });
    }

    await createOutboxEvent({ topic: DASHBOARD_EVENT_TOPICS.cattleUpdated, aggregateId: id, payload: { tagNumber: payload.tagNumber, name: payload.name } });
    await invalidateHomeCaches({ summary: true, notifications: true, cattleListPages: true });
    return { success: true, data: updated };
  } catch (error) {
    console.error("Failed to update cattle:", error);
    return { success: false, message: error.message };
  }
}

export async function recordCalving(data) {
  await requireAuthenticatedSession();
  try {
    const mother = await prisma.cattle.findUnique({
      where: { id: data.motherId },
    });

    if (!mother || mother.isArchived) {
      return { success: false, message: "분만 대상 개체를 찾을 수 없습니다." };
    }

    const calvingDate = new Date(data.calvingDate);
    const calfTagNumber = data.calfTagNumber;
    const calfGender = data.calfGender;
    const nextMemo = mother.memo
      ? `${mother.memo}\n[분만] ${data.calvingDate} ${calfGender} 송아지 분만`
      : `[분만] ${data.calvingDate} ${calfGender} 송아지 분만`;

    const result = await prisma.$transaction(async (tx) => {
      const updatedMother = await tx.cattle.update({
        where: { id: mother.id },
        data: {
          status: "번식우",
          pregnancyDate: null,
          lastEstrus: null,
          memo: nextMemo,
        },
      });

      const calf = await tx.cattle.create({
        data: {
          tagNumber: calfTagNumber,
          name: `${mother.name}의 송아지`,
          birthDate: calvingDate,
          gender: calfGender,
          status: "송아지",
          weight: 25,
          buildingId: mother.buildingId,
          penNumber: mother.penNumber,
          memo: `모체 ${mother.tagNumber} (${mother.name})`,
          geneticFather: mother.geneticFather || "미상",
          geneticMother: mother.tagNumber,
          geneticGrade: "-",
        },
      });

      const historyItems = [
        {
          cattleId: mother.id,
          eventType: "calving",
          eventDate: calvingDate,
          description: `분만 완료: ${calfGender} 송아지 (${calfTagNumber})`,
          metadata: JSON.stringify({
            calfId: calf.id,
            calfTagNumber,
            calfGender,
          }),
        },
      ];

      if (mother.status !== "번식우") {
        historyItems.push({
          cattleId: mother.id,
          eventType: "status_change",
          eventDate: calvingDate,
          description: `상태 변경: ${mother.status} → 번식우`,
          metadata: JSON.stringify({
            from: mother.status,
            to: "번식우",
          }),
        });
      }

      await tx.cattleHistory.createMany({
        data: historyItems,
      });

      return {
        mother: updatedMother,
        calf,
      };
    });

    await createOutboxEvent({ topic: DASHBOARD_EVENT_TOPICS.cattleUpdated, aggregateId: data.motherId, payload: { event: 'calving', calfTagNumber: data.calfTagNumber } });
    await invalidateHomeCaches({ summary: true, notifications: true, cattleListPages: true });
    return { success: true, data: result };
  } catch (error) {
    console.error("Failed to record calving:", error);
    return { success: false, message: error.message };
  }
}

export async function deleteCattle(id) {
  await requireAuthenticatedSession();
  try {
    // 판매기록 있으면 삭제 불가
    const salesCount = await prisma.salesRecord.count({ where: { cattleId: id } });
    if (salesCount > 0) {
      return { success: false, message: `이 개체에 ${salesCount}건의 판매 기록이 있어 삭제할 수 없습니다.` };
    }

    // 소프트 삭제
    await prisma.cattle.update({
      where: { id },
      data: { isArchived: true, archivedAt: new Date() }
    });

    await recordCattleHistory(id, 'status_change', new Date(), '아카이브 처리됨', { action: 'archive' });

    await createOutboxEvent({ topic: DASHBOARD_EVENT_TOPICS.cattleArchived, aggregateId: id, payload: { action: 'archive' } });
    await invalidateHomeCaches({ summary: true, notifications: true, cattleListPages: true });
    return { success: true, data: { id } };
  } catch (error) {
    console.error("Failed to archive cattle:", error);
    return { success: false, message: error.message };
  }
}

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
    return { success: false, message: e.message };
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

// ============================================================
// Inventory Actions
// ============================================================

export async function getInventory() {
  await requireAuthenticatedSession();
  try {
    return await prisma.inventoryItem.findMany({ orderBy: { category: 'asc' } });
  } catch (error) {
    console.error("Failed to fetch inventory:", error);
    return [];
  }
}

export async function addInventoryItem(data) {
  await requireAuthenticatedSession();
  try {
    const validation = validateInventoryItemInput(data);
    if (!validation.success) {
      return validation;
    }

    const payload = validation.data;
    const created = await prisma.inventoryItem.create({
      data: {
        name: payload.name,
        category: payload.category,
        quantity: payload.quantity,
        unit: payload.unit,
        threshold: payload.threshold,
      }
    });
    return { success: true, data: created };
  } catch (error) {
    return { success: false, message: error.message };
  }
}

export async function updateInventoryQuantity(id, quantity) {
  await requireAuthenticatedSession();
  try {
    const validation = validateInventoryQuantityInput(quantity);
    if (!validation.success) {
      return validation;
    }

    const updated = await prisma.inventoryItem.update({
      where: { id },
      data: { quantity: validation.data.quantity }
    });
    return { success: true, data: updated };
  } catch (error) {
    return { success: false, message: error.message };
  }
}

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

// ============================================================
// Building Actions
// ============================================================

export async function getBuildings() {
  await requireAuthenticatedSession();
  try {
    return await prisma.building.findMany({ orderBy: { name: 'asc' } });
  } catch (e) {
    console.error("Failed to fetch buildings:", e);
    return [];
  }
}

export async function createBuilding(data) {
  await requireAuthenticatedSession();
  try {
    const created = await prisma.building.create({
      data: { name: data.name, penCount: parseInt(data.penCount) }
    });
    return { success: true, data: created };
  } catch (e) {
    return { success: false, message: e.message };
  }
}

export async function deleteBuilding(id) {
  await requireAuthenticatedSession();
  try {
    const cattleCount = await prisma.cattle.count({ where: { buildingId: id, isArchived: false } });
    if (cattleCount > 0) {
      return { success: false, message: `이 축사에 ${cattleCount}두의 소가 있어 삭제할 수 없습니다. 먼저 소를 이동해주세요.` };
    }
    await prisma.building.delete({ where: { id } });
    return { success: true, data: { id } };
  } catch (e) {
    return { success: false, message: e.message };
  }
}

// ============================================================
// Farm Settings Actions
// ============================================================

export async function getFarmSettings() {
  await requireAuthenticatedSession();
  try {
    let settings = await prisma.farmSettings.findUnique({ where: { id: "default" } });
    if (!settings) {
      settings = await prisma.farmSettings.create({
        data: {
          id: "default",
          name: "Joolife × 남원 대산농장",
          location: "남원시 대산면",
          latitude: 35.446,
          longitude: 127.344,
        }
      });
    }
    return settings;
  } catch (e) {
    console.error("Failed to fetch farm settings:", e);
    return { name: "Joolife × 남원 대산농장", location: "남원시 대산면", latitude: 35.446, longitude: 127.344 };
  }
}

export async function updateFarmSettings(data) {
  await requireAuthenticatedSession();
  try {
    const validation = validateFarmSettingsInput(data);
    if (!validation.success) {
      return validation;
    }

    const payload = validation.data;
    const settings = await prisma.farmSettings.upsert({
      where: { id: "default" },
      update: { name: payload.name, location: payload.location, latitude: payload.latitude, longitude: payload.longitude },
      create: { id: "default", name: payload.name, location: payload.location, latitude: payload.latitude, longitude: payload.longitude },
    });
    await invalidateHomeCaches({ summary: true });
    return { success: true, data: settings };
  } catch (e) {
    return { success: false, message: e.message };
  }
}

// ============================================================
// Market Actions
// ============================================================

export async function getRealTimeMarketPrice() {
  await requireAuthenticatedSession();
  let cachedMarketPrice = null;

  try {
    const cached = await getLatestMarketPriceSnapshot();
    cachedMarketPrice = normalizeCachedMarketPrice(cached);

    if (cached && !cachedMarketPrice) {
      console.warn('Ignoring non-authoritative market price snapshot.', {
        fetchedAt: cached.fetchedAt,
        isRealtime: cached.isRealtime,
        source: cached.source,
      });
    }

    if (cachedMarketPrice && !cachedMarketPrice.isStale) {
      return cachedMarketPrice;
    }
  } catch (err) {
    console.error('Market price cache read failed (falling back to API):', err);
  }

  const marketPrice = normalizeLiveMarketPrice(await fetchMarketPrice());

  if (shouldPersistLiveMarketPrice(marketPrice)) {
    try {
      await saveMarketPriceSnapshot({
        issueDate: marketPrice.issueDate,
        isRealtime: true,
        bull: marketPrice.bull,
        cow: marketPrice.cow,
        source: 'KAPE',
      });
      await createOutboxEvent({
        topic: DASHBOARD_EVENT_TOPICS.marketPriceRefreshed,
        payload: { issueDate: marketPrice.issueDate, source: marketPrice.source },
      });
    } catch (err) {
      console.error('Market price snapshot save failed:', err);
    }

    return marketPrice;
  }

  if (cachedMarketPrice) {
    return cachedMarketPrice;
  }

  return buildUnavailableMarketPrice();
}

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
    const notifications = [];

    cattle.forEach(cow => {
      if ((cow.status === "번식우" || cow.status === "육성우") && cow.lastEstrus && isEstrusAlert(cow.lastEstrus)) {
        const daysLeft = getDaysUntilEstrus(cow.lastEstrus);
        notifications.push({
          id: `estrus-${cow.id}`,
          type: 'estrus',
          level: daysLeft <= 1 ? 'critical' : 'warning',
          title: daysLeft === 0 ? '🔥 발정 예정일' : '💕 발정 임박',
          message: `${cow.name} (${cow.tagNumber}) 발정 예정일이 ${daysLeft}일 남았습니다.`,
          date: new Date(),
        });
      }

      if (cow.status === "임신우" && cow.pregnancyDate && isCalvingAlert(cow.pregnancyDate)) {
        const daysLeft = getDaysUntilCalving(cow.pregnancyDate);
        notifications.push({
          id: `calving-${cow.id}`,
          type: 'calving',
          level: daysLeft <= 3 ? 'critical' : 'warning',
          title: daysLeft === 0 ? '🚨 분만 예정일' : '👶 분만 임박',
          message: `${cow.name} (${cow.tagNumber}) 분만 예정일이 ${daysLeft}일 남았습니다!`,
          date: new Date(),
        });
      }
    });

    notifications.sort((a, b) => {
      if (a.level === 'critical' && b.level !== 'critical') return -1;
      if (a.level !== 'critical' && b.level === 'critical') return 1;
      return 0;
    });

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

// ============================================================
// Expense Actions (신규)
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

// ============================================================
// CattleHistory Actions (신규)
// ============================================================

export async function getCattleHistory(cattleId) {
  await requireAuthenticatedSession();
  try {
    const history = await prisma.cattleHistory.findMany({
      where: { cattleId },
      orderBy: { eventDate: 'desc' },
    });
    return history.map(h => ({
      ...h,
      metadata: h.metadata ? JSON.parse(h.metadata) : null,
    }));
  } catch (error) {
    console.error("Failed to fetch cattle history:", error);
    return [];
  }
}

// ============================================================
// System Diagnostics
// ============================================================

export async function getSystemDiagnostics() {
  await requireAuthenticatedSession();
  try {
    const start = Date.now();
    const cattleCount = await prisma.cattle.count();
    const latency = Date.now() - start;
    return {
      success: true,
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      nodeVersion: process.version,
      database: {
        status: 'Online',
        latency: `${latency}ms`,
        recordCounts: {
          cattle: cattleCount,
          sales: await prisma.salesRecord.count(),
          feed: await prisma.feedRecord.count(),
          expenses: await prisma.expenseRecord.count(),
          histories: await prisma.cattleHistory.count(),
        }
      }
    };
  } catch (error) {
    return { success: false, timestamp: new Date().toISOString(), error: error.message, database: { status: 'Offline', latency: 'N/A' } };
  }
}

export async function getRawData(modelName) {
  await requireAuthenticatedSession();
  try {
    const allowedModels = ['cattle', 'salesRecord', 'feedRecord', 'scheduleEvent', 'inventoryItem', 'building', 'farmSettings', 'expenseRecord', 'cattleHistory'];
    if (!allowedModels.includes(modelName)) {
      throw new Error("Invalid model name");
    }
    const data = await prisma[modelName].findMany({
      take: 50,
      orderBy: { createdAt: 'desc' },
    });
    return { success: true, data };
  } catch (error) {
    return { success: false, message: error.message };
  }
}

export async function lookupCattleTag(tagNumber) {
  await requireAuthenticatedSession();
  const { lookupCattleByTag } = await import('./mtrace');
  return lookupCattleByTag(tagNumber);
}
