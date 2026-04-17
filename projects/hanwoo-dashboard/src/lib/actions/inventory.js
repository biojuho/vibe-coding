'use server';

import { requireAuthenticatedSession } from '@/lib/auth-guard';
import { validateInventoryItemInput, validateInventoryQuantityInput } from '../action-validation.mjs';
import { prisma } from './_helpers';

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
