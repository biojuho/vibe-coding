"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { fetchWithTimeout } from "@/lib/fetchWithTimeout";
import {
	buildGatewayErrorMessage,
	PAYMENT_CONFIRMATION_PENDING_MESSAGE,
	readJsonResponseSafely,
} from "@/lib/payment-confirmation.mjs";

const CONFIRM_RETRY_DELAY_MS = 3000;
const CONFIRM_RETRY_LIMIT = 3;
const AMOUNT_INPUT_PATTERN = /^\d+$/;
const PAYMENT_CONFIRMATION_ERROR_MESSAGE =
	"결제 확인 중 오류가 발생했습니다. 잠시 후 다시 확인해 주세요.";

const PAYMENT_AMOUNT_ERROR_MESSAGE = "결제 금액 정보를 확인해 주세요.";

function parsePaymentAmount(value) {
	if (!value || !AMOUNT_INPUT_PATTERN.test(value)) {
		return null;
	}

	const amount = Number(value);
	return Number.isSafeInteger(amount) ? amount : null;
}

function SuccessContent() {
	const searchParams = useSearchParams();
	const router = useRouter();
	const [status, setStatus] = useState("결제를 확인하고 있습니다.");

	useEffect(() => {
		const paymentKey = searchParams.get("paymentKey");
		const orderId = searchParams.get("orderId");
		const amount = searchParams.get("amount");

		if (!paymentKey || !orderId || !amount) {
			return;
		}

		const paymentAmount = parsePaymentAmount(amount);
		if (paymentAmount === null) {
			const invalidAmountTimer = setTimeout(
				() => setStatus(PAYMENT_AMOUNT_ERROR_MESSAGE),
				0,
			);
			return () => clearTimeout(invalidAmountTimer);
		}

		let cancelled = false;
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
					setStatus("success");
					retryTimer = setTimeout(() => router.push("/"), 3000);
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
					retryTimer = setTimeout(() => {
						void confirmPayment(attempt + 1);
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
				if (!cancelled) {
					console.error("Payment confirmation failed:", error);
					setStatus(PAYMENT_CONFIRMATION_ERROR_MESSAGE);
				}
			}
		};

		void confirmPayment();

		return () => {
			cancelled = true;
			if (retryTimer) {
				clearTimeout(retryTimer);
			}
		};
	}, [searchParams, router]);

	return (
		<div
			style={{
				padding: "56px 24px",
				textAlign: "center",
				fontFamily: "var(--font-sans-custom)",
				color: "var(--color-text)",
			}}
		>
			{status === "success" ? (
				<div>
					<h1
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
						style={{
							fontSize: "28px",
							fontWeight: 700,
							fontFamily: "var(--font-display-custom)",
						}}
					>
						{status}
					</h1>
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

function SubscriptionFallback({ message }) {
	return (
		<div
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
