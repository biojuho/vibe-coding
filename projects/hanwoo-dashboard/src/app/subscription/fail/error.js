"use client";

import { RotateCcw, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";

function normalizeErrorOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeReset(reset) {
	return typeof reset === "function" ? reset : () => {};
}

export default function SubscriptionFailError(options = {}) {
	const { error, reset } = normalizeErrorOptions(options);
	const safeReset = normalizeReset(reset);
	const retryLabel = "결제 실패 페이지 다시 불러오기";

	useEffect(() => {
		console.error("[hanwoo-dashboard] subscription/fail error:", error);
	}, [error]);

	return (
		<main className="login-shell" id="main-content">
			<section
				className="login-card status-card"
				aria-labelledby="subscription-fail-error-title"
			>
				<div className="login-brand">
					<div className="login-mark status-mark-danger" aria-hidden="true">
						<TriangleAlert size={26} strokeWidth={2.2} aria-hidden="true" />
					</div>
					<div>
						<p className="login-eyebrow">Joolife 한우 운영</p>
						<h1 id="subscription-fail-error-title" className="login-title">
							결제 실패 페이지를 불러오지 못했습니다
						</h1>
					</div>
				</div>

				<p className="login-copy">
					결제 실패 정보를 불러오는 중 오류가 발생했습니다. 결제는 처리되지 않은
					상태이니 구독 화면에서 다시 시도해 주세요.
				</p>

				<div className="status-actions">
					<button
						type="button"
						className="login-submit"
						onClick={() => safeReset()}
						aria-label={retryLabel}
						title={retryLabel}
					>
						<RotateCcw size={18} aria-hidden="true" />
						{retryLabel}
					</button>
					<Link
						href="/subscription"
						aria-label="구독 화면으로 돌아가기"
						title="구독 화면으로 돌아가기"
						className="status-link"
					>
						구독 화면으로 돌아가기
					</Link>
				</div>
			</section>
		</main>
	);
}
