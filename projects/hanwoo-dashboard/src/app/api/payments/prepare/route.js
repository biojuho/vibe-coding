import { NextResponse } from "next/server";

import {
	AUTHENTICATION_REQUIRED_MESSAGE,
	isAuthenticationError,
	requireAuthenticatedSession,
} from "@/lib/auth-guard";
import { checkRateLimit } from "@/lib/rate-limit.mjs";
import {
	buildCustomerKey,
	buildOrderId,
	PREMIUM_SUBSCRIPTION,
} from "@/lib/subscription";

const AMOUNT_INPUT_PATTERN = /^\d+$/;

function parsePaymentAmount(value) {
	if (typeof value === "number") {
		return Number.isSafeInteger(value) ? value : Number.NaN;
	}

	if (typeof value === "string" && AMOUNT_INPUT_PATTERN.test(value)) {
		const amount = Number(value);
		return Number.isSafeInteger(amount) ? amount : Number.NaN;
	}

	return Number.NaN;
}

function normalizePaymentPrepareBody(body) {
	return body && typeof body === "object" && !Array.isArray(body) ? body : {};
}

// 10 payment prepare attempts per hour per user is generous for legitimate use
const PAYMENT_PREPARE_RATE_LIMIT = { maxRequests: 10, windowMs: 3600000 };

export async function POST(req) {
	try {
		const session = await requireAuthenticatedSession();
		const rateLimitKey = `payment-prepare:${session.user.id}`;
		const rateCheck = checkRateLimit(rateLimitKey, PAYMENT_PREPARE_RATE_LIMIT);
		if (!rateCheck.allowed) {
			return NextResponse.json(
				{ success: false, message: "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요." },
				{
					status: 429,
					headers: { "Retry-After": String(rateCheck.retryAfterSeconds) },
				},
			);
		}

		const body = normalizePaymentPrepareBody(await req.json());
		const amount = parsePaymentAmount(
			body?.amount ?? PREMIUM_SUBSCRIPTION.amount,
		);
		const customerKey = buildCustomerKey(session.user.id);

		if (customerKey !== body?.customerKey) {
			return NextResponse.json(
				{
					success: false,
					message: "결제 고객 정보가 현재 로그인 사용자와 일치하지 않습니다.",
				},
				{ status: 403 },
			);
		}

		if (amount !== PREMIUM_SUBSCRIPTION.amount) {
			return NextResponse.json(
				{
					success: false,
					message: "결제 금액이 구독 상품 금액과 일치하지 않습니다.",
				},
				{ status: 400 },
			);
		}

		return NextResponse.json(
			{
				success: true,
				orderId: buildOrderId(customerKey),
				orderName: body?.orderName || PREMIUM_SUBSCRIPTION.displayName,
				customerName: body?.customerName || session.user.name || "Joolife 사용자",
				customerEmail: body?.customerEmail || null,
				amount,
			},
			{ headers: { "Cache-Control": "no-store" } },
		);
	} catch (error) {
		if (isAuthenticationError(error)) {
			return NextResponse.json(
				{ success: false, message: AUTHENTICATION_REQUIRED_MESSAGE },
				{ status: 401 },
			);
		}

		console.error("결제 준비 처리 실패:", error);
		return NextResponse.json(
			{
				success: false,
				message: "결제를 준비하지 못했습니다. 잠시 후 다시 시도해 주세요.",
			},
			{ status: 500 },
		);
	}
}
