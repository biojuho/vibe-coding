'use server';

import { requireAuthenticatedSession } from '@/lib/auth-guard';
import { getProfitabilityEstimates } from '../dashboard/profitability-service';
import { prisma } from './_helpers';

// ============================================================
// System Diagnostics & Utilities
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
  const { lookupCattleByTag } = await import('../mtrace');
  return lookupCattleByTag(tagNumber);
}

// ============================================================
// Profitability Actions
// ============================================================

export async function getProfitabilityData() {
  await requireAuthenticatedSession();
  return await getProfitabilityEstimates();
}
