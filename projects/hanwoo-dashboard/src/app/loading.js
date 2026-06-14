export default function Loading() {
	return (
		<div
			style={{
				minHeight: "100dvh",
				display: "flex",
				alignItems: "center",
				justifyContent: "center",
				flexDirection: "column",
				gap: "16px",
				background: "var(--color-bg)",
				color: "var(--color-text-secondary)",
				fontFamily: "var(--font-sans-custom)",
			}}
		>
			<div
				style={{
					width: "40px",
					height: "40px",
					borderRadius: "50%",
					border: "3px solid var(--color-surface-stroke)",
					borderTopColor: "var(--color-primary)",
					animation: "spin 0.8s linear infinite",
				}}
				role="status"
				aria-label="대시보드 로딩 중"
			/>
			<style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
			<p style={{ fontSize: "14px", fontWeight: 600 }}>잠시만 기다려 주세요...</p>
		</div>
	);
}
