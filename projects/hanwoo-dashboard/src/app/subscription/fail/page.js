"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

const PAYMENT_FAILURE_GENERIC_MESSAGE =
	"결제 상태를 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.";
const PAYMENT_FAILURE_LOADING_MESSAGE = "결제 실패 정보를 불러오는 중입니다.";
const PAYMENT_FAILURE_CODE_FALLBACK = "미전달";
const PAYMENT_FAILURE_MESSAGES = {
	PAY_PROCESS_CANCELED:
		"결제 진행이 취소되어 완료되지 않았습니다. 필요하면 다시 시도해 주세요.",
	PAY_PROCESS_ABORTED:
		"결제 요청 또는 결제 수단 인증 중 문제가 발생했습니다. 잠시 후 다시 시도하거나 다른 결제 수단을 선택해 주세요.",
	REJECT_CARD_COMPANY:
		"카드사에서 결제를 승인하지 않았습니다. 카드 정보를 확인하거나 다른 결제 수단을 선택해 주세요.",
};
const PAYMENT_RETRY_PATH = "/subscription";
const PAYMENT_RETRY_PENDING_MESSAGE = "결제 화면으로 이동하고 있습니다.";
const PAYMENT_RETRY_NAVIGATION_ERROR_MESSAGE =
	"결제 화면으로 자동 이동하지 못했습니다. 주소창에서 구독 화면으로 다시 이동해 주세요.";
const PAYMENT_FAILURE_ORDER_ID_PATTERN = /^[A-Za-z0-9_-]{6,128}$/;

function normalizePaymentFailureCode(value) {
	return typeof value === "string" && value.trim()
		? value.trim()
		: PAYMENT_FAILURE_CODE_FALLBACK;
}

function getPaymentFailureMessage(code) {
	return PAYMENT_FAILURE_MESSAGES[code] || PAYMENT_FAILURE_GENERIC_MESSAGE;
}

function normalizePaymentFailureOrderId(value) {
	if (typeof value !== "string") {
		return "";
	}
	const orderId = value.trim();
	return PAYMENT_FAILURE_ORDER_ID_PATTERN.test(orderId) ? orderId : "";
}

function navigateToPaymentRetry() {
	if (typeof window === "undefined") {
		throw new Error("Browser navigation is unavailable");
	}
	window.location.assign(PAYMENT_RETRY_PATH);
}

function FailContent() {
	const searchParams = useSearchParams();
	const [retryStatus, setRetryStatus] = useState("");
	const [isRetrying, setIsRetrying] = useState(false);
	const errorCode = normalizePaymentFailureCode(searchParams.get("code"));
	const orderId = normalizePaymentFailureOrderId(searchParams.get("orderId"));
	const failureMessage = getPaymentFailureMessage(errorCode);
	const retryButtonLabel = isRetrying
		? PAYMENT_RETRY_PENDING_MESSAGE
		: "결제 화면으로 돌아가 다시 시도하기";
	const handleRetry = () => {
		if (isRetrying) {
			return;
		}

		setRetryStatus(PAYMENT_RETRY_PENDING_MESSAGE);
		setIsRetrying(true);
		try {
			navigateToPaymentRetry();
		} catch (error) {
			console.error("Payment retry navigation failed:", error);
			setIsRetrying(false);
			setRetryStatus(PAYMENT_RETRY_NAVIGATION_ERROR_MESSAGE);
		}
	};

	return (
		<div
			style={{
				padding: "56px 24px",
				textAlign: "center",
				fontFamily: "var(--font-sans-custom)",
				color: "var(--color-text)",
			}}
		>
			<h1
				style={{
					fontSize: "28px",
					fontWeight: 700,
					color: "var(--color-danger)",
					fontFamily: "var(--font-display-custom)",
				}}
			>
				결제를 완료하지 못했습니다
			</h1>
			<p style={{ marginTop: "10px", color: "var(--color-text-secondary)" }}>
				{failureMessage}
			</p>
			<p
				style={{
					marginTop: "4px",
					fontSize: "12px",
					color: "var(--color-text-muted)",
					overflowWrap: "anywhere",
				}}
			>
				오류 코드: {errorCode}
			</p>
			{orderId ? (
				<p
					style={{
						marginTop: "8px",
						fontSize: "12px",
						color: "var(--color-text-muted)",
						overflowWrap: "anywhere",
					}}
				>
					문의용 주문번호: {orderId}
				</p>
			) : null}
			{retryStatus ? (
				<p
					role="status"
					aria-live="polite"
					aria-atomic="true"
					style={{
						marginTop: "12px",
						fontSize: "13px",
						fontWeight: 700,
						color: "var(--color-danger)",
					}}
				>
					{retryStatus}
				</p>
			) : null}

			<button
				type="button"
				onClick={handleRetry}
				disabled={isRetrying}
				aria-busy={isRetrying}
				aria-label={retryButtonLabel}
				title={retryButtonLabel}
				style={{
					marginTop: "20px",
					padding: "12px 22px",
					background: "var(--surface-gradient-primary)",
					color: "white",
					borderRadius: "18px",
					border: "1px solid var(--color-surface-stroke)",
					cursor: isRetrying ? "wait" : "pointer",
					boxShadow: "var(--shadow-button-primary)",
					opacity: isRetrying ? 0.72 : 1,
				}}
			>
				{isRetrying ? "이동 중입니다..." : "다시 시도하기"}
			</button>
		</div>
	);
}

export default function FailPage() {
	return (
		<Suspense
			fallback={
				<SubscriptionFallback message={PAYMENT_FAILURE_LOADING_MESSAGE} />
			}
		>
			<FailContent />
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
