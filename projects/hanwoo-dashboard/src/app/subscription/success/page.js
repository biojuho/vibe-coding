"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { fetchWithTimeout } from "@/lib/fetchWithTimeout";
import {
	buildGatewayErrorMessage,
	PAYMENT_CONFIRMATION_PENDING_MESSAGE,
	readJsonResponseSafely,
} from "@/lib/payment-confirmation.mjs";
import { normalizePaymentKey, normalizePaymentOrderId } from "@/lib/subscription";

const CONFIRM_RETRY_DELAY_MS = 3000;
const CONFIRM_RETRY_LIMIT = 3;
const AMOUNT_INPUT_PATTERN = /^\d+$/;
const PAYMENT_CONFIRMATION_INITIAL_MESSAGE = "결제를 확인하고 있습니다.";
const PAYMENT_CONFIRMATION_ERROR_MESSAGE =
	"결제 확인 중 오류가 발생했습니다. 잠시 후 다시 확인해 주세요.";
const PAYMENT_REDIRECT_ERROR_MESSAGE =
	"대시보드로 자동 이동하지 못했습니다. 대시보드로 돌아가 다시 확인해 주세요.";
const PAYMENT_MISSING_REDIRECT_MESSAGE =
	"결제 확인에 필요한 정보가 부족합니다. 결제 화면으로 돌아가 다시 시도해 주세요.";
const PAYMENT_INVALID_REDIRECT_MESSAGE =
	"결제 식별자 정보를 확인해 주세요. 결제 화면으로 돌아가 다시 시도해 주세요.";
const PAYMENT_RETRY_PATH = "/subscription";
const PAYMENT_SUCCESS_STATUS = "success";

const PAYMENT_AMOUNT_ERROR_MESSAGE = "결제 금액 정보를 확인해 주세요.";

function parsePaymentAmount(value) {
	if (!value || !AMOUNT_INPUT_PATTERN.test(value)) {
		return null;
	}

	const amount = Number(value);
	return Number.isSafeInteger(amount) ? amount : null;
}

function schedulePaymentStatusTimer(callback, delay) {
	try {
		return window.setTimeout(callback, delay);
	} catch (error) {
		console.error("Payment success timer scheduling failed:", error);
		callback();
		return null;
	}
}

function clearPaymentStatusTimer(timeoutId) {
	if (timeoutId === null) {
		return;
	}

	try {
		window.clearTimeout(timeoutId);
	} catch {}
}

