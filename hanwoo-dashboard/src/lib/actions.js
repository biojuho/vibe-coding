'use server';

import prisma from './db';
import { revalidatePath } from 'next/cache';
import { isEstrusAlert, isCalvingAlert, getDaysUntilEstrus, getDaysUntilCalving } from './utils';
import { fetchMarketPrice } from './kape';

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

// ============================================================
// Cattle Actions
// ============================================================

export async function getCattleList() {
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
  try {
    if (!data.tagNumber || !data.name) {
      return { success: false, message: "이름과 이력번호는 필수입니다." };
    }

    const created = await prisma.cattle.create({
      data: {
        tagNumber: data.tagNumber,
        name: data.name,
        birthDate: new Date(data.birthDate),
        gender: data.gender,
        status: data.status,
        weight: parseFloat(data.weight),
        buildingId: data.buildingId,
        penNumber: parseInt(data.penNumber),
        memo: data.memo || "",
        geneticFather: data.geneticInfo?.father,
        geneticMother: data.geneticInfo?.mother,
        geneticGrade: data.geneticInfo?.grade,
        lastEstrus: data.lastEstrus ? new Date(data.lastEstrus) : null,
        pregnancyDate: data.pregnancyDate ? new Date(data.pregnancyDate) : null,
        purchasePrice: data.purchasePrice ? parseInt(data.purchasePrice) : null,
        purchaseDate: data.purchaseDate ? new Date(data.purchaseDate) : null,
      }
    });

    await recordCattleHistory(created.id, 'purchase', new Date(), `신규 등록: ${data.name} (${data.tagNumber})`, {
      purchasePrice: data.purchasePrice ? parseInt(data.purchasePrice) : null,
    });

    revalidatePath('/');
    return { success: true };
  } catch (error) {
    console.error("Failed to create cattle:", error);
    return { success: false, message: error.message };
  }
}

export async function updateCattle(id, data) {
  try {
    // 변경 전 기존값 조회 (이력 비교용)
    const existing = await prisma.cattle.findUnique({ where: { id } });

    await prisma.cattle.update({
      where: { id },
      data: {
        tagNumber: data.tagNumber,
        name: data.name,
        birthDate: new Date(data.birthDate),
        gender: data.gender,
        status: data.status,
        weight: parseFloat(data.weight),
        buildingId: data.buildingId,
        penNumber: parseInt(data.penNumber),
        memo: data.memo || "",
        geneticFather: data.geneticInfo?.father,
        geneticMother: data.geneticInfo?.mother,
        geneticGrade: data.geneticInfo?.grade,
        lastEstrus: data.lastEstrus ? new Date(data.lastEstrus) : null,
        pregnancyDate: data.pregnancyDate ? new Date(data.pregnancyDate) : null,
        purchasePrice: data.purchasePrice ? parseInt(data.purchasePrice) : null,
        purchaseDate: data.purchaseDate ? new Date(data.purchaseDate) : null,
      }
    });

    // 상태 변경 이력
    if (existing && existing.status !== data.status) {
      await recordCattleHistory(id, 'status_change', new Date(), `상태 변경: ${existing.status} → ${data.status}`, {
        from: existing.status, to: data.status,
      });
    }
    // 체중 변경 이력
    if (existing && existing.weight !== parseFloat(data.weight)) {
      await recordCattleHistory(id, 'weight', new Date(), `체중 변경: ${existing.weight}kg → ${data.weight}kg`, {
        from: existing.weight, to: parseFloat(data.weight),
      });
    }
    // 이동 이력
    if (existing && (existing.buildingId !== data.buildingId || existing.penNumber !== parseInt(data.penNumber))) {
      await recordCattleHistory(id, 'movement', new Date(), `이동: ${existing.buildingId} ${existing.penNumber}번 → ${data.buildingId} ${data.penNumber}번`, {
        fromBuilding: existing.buildingId, fromPen: existing.penNumber,
        toBuilding: data.buildingId, toPen: parseInt(data.penNumber),
      });
    }

    revalidatePath('/');
    return { success: true };
  } catch (error) {
    console.error("Failed to update cattle:", error);
    return { success: false, message: error.message };
  }
}

export async function recordCalving(data) {
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

    revalidatePath('/');
    return { success: true, data: result };
  } catch (error) {
    console.error("Failed to record calving:", error);
    return { success: false, message: error.message };
  }
}

export async function deleteCattle(id) {
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

    revalidatePath('/');
    return { success: true };
  } catch (error) {
    console.error("Failed to archive cattle:", error);
    return { success: false, message: error.message };
  }
}

// ============================================================
// Sales Actions
// ============================================================

export async function getSalesRecords() {
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
  try {
    // cattleId 존재 검증
    if (data.cattleId) {
      const cattle = await prisma.cattle.findUnique({ where: { id: data.cattleId } });
      if (!cattle) return { success: false, message: "존재하지 않는 개체입니다." };
    }

    await prisma.salesRecord.create({
      data: {
        saleDate: new Date(data.saleDate),
        price: parseInt(data.price),
        purchaser: data.purchaser,
        grade: data.grade,
        cattleId: data.cattleId,
      }
    });

    // 출하 이력
    if (data.cattleId) {
      await recordCattleHistory(data.cattleId, 'sale', new Date(data.saleDate),
        `출하: ${parseInt(data.price).toLocaleString()}원 (등급: ${data.grade || '-'})`,
        { price: parseInt(data.price), grade: data.grade, purchaser: data.purchaser }
      );
    }

    revalidatePath('/');
    return { success: true };
  } catch (error) {
    console.error("Failed to create sales record:", error);
    return { success: false, message: error.message };
  }
}

