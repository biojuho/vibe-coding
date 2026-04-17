'use server';

import { requireAuthenticatedSession } from '@/lib/auth-guard';
import { validateFarmSettingsInput } from '../action-validation.mjs';
import { prisma, invalidateHomeCaches } from './_helpers';

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
