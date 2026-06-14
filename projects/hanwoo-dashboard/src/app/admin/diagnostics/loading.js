export default function DiagnosticsLoading() {
	return (
		<div
			role="status"
			aria-live="polite"
			aria-label="진단 페이지 로딩 중"
			style={{
				padding: "64px 24px",
				textAlign: "center",
				fontFamily: "var(--font-sans-custom)",
				color: "var(--color-text-secondary)",
				fontWeight: 700,
			}}
		>
			진단 정보를 불러오는 중...
		</div>
	);
}
