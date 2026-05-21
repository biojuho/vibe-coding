import { GoogleGenerativeAI } from '@google/generative-ai';

import {
  createAiChatSseStream,
  handleAiChatRequest,
} from '@/lib/ai-chat-api.mjs';
import { requireAuthenticatedSession } from '@/lib/auth-guard';
import prisma from '@/lib/db';
import { toFiniteNumber } from '@/lib/utils';

const SYSTEM_INSTRUCTION = `
당신은 한우 농가 운영자를 돕는 Joolife AI 농장 비서입니다.
기본적으로 한국어로 답변하고, 제공된 농장 데이터를 근거로 간결하고 실행 가능한 조언을 주세요.
데이터가 없거나 불확실한 경우 확인이 필요하다고 명확히 말하세요.
응급 질병이나 수의학적 상황은 전문 수의사에게 상담하도록 안내하세요.
`;

function formatSaleDateForContext(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '출하일 미등록' : date.toISOString().slice(0, 10);
}

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
            const cattleName = sale.cattle?.name || '개체명 미등록';
            const tagNumber = sale.cattle?.tagNumber || '이력번호 미등록';
            const priceManwon = (toFiniteNumber(sale.price) / 10000).toFixed(0);
            const saleDate = formatSaleDateForContext(sale.saleDate);
            return `${cattleName}(${tagNumber}) ${priceManwon}만원 (${saleDate})`;
          })
          .join('\n  ')
      : '최근 판매 기록 없음';

    return `
## 현재 농장 정보
- 농장: ${farmSettings?.name || 'Joolife 한우 농장'}
- 운영 개체: ${cattleCount}
- 축사: ${buildingCount}
- 상태별 개체 수: ${statusSummary || '데이터 없음'}
- 최근 판매:
  ${salesSummary}`;
  } catch (error) {
    console.error('AI 농장 컨텍스트 구성 실패:', error);
    return '\n## 현재 농장 정보\n농장 데이터를 불러오지 못했습니다. 일반적인 한우 농장 운영 기준으로 답변해 주세요.';
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