// ============================================================
// Feed Actions
// ============================================================

export async function getFeedStandards() {
  try {
    return await prisma.feedStandard.findMany();
  } catch (error) {
    console.error("Failed to fetch feed standards:", error);
    return [];
  }
}

export async function recordFeed(data) {
  try {
    await prisma.feedRecord.create({
      data: {
        date: new Date(data.date),
        buildingId: data.buildingId,
        penNumber: data.penNumber ? parseInt(data.penNumber) : null,
        roughage: parseFloat(data.roughage),
        concentrate: parseFloat(data.concentrate),
        note: data.note || null,
      }
    });
    revalidatePath('/');
    return { success: true };
  } catch (e) {
    return { success: false, message: e.message };
  }
}

export async function getFeedHistory() {
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
  try {
    return await prisma.inventoryItem.findMany({ orderBy: { category: 'asc' } });
  } catch (error) {
    console.error("Failed to fetch inventory:", error);
    return [];
  }
}

export async function addInventoryItem(data) {
  try {
    await prisma.inventoryItem.create({
      data: {
        name: data.name,
        category: data.category,
        quantity: parseFloat(data.quantity),
        unit: data.unit,
        threshold: data.threshold ? parseFloat(data.threshold) : null,
      }
    });
    revalidatePath('/');
    return { success: true };
  } catch (error) {
    return { success: false, message: error.message };
  }
}

export async function updateInventoryQuantity(id, quantity) {
  try {
    await prisma.inventoryItem.update({
      where: { id },
      data: { quantity: parseFloat(quantity) }
    });
    revalidatePath('/');
    return { success: true };
  } catch (error) {
    return { success: false, message: error.message };
  }
}

// ============================================================
// Schedule Actions
// ============================================================

export async function getScheduleEvents() {
  try {
    return await prisma.scheduleEvent.findMany({ orderBy: { date: 'asc' } });
  } catch (e) {
    console.error("Failed to fetch schedule:", e);
    return [];
  }
}

export async function createScheduleEvent(data) {
  try {
    await prisma.scheduleEvent.create({
      data: {
        title: data.title,
        date: new Date(data.date),
        type: data.type,
        cattleId: data.cattleId || null,
      }
    });
    revalidatePath('/');
    return { success: true };
  } catch (e) {
    return { success: false, message: e.message };
  }
}

export async function toggleEventCompletion(id, isCompleted) {
  try {
    await prisma.scheduleEvent.update({
      where: { id },
      data: { isCompleted }
    });
    revalidatePath('/');
    return { success: true };
  } catch (e) {
    return { success: false, message: e.message };
  }
}

// ============================================================
// Building Actions
// ============================================================

export async function getBuildings() {
  try {
    return await prisma.building.findMany({ orderBy: { name: 'asc' } });
  } catch (e) {
    console.error("Failed to fetch buildings:", e);
    return [];
  }
}

export async function createBuilding(data) {
  try {
    await prisma.building.create({
      data: { name: data.name, penCount: parseInt(data.penCount) }
    });
    revalidatePath('/');
    return { success: true };
  } catch (e) {
    return { success: false, message: e.message };
  }
}

export async function deleteBuilding(id) {
  try {
    const cattleCount = await prisma.cattle.count({ where: { buildingId: id, isArchived: false } });
    if (cattleCount > 0) {
      return { success: false, message: `이 축사에 ${cattleCount}두의 소가 있어 삭제할 수 없습니다. 먼저 소를 이동해주세요.` };
    }
    await prisma.building.delete({ where: { id } });
    revalidatePath('/');
    return { success: true };
  } catch (e) {
    return { success: false, message: e.message };
  }
}

// ============================================================
// Farm Settings Actions
// ============================================================

export async function getFarmSettings() {
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
  try {
    const settings = await prisma.farmSettings.upsert({
      where: { id: "default" },
      update: { name: data.name, location: data.location, latitude: parseFloat(data.latitude), longitude: parseFloat(data.longitude) },
      create: { id: "default", name: data.name, location: data.location, latitude: parseFloat(data.latitude), longitude: parseFloat(data.longitude) },
    });
    revalidatePath('/');
    return { success: true, data: settings };
  } catch (e) {
    return { success: false, message: e.message };
  }
}

// ============================================================
// Market Actions
// ============================================================

export async function getRealTimeMarketPrice() {
  return await fetchMarketPrice();
}

// ============================================================
// Notification Actions
// ============================================================

export async function getNotifications() {
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
  try {
    if (!data.date || !data.category || !data.amount) {
      return { success: false, message: "날짜, 카테고리, 금액은 필수입니다." };
    }
    if (data.cattleId) {
      const cattle = await prisma.cattle.findUnique({ where: { id: data.cattleId } });
      if (!cattle) return { success: false, message: "존재하지 않는 개체입니다." };
    }
    if (data.buildingId) {
      const building = await prisma.building.findUnique({ where: { id: data.buildingId } });
      if (!building) return { success: false, message: "존재하지 않는 축사입니다." };
    }

    await prisma.expenseRecord.create({
      data: {
        date: new Date(data.date),
        cattleId: data.cattleId || null,
        buildingId: data.buildingId || null,
        category: data.category,
        amount: parseInt(data.amount),
        description: data.description || null,
      }
    });
    revalidatePath('/');
    return { success: true };
  } catch (error) {
    console.error("Failed to create expense:", error);
    return { success: false, message: error.message };
  }
}

export async function getExpenseAggregation() {
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
  const { lookupCattleByTag } = await import('./mtrace');
  return lookupCattleByTag(tagNumber);
}
