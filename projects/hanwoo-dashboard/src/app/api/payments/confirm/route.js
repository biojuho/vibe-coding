import { NextResponse } from "next/server";
import {
	AUTHENTICATION_REQUIRED_MESSAGE,
	isAuthenticationError,
	requireAuthenticatedSession,
} from "@/lib/auth-guard";
import prisma from "@/lib/db";
import { fetchWithTimeout, isTimeoutError } from "@/lib/fetchWithTimeout";
import {
	classifyPaymentConfirmationResult,
	PAYMENT_CONFIRMATION_PENDING_MESSAGE,
	readJsonResponseSafely,
} from "@/lib/payment-confirmation.mjs";
import {
	addDays,
	buildCustomerKey,
	PREMIUM_SUBSCRIPTION,
	parseCustomerKeyFromOrderId,
} from "@/lib/subscription";

const TOSS_CONFIRM_TIMEOUT_MS = 15000;
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

function buildPendingResponse(message = PAYMENT_CONFIRMATION_PENDING_MESSAGE) {
	return NextResponse.json(
		{
			success: false,
			pending: true,
			message,
		},
		{ status: 202 },
	);
}

async function markPaymentLogFailed({ orderId, paymentKey, amount }) {
	await prisma.paymentLog.upsert({
		where: { orderId },
		update: {
			paymentKey,
			amount,
			status: "FAILED",
		},
		create: {
			orderId,
			paymentKey,
			amount,
			status: "FAILED",
		},
	});
}

export async function POST(req) {
	try {
		const session = await requireAuthenticatedSession();
		const body = await req.json();
		const { paymentKey, orderId } = body;
		const amount = parsePaymentAmount(body?.amount);

		if (!paymentKey || !orderId || !Number.isSafeInteger(amount)) {
			return NextResponse.json(
				{ success: false, message: "결제 승인에 필요한 정보가 부족합니다." },
				{ status: 400 },
			);
		}

		const expectedCustomerKey = buildCustomerKey(session.user.id);
		const orderCustomerKey = parseCustomerKeyFromOrderId(orderId);

		if (!orderCustomerKey || orderCustomerKey !== expectedCustomerKey) {
			return NextResponse.json(
				{
					success: false,
					message: "이 결제 요청은 현재 로그인 사용자와 일치하지 않습니다.",
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

		const secretKey = process.env.TOSS_PAYMENTS_SECRET_KEY;
		if (!secretKey) {
			throw new Error(
				"결제 설정이 완료되지 않았습니다. 관리자에게 문의해 주세요.",
			);
		}

		await prisma.paymentLog.upsert({
			where: { orderId },
			update: {
				paymentKey,
				amount,
				status: "PENDING_CONFIRMATION",
			},
			create: {
				orderId,
				paymentKey,
				amount,
				status: "PENDING_CONFIRMATION",
			},
		});

		const basicAuth = Buffer.from(`${secretKey}:`).toString("base64");
		let response;

		try {
			response = await fetchWithTimeout(
				"https://api.tosspayments.com/v1/payments/confirm",
				{
					method: "POST",
					headers: {
						Authorization: `Basic ${basicAuth}`,
						"Content-Type": "application/json",
					},
					body: JSON.stringify({ paymentKey, orderId, amount }),
					cache: "no-store",
				},
				{
					timeoutMs: TOSS_CONFIRM_TIMEOUT_MS,
					errorMessage: `결제 승인 확인이 ${TOSS_CONFIRM_TIMEOUT_MS}ms 안에 끝나지 않았습니다.`,
				},
			);
		} catch (error) {
			if (isTimeoutError(error)) {
				return buildPendingResponse();
			}

			console.error("결제 승인 요청 응답 수신 전 실패:", error);
			return buildPendingResponse();
		}

		const {
			data: paymentData,
			rawText,
			parseError,
		} = await readJsonResponseSafely(response);
		const confirmationResult = classifyPaymentConfirmationResult({
			status: response.status,
			payload: paymentData,
			rawText,
			parseError,
			expectedAmount: amount,
		});

		if (confirmationResult.kind === "pending") {
			if (response.status >= 500 || parseError) {
				console.error("재시도 가능한 결제 승인 응답으로 확인을 보류했습니다.", {
					orderId,
					status: response.status,
					parseError: parseError?.message,
				});
			}

			return buildPendingResponse(confirmationResult.message);
		}

		if (confirmationResult.kind === "failed") {
			await markPaymentLogFailed({ orderId, paymentKey, amount });
			return NextResponse.json(
				{ success: false, message: confirmationResult.message },
				{ status: confirmationResult.httpStatus },
			);
		}

		const { approvedAt, confirmedAmount, receiptUrl } = confirmationResult;

		await prisma.$transaction(async (tx) => {
			await tx.paymentLog.upsert({
				where: { orderId },
				update: {
					paymentKey,
					amount: confirmedAmount,
					status: "DONE",
					approvedAt,
					receiptUrl,
				},
				create: {
					orderId,
					paymentKey,
					amount: confirmedAmount,
					status: "DONE",
					approvedAt,
					receiptUrl,
				},
			});

			await tx.subscription.upsert({
				where: { customerKey: expectedCustomerKey },
				update: {
					userId: session.user.id,
					status: "ACTIVE",
					planName: PREMIUM_SUBSCRIPTION.planName,
					amount: confirmedAmount,
					nextPaymentDate: addDays(approvedAt, 30),
				},
				create: {
					userId: session.user.id,
					customerKey: expectedCustomerKey,
					status: "ACTIVE",
					planName: PREMIUM_SUBSCRIPTION.planName,
					amount: confirmedAmount,
					nextPaymentDate: addDays(approvedAt, 30),
				},
			});
		});

		return NextResponse.json({ success: true });
	} catch (error) {
		if (isAuthenticationError(error)) {
			return NextResponse.json(
				{ success: false, message: AUTHENTICATION_REQUIRED_MESSAGE },
				{ status: 401 },
			);
		}

		console.error("결제 승인 확인 처리 실패:", error);
		return NextResponse.json(
			{
				success: false,
				message: "결제 확인을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.",
			},
			{ status: 500 },
		);
	}
}
