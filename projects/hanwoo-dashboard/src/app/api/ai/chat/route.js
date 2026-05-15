import { GoogleGenerativeAI } from '@google/generative-ai';

import {
  createAiChatSseStream,
  handleAiChatRequest,
} from '@/lib/ai-chat-api.mjs';
import { requireAuthenticatedSession } from '@/lib/auth-guard';
import prisma from '@/lib/db';

const SYSTEM_INSTRUCTION = `
You are the Joolife AI farm assistant for Hanwoo cattle farm operators.
Answer in Korean by default. Keep answers concise, practical, and grounded in the provided farm data.
If data is missing or uncertain, say that the information needs to be checked.
For urgent medical or veterinary situations, recommend contacting a professional veterinarian.
`;

async function buildFarmContext() {
  try {
    const [cattleCount, buildingCount, recentSales, farmSettings] = await Promise.all([
      prisma.cattle.count({ where: { isArchived: false } }),
      prisma.building.count(),
      prisma.salesRecord.findMany({
        orderBy: { saleDate: 'desc' },
        take: 3,
        include: { cattle: { select: { name: true, tagNumber: true } } },
      }),
      prisma.farmSettings.findFirst(),
    ]);

    const statusCounts = await prisma.cattle.groupBy({
      by: ['status'],
      where: { isArchived: false },
      _count: true,
    });

    const statusSummary = statusCounts
      .map((item) => `${item.status}: ${item._count}`)
      .join(', ');

    const salesSummary = recentSales.length > 0
      ? recentSales
          .map((sale) => {
            const cattleName = sale.cattle?.name || 'unknown';
            const tagNumber = sale.cattle?.tagNumber || '-';
            const priceManwon = (sale.price / 10000).toFixed(0);
            const saleDate = new Date(sale.saleDate).toISOString().slice(0, 10);
            return `${cattleName}(${tagNumber}) ${priceManwon}man KRW (${saleDate})`;
          })
          .join('\n  ')
      : 'No recent sales records.';

    return `
## Current farm context
- Farm: ${farmSettings?.name || 'Joolife Farm'}
- Active cattle: ${cattleCount}
- Buildings: ${buildingCount}
- Status counts: ${statusSummary || 'No data'}
- Recent sales:
  ${salesSummary}`;
  } catch (error) {
    console.error('Failed to build farm context:', error);
    return '\n## Current farm context\nFarm data could not be loaded. Answer using general Hanwoo farm guidance.';
  }
}

function createGeminiChatStream({ apiKey, message, history, systemInstruction }) {
  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({
    model: 'gemini-2.0-flash',
    systemInstruction,
  });

  const chat = model.startChat({ history });
  return createAiChatSseStream({ chat, message });
}

export async function POST(request) {
  return handleAiChatRequest(request, {
    authenticate: requireAuthenticatedSession,
    getApiKey: () => process.env.GEMINI_API_KEY,
    buildFarmContext,
    createChatStream: createGeminiChatStream,
    systemInstruction: SYSTEM_INSTRUCTION,
  });
}
