'use server';

import { requireAuthenticatedSession } from '@/lib/auth-guard';
import { prisma } from './_helpers';

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
