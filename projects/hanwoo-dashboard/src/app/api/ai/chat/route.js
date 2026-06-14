import { GoogleGenerativeAI } from "@google/generative-ai";

import {
	createAiChatSseStream,
	handleAiChatRequest,
} from "@/lib/ai-chat-api.mjs";
import { requireAuthenticatedSession } from "@/lib/auth-guard";
import prisma from "@/lib/db";
import { checkRateLimit } from "@/lib/rate-limit.mjs";
import { getSubscriptionStatus } from "@/lib/subscription-queries";
import { toFiniteNumber } from "@/lib/utils";

const SYSTEM_INSTRUCTION = `
당신은 한우 농가 운영자를 돕는 Joolife AI 농장 비서입니다.

## 역할과 목표
- 기본적으로 한국어로 답변하고, 제공된 농장 정보를 근거로 간결하고 실행 가능한 조언을 주세요.
- 사용자의 질문을 한우 농장 운영 맥락으로 해석하되, 질문에 없는 개체명, 이력번호, 날짜, 수치, 진단명은 만들어내지 마세요.
- 정보가 없거나 불확실한 경우 확인이 필요하다고 명확히 말해 주세요.

## 답변 방식
- 첫 문장은 현재 판단의 전제를 짧게 말하세요.
- 이어서 "오늘 확인할 것" 또는 "바로 할 일" 중심으로 3~5개의 구체적인 항목을 제시하세요.
- 제공된 농장 정보가 부족할 때는 일반 기준과 추가로 확인할 정보를 분리하세요.
- 마지막에는 "다음에 확인할 정보:" 형식으로 필요한 입력값을 1줄로 정리하세요.

## 안전과 한계
- 응급 질병이나 수의학적 상황은 전문 수의사에게 상담하도록 안내해 주세요.
- 치료제, 투약량, 확정 진단은 지시하지 말고 관찰 기록, 격리, 전문가 상담 같은 안전한 운영 행동으로 제한하세요.

## 예시 형식
전제: 제공된 농장 정보만으로는 특정 개체를 확정할 수 없습니다.
오늘 확인할 것:
- 이력번호와 마지막 발정일을 기록하세요.
- 승가 허용, 점액, 활동량 증가를 같은 시간대에 다시 확인하세요.
다음에 확인할 정보: 개체 이력번호, 마지막 발정일, 분만/수정 이력
`;

function formatSaleDateForContext(value) {
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) {
		return "출하일 미등록";
	}

	if (typeof value === "string") {
		const dateKey = value.trim().slice(0, 10);
		if (
			/^\d{4}-\d{2}-\d{2}$/.test(dateKey) &&
			date.toISOString().slice(0, 10) !== dateKey
		) {
			return "출하일 미등록";
		}
	}

	return date.toISOString().slice(0, 10);
}

function isFarmContextRow(value) {
	return (
		value !== null &&
		typeof value === "object" &&
		!Array.isArray(value)
	);
}

function normalizeFarmContextRows(rows) {
	return Array.isArray(rows) ? rows.filter((row) => isFarmContextRow(row)) : [];
}

function normalizeStatusCountLabel(value) {
	return typeof value === "string" && value.trim()
		? value.trim()
		: "상태 미등록";
}

function normalizeStatusCountValue(value) {
	if (isFarmContextRow(value._count)) {
		return toFiniteNumber(value._count._all);
	}

	return toFiniteNumber(value._count);
}

