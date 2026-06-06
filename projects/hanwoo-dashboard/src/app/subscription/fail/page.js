"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

const PAYMENT_FAILURE_MESSAGE =
	"결제 상태를 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.";
const PAYMENT_FAILURE_LOADING_MESSAGE = "결제 실패 정보를 불러오는 중입니다.";
const PAYMENT_FAILURE_CODE_FALLBACK = "오류 코드 미전달";
const PAYMENT_RETRY_PATH = "/subscription";
const PAYMENT_RETRY_NAVIGATION_ERROR_MESSAGE =
	"결제 화면으로 자동 이동하지 못했습니다. 주소창에서 구독 화면으로 다시 이동해 주세요.";

function navigateToPaymentRetry() {
	if (typeof window === "undefined") {
		throw new Error("Browser navigation is unavailable");
	}
	window.location.assign(PAYMENT_RETRY_PATH);
}

function FailContent() {
	const searchParams = useSearchParams();
	const [retryStatus, setRetryStatus] = useState("");
	const errorCode = searchParams.get("code") || PAYMENT_FAILURE_CODE_FALLBACK;
	const handleRetry = () => {
		setRetryStatus("");
		try {
			navigateToPaymentRetry();
		} catch (error) {
			console.error("Payment retry navigation failed:", error);
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
				{PAYMENT_FAILURE_MESSAGE}
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
				aria-label="결제 화면으로 돌아가 다시 시도하기"
				title="결제 화면으로 돌아가 다시 시도하기"
				style={{
					marginTop: "20px",
					padding: "12px 22px",
					background: "var(--surface-gradient-primary)",
					color: "white",
					borderRadius: "18px",
					border: "1px solid var(--color-surface-stroke)",
					cursor: "pointer",
					boxShadow: "var(--shadow-button-primary)",
				}}
			>
				다시 시도하기
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
