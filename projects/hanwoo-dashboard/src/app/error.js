"use client";

/* eslint-disable @next/next/no-html-link-for-pages -- Dashboard recovery must use document navigation so auth proxy redirect fragments are preserved. */
import { RotateCcw, TriangleAlert } from "lucide-react";
import { useEffect } from "react";

function normalizeRouteErrorOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeRouteErrorReset(reset) {
	return typeof reset === "function" ? reset : () => {};
}

export default function RouteError(options = {}) {
	const { error, reset } = normalizeRouteErrorOptions(options);
	const safeReset = normalizeRouteErrorReset(reset);
	const resetButtonLabel = "화면 다시 불러오기";

	useEffect(() => {
		console.error("[hanwoo-dashboard] route error:", error);
	}, [error]);

	return (
		<main className="login-shell">
			<section
				className="login-card status-card"
				aria-labelledby="route-error-title"
			>
				<div className="login-brand">
					<div className="login-mark status-mark-danger" aria-hidden="true">
						<TriangleAlert size={26} strokeWidth={2.2} aria-hidden="true" />
					</div>
					<div>
						<p className="login-eyebrow">Joolife 한우 운영</p>
						<h1 id="route-error-title" className="login-title">
							잠시 문제가 발생했습니다
						</h1>
					</div>
				</div>

				<p className="login-copy">
					화면을 불러오는 중 오류가 발생했습니다. 입력하던 내용은 오프라인
					대기열에 안전하게 남아 있으니, 다시 시도하거나 대시보드로 돌아가 주세요.
				</p>

				<div className="status-actions">
					<button
						type="button"
						className="login-submit"
						onClick={() => safeReset()}
						aria-label={resetButtonLabel}
						title={resetButtonLabel}
					>
						<RotateCcw size={18} aria-hidden="true" />
						{resetButtonLabel}
					</button>
					{/* Use document navigation so the auth proxy owns protected redirects. */}
					<a
						href="/"
						aria-label="대시보드로 돌아가기"
						title="대시보드로 돌아가기"
						className="status-link"
					>
						대시보드로 돌아가기
					</a>
				</div>
			</section>
		</main>
	);
}
