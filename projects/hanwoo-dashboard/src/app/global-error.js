"use client";

import { useEffect } from "react";

// global-error replaces the root layout, so it must render its own <html>/<body>
// and cannot rely on globals.css being applied. Styles are inlined intentionally.
function normalizeGlobalErrorOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeGlobalErrorReset(reset) {
	return typeof reset === "function" ? reset : () => {};
}

export default function GlobalError(options = {}) {
	const { error, reset } = normalizeGlobalErrorOptions(options);
	const safeReset = normalizeGlobalErrorReset(reset);
	const resetButtonLabel = "앱 다시 불러오기";

	useEffect(() => {
		console.error("[hanwoo-dashboard] global error:", error);
	}, [error]);

	return (
		<html lang="ko">
			<body
				style={{
					margin: 0,
					minHeight: "100vh",
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
					padding: "24px",
					background: "linear-gradient(180deg, #f4f1ec 0%, #e9e4db 100%)",
					color: "#2c2a26",
					fontFamily:
						"'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
				}}
			>
				<main
					style={{
						width: "min(100%, 420px)",
						padding: "32px 28px",
						borderRadius: "28px",
						background: "#fffdf9",
						border: "1px solid rgba(0, 0, 0, 0.06)",
						boxShadow: "0 24px 60px rgba(40, 36, 30, 0.16)",
						textAlign: "center",
					}}
				>
					<p
						style={{
							margin: "0 0 6px",
							fontSize: "11px",
							fontWeight: 850,
							letterSpacing: "0.02em",
							textTransform: "uppercase",
							color: "#9b9488",
						}}
					>
						Joolife 한우 운영
					</p>
					<h1 style={{ margin: "0 0 12px", fontSize: "24px", fontWeight: 900 }}>
						앱을 불러오지 못했어요
					</h1>
					<p
						style={{
							margin: "0 0 24px",
							fontSize: "14px",
							lineHeight: 1.6,
							fontWeight: 600,
							color: "#6f685c",
						}}
					>
						예상치 못한 오류로 화면을 표시할 수 없습니다. 다시 시도하거나, 잠시
						후 앱을 새로 열어 주세요.
					</p>
					<button
						type="button"
						onClick={() => safeReset()}
						aria-label={resetButtonLabel}
						title={resetButtonLabel}
						style={{
							minHeight: "52px",
							width: "100%",
							border: 0,
							borderRadius: "18px",
							background: "linear-gradient(145deg, #b8703a, #9a5a2c)",
							color: "#fffdf9",
							fontSize: "16px",
							fontWeight: 900,
							cursor: "pointer",
						}}
					>
						{resetButtonLabel}
					</button>
				</main>
			</body>
		</html>
	);
}