function SuccessContent() {
	const searchParams = useSearchParams();
	const router = useRouter();
	const [status, setStatus] = useState(PAYMENT_CONFIRMATION_INITIAL_MESSAGE);
	// Bumping this re-runs the confirmation effect from attempt 0 — used by the
	// manual "re-check" button so a network blip after payment isn't a dead end.
	const [retryNonce, setRetryNonce] = useState(0);
	const paymentKeyParam = searchParams.get("paymentKey");
	const orderIdParam = searchParams.get("orderId");
	const amountParam = searchParams.get("amount");
	const normalizedPaymentKey = normalizePaymentKey(paymentKeyParam);
	const normalizedOrderId = normalizePaymentOrderId(orderIdParam);
	const hasPaymentRedirectParameters = Boolean(
		paymentKeyParam && orderIdParam && amountParam,
	);
	const hasInvalidPaymentRedirectIdentifiers = Boolean(
		hasPaymentRedirectParameters && (!normalizedPaymentKey || !normalizedOrderId),
	);
	const visibleStatus = !hasPaymentRedirectParameters
		? PAYMENT_MISSING_REDIRECT_MESSAGE
		: hasInvalidPaymentRedirectIdentifiers
			? PAYMENT_INVALID_REDIRECT_MESSAGE
			: status;
	const shouldShowPaymentRetryLink =
		visibleStatus === PAYMENT_MISSING_REDIRECT_MESSAGE ||
		visibleStatus === PAYMENT_INVALID_REDIRECT_MESSAGE;
	// Show a manual re-check when confirmation is stuck in a recoverable state
	// (network/timeout error, gateway pending, redirect failure) but not while it
	// is still auto-confirming, already succeeded, or blocked on bad URL params.
	const isActivelyConfirming =
		visibleStatus === PAYMENT_CONFIRMATION_INITIAL_MESSAGE ||
		visibleStatus.startsWith("결제 확인을 다시 시도합니다");
	const shouldShowManualRetry =
		!shouldShowPaymentRetryLink &&
		!isActivelyConfirming &&
		visibleStatus !== PAYMENT_SUCCESS_STATUS;

	useEffect(() => {
		const paymentKey = normalizePaymentKey(searchParams.get("paymentKey"));
		const orderId = normalizePaymentOrderId(searchParams.get("orderId"));
		const amount = searchParams.get("amount");
		let cancelled = false;

		if (!paymentKey || !orderId || !amount) {
			return;
		}

		const paymentAmount = parsePaymentAmount(amount);
		if (paymentAmount === null) {
			const invalidAmountTimer = schedulePaymentStatusTimer(
				() => {
					if (!cancelled) {
						setStatus(PAYMENT_AMOUNT_ERROR_MESSAGE);
					}
				},
				0,
			);
			return () => {
				cancelled = true;
				clearPaymentStatusTimer(invalidAmountTimer);
			};
		}

		let retryTimer = null;

		const confirmPayment = async (attempt = 0) => {
			try {
				const response = await fetchWithTimeout(
					"/api/payments/confirm",
					{
						method: "POST",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify({
							paymentKey,
							orderId,
							amount: paymentAmount,
						}),
					},
					{
						timeoutMs: 15000,
						errorMessage: "결제 확인 시간이 길어지고 있습니다.",
					},
				);

				const { data, rawText, parseError } =
					await readJsonResponseSafely(response);
				if (cancelled) {
					return;
				}

				if (data?.success) {
					setStatus(PAYMENT_SUCCESS_STATUS);
					retryTimer = schedulePaymentStatusTimer(() => {
						if (cancelled) {
							return;
						}

						try {
							router.push("/");
						} catch (error) {
							console.error("Payment success redirect failed:", error);
							if (!cancelled) {
								setStatus(PAYMENT_REDIRECT_ERROR_MESSAGE);
							}
						}
					}, 3000);
					return;
				}

				const shouldTreatAsPending =
					response.status === 202 ||
					(response.ok && !data?.success && (parseError || !data));
				const pendingMessage = buildGatewayErrorMessage({
					payload: data,
					rawText,
					fallbackMessage: PAYMENT_CONFIRMATION_PENDING_MESSAGE,
				});

				if (shouldTreatAsPending && attempt < CONFIRM_RETRY_LIMIT) {
					setStatus(
						`결제 확인을 다시 시도합니다. ${CONFIRM_RETRY_DELAY_MS / 1000}초 후 재확인합니다.`,
					);
					retryTimer = schedulePaymentStatusTimer(() => {
						if (!cancelled) {
							void confirmPayment(attempt + 1);
						}
					}, CONFIRM_RETRY_DELAY_MS);
					return;
				}

				if (shouldTreatAsPending) {
					setStatus(pendingMessage);
					return;
				}

				setStatus(
					`결제 확인 실패: ${buildGatewayErrorMessage({
						payload: data,
						rawText,
					})}`,
				);
			} catch (error) {
				if (cancelled) {
					return;
				}

				console.error("Payment confirmation failed:", error);
				// Network/timeout errors are transient: keep retrying within the
				// same bounded loop instead of dead-ending the just-charged user.
				if (attempt < CONFIRM_RETRY_LIMIT) {
					setStatus(
						`결제 확인을 다시 시도합니다. ${CONFIRM_RETRY_DELAY_MS / 1000}초 후 재확인합니다.`,
					);
					retryTimer = schedulePaymentStatusTimer(() => {
						if (!cancelled) {
							void confirmPayment(attempt + 1);
						}
					}, CONFIRM_RETRY_DELAY_MS);
					return;
				}

				setStatus(PAYMENT_CONFIRMATION_ERROR_MESSAGE);
			}
		};

		void confirmPayment();

		return () => {
			cancelled = true;
			clearPaymentStatusTimer(retryTimer);
		};
	}, [searchParams, router, retryNonce]);

	return (
		<div
			style={{
				padding: "56px 24px",
				textAlign: "center",
				fontFamily: "var(--font-sans-custom)",
				color: "var(--color-text)",
			}}
		>
			{visibleStatus === PAYMENT_SUCCESS_STATUS ? (
				<div>
					<h1
						aria-live="polite"
						aria-atomic="true"
						style={{
							fontSize: "28px",
							fontWeight: 700,
							color: "var(--color-success)",
							fontFamily: "var(--font-display-custom)",
						}}
					>
						결제가 완료되었습니다
					</h1>
					<p>Joolife 구독이 활성화되었습니다.</p>
					<p>3초 후 대시보드로 이동합니다.</p>
				</div>
			) : (
				<div>
					<h1
						aria-live="polite"
						aria-atomic="true"
						style={{
							fontSize: "28px",
							fontWeight: 700,
							fontFamily: "var(--font-display-custom)",
						}}
					>
						{visibleStatus}
					</h1>
					{shouldShowPaymentRetryLink ? (
						<a
							href={PAYMENT_RETRY_PATH}
							aria-label="결제 화면으로 돌아가기"
							title="결제 화면으로 돌아가기"
							style={{
								display: "inline-flex",
								alignItems: "center",
								justifyContent: "center",
								marginTop: "22px",
								padding: "14px 18px",
								borderRadius: "16px",
								background: "var(--surface-gradient-primary)",
								color: "white",
								fontSize: "15px",
								fontWeight: 700,
								textDecoration: "none",
								boxShadow: "var(--shadow-button-primary)",
							}}
						>
							결제 화면으로 돌아가기
						</a>
					) : null}
					{shouldShowManualRetry ? (
						<button
							type="button"
							onClick={() => {
								setStatus(PAYMENT_CONFIRMATION_INITIAL_MESSAGE);
								setRetryNonce((nonce) => nonce + 1);
							}}
							aria-label="결제 다시 확인하기"
							title="결제 다시 확인하기"
							style={{
								display: "inline-flex",
								alignItems: "center",
								justifyContent: "center",
								marginTop: "22px",
								padding: "14px 18px",
								borderRadius: "16px",
								background: "var(--surface-gradient-primary)",
								color: "white",
								fontSize: "15px",
								fontWeight: 700,
								border: "none",
								cursor: "pointer",
								boxShadow: "var(--shadow-button-primary)",
							}}
						>
							결제 다시 확인하기
						</button>
					) : null}
				</div>
			)}
		</div>
	);
}

export default function SuccessPage() {
	return (
		<Suspense
			fallback={
				<SubscriptionFallback message="결제 정보를 불러오는 중입니다." />
			}
		>
			<SuccessContent />
		</Suspense>
	);
}

function normalizeSubscriptionFallbackOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function SubscriptionFallback(options = {}) {
	const { message } = normalizeSubscriptionFallbackOptions(options);

	return (
		<div
			role="status"
			aria-live="polite"
			aria-atomic="true"
			aria-busy="true"
			style={{
				padding: "56px 24px",
				textAlign: "center",
				fontFamily: "var(--font-sans-custom)",
				color: "var(--color-text-secondary)",
				fontWeight: 700,
			}}
		>
			{message}
		</div>
	);
}
