'use server';

import { requireAuthenticatedSession } from '@/lib/auth-guard';
import { normalizeCattleHistoryRows } from '../cattle-history.mjs';
import { validateCattleMutationInput } from '../action-validation.mjs';
import { prisma, createOutboxEvent, DASHBOARD_EVENT_TOPICS, recordCattleHistory, invalidateHomeCaches } from './_helpers';

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
// CattleHistory Actions
// ============================================================

export async function getCattleHistory(cattleId) {
  await requireAuthenticatedSession();
  try {
    const history = await prisma.cattleHistory.findMany({
      where: { cattleId },
      orderBy: { eventDate: 'desc' },
    });
    return normalizeCattleHistoryRows(history);
  } catch (error) {
    console.error("Failed to fetch cattle history:", error);
    return [];
  }
}
