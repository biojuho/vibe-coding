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
	normalizePaymentKey,
	normalizePaymentOrderId,
	PREMIUM_SUBSCRIPTION,
	parseCustomerKeyFromOrderId,
} from "@/lib/subscription";

const TOSS_CONFIRM_TIMEOUT_MS = 15000;
const TOSS_LOOKUP_TIMEOUT_MS = 10000;
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

function normalizePaymentConfirmBody(body) {
	return body && typeof body === "object" && !Array.isArray(body) ? body : {};
}

function normalizePaymentLogFailureOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

async function markPaymentLogFailed(options = {}) {
	const { orderId, paymentKey, amount } =
		normalizePaymentLogFailureOptions(options);
	// Never downgrade a DONE payment to FAILED: a duplicate/late confirm must not
	// erase a payment that already succeeded. Only non-DONE rows are touched.
	const { count } = await prisma.paymentLog.updateMany({
		where: { orderId, status: { not: "DONE" } },
		data: { paymentKey, amount, status: "FAILED" },
	});

	if (count === 0) {
		// Either the row is already DONE (leave it) or it doesn't exist yet
		// (the pre-Toss PENDING upsert failed); only create when truly absent.
		const existing = await prisma.paymentLog.findUnique({ where: { orderId } });
		if (!existing) {
			await prisma.paymentLog.create({
				data: { orderId, paymentKey, amount, status: "FAILED" },
			});
		}
	}
}

// Persist the successful payment + activate the subscription atomically. Shared
// by the normal confirm path and the already-processed reconciliation path so
// both produce identical, idempotent ledger + subscription state.
async function persistConfirmedPayment({
	orderId,
	paymentKey,
	customerKey,
	userId,
	confirmedAmount,
	approvedAt,
	receiptUrl,
}) {
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
			where: { customerKey },
			update: {
				userId,
				status: "ACTIVE",
				planName: PREMIUM_SUBSCRIPTION.planName,
				amount: confirmedAmount,
				nextPaymentDate: addDays(approvedAt, 30),
			},
			create: {
				userId,
				customerKey,
				status: "ACTIVE",
				planName: PREMIUM_SUBSCRIPTION.planName,
				amount: confirmedAmount,
				nextPaymentDate: addDays(approvedAt, 30),
			},
		});
	});
}

// Reconcile an ALREADY_PROCESSED_PAYMENT by asking Toss for the canonical
// payment record. Returns the confirmation result if Toss reports it DONE for
// this order/amount, or null when the lookup is inconclusive (caller stays in
// retryable "pending" — never FAILED).
async function lookupTossPayment({
	orderId,
	paymentKey,
	basicAuth,
	expectedAmount,
}) {
	let response;
	try {
		response = await fetchWithTimeout(
			`https://api.tosspayments.com/v1/payments/${encodeURIComponent(paymentKey)}`,
			{
				method: "GET",
				headers: { Authorization: `Basic ${basicAuth}` },
				cache: "no-store",
			},
			{
				timeoutMs: TOSS_LOOKUP_TIMEOUT_MS,
				errorMessage: `결제 조회가 ${TOSS_LOOKUP_TIMEOUT_MS}ms 안에 끝나지 않았습니다.`,
			},
		);
	} catch (error) {
		console.error("이미 승인된 결제 조회 실패:", error);
		return null;
	}

	const {
		data: payload,
		rawText,
		parseError,
	} = await readJsonResponseSafely(response);
	const result = classifyPaymentConfirmationResult({
		status: response.status,
		payload,
		rawText,
		parseError,
		expectedAmount,
	});

	if (result.kind !== "confirmed") {
		return null;
	}

	// classify() validates amount but not identity/status; confirm both before
	// we trust the lookup enough to activate a subscription.
	const isMatchingPayment =
		payload &&
		typeof payload === "object" &&
		payload.orderId === orderId &&
		payload.status === "DONE";

	return isMatchingPayment ? result : null;
}

export async function POST(req) {
	try {
		const session = await requireAuthenticatedSession();
		const body = normalizePaymentConfirmBody(await req.json());
		const paymentKey = normalizePaymentKey(body?.paymentKey);
		const orderId = normalizePaymentOrderId(body?.orderId);
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

		// Idempotency guard: if this order was already confirmed (a retry after a
		// lost success response), return success instead of re-confirming. The
		// success transaction is atomic, so a DONE log implies an ACTIVE
		// subscription already exists.
		const existingLog = await prisma.paymentLog.findUnique({
			where: { orderId },
		});
		if (existingLog?.status === "DONE") {
			return NextResponse.json({ success: true });
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

		// Toss says the payment was already approved (duplicate confirm after a
		// lost response). The money was charged, so reconcile against Toss and
		// activate the subscription rather than marking the log FAILED. If the
		// lookup is inconclusive, stay retryable (pending) — never FAILED.
		if (confirmationResult.kind === "already_processed") {
			const reconciled = await lookupTossPayment({
				orderId,
				paymentKey,
				basicAuth,
				expectedAmount: amount,
			});

			if (!reconciled) {
				console.error("이미 승인된 결제를 조회로 확정하지 못했습니다.", {
					orderId,
				});
				return buildPendingResponse();
			}

			await persistConfirmedPayment({
				orderId,
				paymentKey,
				customerKey: expectedCustomerKey,
				userId: session.user.id,
				confirmedAmount: reconciled.confirmedAmount,
				approvedAt: reconciled.approvedAt,
				receiptUrl: reconciled.receiptUrl,
			});

			return NextResponse.json({ success: true });
		}

		if (confirmationResult.kind === "failed") {
			await markPaymentLogFailed({ orderId, paymentKey, amount });
			return NextResponse.json(
				{ success: false, message: confirmationResult.message },
				{ status: confirmationResult.httpStatus },
			);
		}

		const { approvedAt, confirmedAmount, receiptUrl } = confirmationResult;

		await persistConfirmedPayment({
			orderId,
			paymentKey,
			customerKey: expectedCustomerKey,
			userId: session.user.id,
			confirmedAmount,
			approvedAt,
			receiptUrl,
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