async function buildFarmContext() {
	try {
		const [cattleCount, buildingCount, recentSales, farmSettings] =
			await Promise.all([
				prisma.cattle.count({ where: { isArchived: false } }),
				prisma.building.count(),
				prisma.salesRecord.findMany({
					orderBy: { saleDate: "desc" },
					take: 3,
					include: { cattle: { select: { name: true, tagNumber: true } } },
				}),
				prisma.farmSettings.findFirst(),
			]);

		const statusCounts = await prisma.cattle.groupBy({
			by: ["status"],
			where: { isArchived: false },
			_count: true,
		});
		const safeStatusCounts = normalizeFarmContextRows(statusCounts);
		const safeRecentSales = normalizeFarmContextRows(recentSales);

		const statusSummary = safeStatusCounts
			.map(
				(item) =>
					`${normalizeStatusCountLabel(item.status)}: ${normalizeStatusCountValue(item)}`,
			)
			.join(", ");

		const salesSummary =
			safeRecentSales.length > 0
				? safeRecentSales
						.map((rawSale) => {
							const sale = {
								...rawSale,
								cattle: isFarmContextRow(rawSale.cattle) ? rawSale.cattle : {},
							};
							const cattleName = sale.cattle.name || "개체명 미등록";
							const tagNumber = sale.cattle.tagNumber || "이력번호 미등록";
				const priceManwon = (toFiniteNumber(sale.price) / 10000).toFixed(0);
							const saleDate = formatSaleDateForContext(sale.saleDate);
							return `${cattleName}(${tagNumber}) ${priceManwon}만원 (${saleDate})`;
						})
						.join("\n  ")
				: "최근 판매 기록 없음";

		return `
## 현재 농장 정보
- 농장 정보 연결 상태: 실시간 조회 성공
- 농장: ${farmSettings?.name || "Joolife 한우 농장"}
- 운영 개체: ${cattleCount}
- 축사: ${buildingCount}
- 상태별 개체 수: ${statusSummary || "상태별 개체 집계 없음"}
- 최근 판매:
  ${salesSummary}`;
	} catch (error) {
		console.error("AI 농장 컨텍스트 구성 실패:", error);
		return "\n## 현재 농장 정보\n- 농장 정보 연결 상태: 불러오기 실패\n- 농장 정보를 불러오지 못했습니다. 일반적인 한우 농장 운영 기준으로 답변해 주세요.\n- 답변에는 실시간 농장 정보가 연결되지 않았다는 한계를 짧게 밝혀 주세요.";
	}
}

function normalizeGeminiChatStreamOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function createGeminiChatStream(options = {}) {
	const {
		apiKey,
		message,
		history,
		systemInstruction,
	} = normalizeGeminiChatStreamOptions(options);
	const genAI = new GoogleGenerativeAI(apiKey);
	const model = genAI.getGenerativeModel({
		model: "gemini-2.0-flash",
		systemInstruction,
	});

	const chat = model.startChat({ history });
	return createAiChatSseStream({ chat, message });
}

export async function POST(request) {
	let session;
	try {
		session = await requireAuthenticatedSession();
	} catch {
		return Response.json(
			{ success: false, message: "로그인이 필요합니다.", error: "UNAUTHENTICATED" },
			{ status: 401 },
		);
	}
	if (!session) {
		return Response.json(
			{ success: false, message: "로그인이 필요합니다.", error: "UNAUTHENTICATED" },
			{ status: 401 },
		);
	}

	const subscriptionStatus = await getSubscriptionStatus(session.user?.id).catch(
		() => ({ status: "INACTIVE" }),
	);
	if (subscriptionStatus.status === "INACTIVE") {
		return Response.json(
			{
				success: false,
				message: "프리미엄 구독이 필요한 기능입니다.",
				error: "SUBSCRIPTION_REQUIRED",
			},
			{ status: 403 },
		);
	}

	if (session.user?.id) {
		const rateResult = checkRateLimit(`ai-chat:${session.user.id}`, { maxRequests: 30, windowMs: 3600000 });
		if (!rateResult.allowed) {
			return Response.json(
				{
					success: false,
					message: "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
					error: "RATE_LIMITED",
				},
				{ status: 429, headers: { "Retry-After": String(rateResult.retryAfterSeconds ?? 3600) } },
			);
		}
	}

	return handleAiChatRequest(request, {
		authenticate: requireAuthenticatedSession,
		getApiKey: () => process.env.GEMINI_API_KEY,
		buildFarmContext,
		createChatStream: createGeminiChatStream,
		systemInstruction: SYSTEM_INSTRUCTION,
	});
}
