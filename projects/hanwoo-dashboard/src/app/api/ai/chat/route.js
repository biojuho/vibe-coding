import { GoogleGenerativeAI } from '@google/generative-ai';
import prisma from '@/lib/db';

export const dynamic = 'force-dynamic';

// ------------------------------------------------------------------
// Gemini AI Chat Endpoint — Streaming SSE
// POST /api/ai/chat
// Body: { message: string, history: [{role, parts}] }
// ------------------------------------------------------------------

const SYSTEM_INSTRUCTION = `당신은 "Joolife AI 농장 비서"입니다.
한우 농장 경영주를 돕는 전문가 수준의 어시스턴트입니다.

## 역할
- 한우 사양관리(급여, 체중, 발정, 분만, 질병) 상담
- 경영 분석 (비용 구조, 출하 타이밍, 수익성)
- 시세 해석 및 출하 전략 조언
- 재고 관리 및 일정 관리 도움

## 규칙
1. 항상 한국어로 답변합니다.
2. 농장 데이터가 제공되면 그것을 근거로 구체적인 조언을 합니다.
3. 확실하지 않은 정보는 "정확한 확인이 필요합니다"라고 명시합니다.
4. 답변은 간결하고 실용적으로, 3~5줄 이내를 기본으로 합니다.
5. 이모지를 적절히 사용하여 친근한 톤을 유지합니다.
6. 의학적/수의학적 긴급 상황은 항상 수의사 상담을 권고합니다.`;

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
      .map((s) => `${s.status}: ${s._count}두`)
      .join(', ');

    const salesSummary = recentSales.length > 0
      ? recentSales.map((s) =>
          `${s.cattle?.name || '이름없음'}(${s.cattle?.tagNumber || '-'}) → ${(s.price / 10000).toFixed(0)}만원 (${new Date(s.saleDate).toLocaleDateString('ko-KR')})`
        ).join('\n  ')
      : '최근 출하 기록 없음';

    return `
## 현재 농장 현황
- 농장명: ${farmSettings?.name || 'Joolife Farm'}
- 총 사육두수: ${cattleCount}두 (축사 ${buildingCount}동)
- 상태별: ${statusSummary || '데이터 없음'}
- 최근 출하:
  ${salesSummary}`;
  } catch (error) {
    console.error('Failed to build farm context:', error);
    return '\n## 농장 데이터를 불러오지 못했습니다. 일반적인 한우 관련 질문에 답변합니다.';
  }
}

export async function POST(request) {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    return Response.json(
      { error: 'GEMINI_API_KEY가 설정되지 않았습니다.' },
      { status: 500 },
    );
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: '잘못된 요청 형식입니다.' }, { status: 400 });
  }

  const { message, history = [] } = body;
  if (!message || typeof message !== 'string') {
    return Response.json({ error: '메시지가 필요합니다.' }, { status: 400 });
  }

  // --- Build context-enriched system instruction ---
  const farmContext = await buildFarmContext();
  const fullSystemInstruction = `${SYSTEM_INSTRUCTION}\n${farmContext}`;

  // --- Gemini setup ---
  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({
    model: 'gemini-2.0-flash',
    systemInstruction: fullSystemInstruction,
  });

  // Convert history format: [{role:'user'|'system', content:string}]
  // → Gemini format: [{role:'user'|'model', parts:[{text}]}]
  const geminiHistory = history
    .filter((m) => m.role === 'user' || m.role === 'system')
    .map((m) => ({
      role: m.role === 'system' ? 'model' : 'user',
      parts: [{ text: m.content }],
    }));

  const chat = model.startChat({ history: geminiHistory });

  // --- Streaming response via SSE ---
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      try {
        const result = await chat.sendMessageStream(message);

        for await (const chunk of result.stream) {
          const text = chunk.text();
          if (text) {
            controller.enqueue(
              encoder.encode(`data: ${JSON.stringify({ text })}\n\n`),
            );
          }
        }

        controller.enqueue(encoder.encode('data: [DONE]\n\n'));
        controller.close();
      } catch (error) {
        console.error('Gemini streaming error:', error);
        const errorMsg = error.message?.includes('API_KEY')
          ? 'API 키가 유효하지 않습니다.'
          : '답변 생성 중 오류가 발생했습니다.';
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ error: errorMsg })}\n\n`),
        );
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
