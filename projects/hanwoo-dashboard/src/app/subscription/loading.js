export default function Loading() {
	return (
		<div
			style={{
				maxWidth: "640px",
				margin: "0 auto",
				padding: "48px 20px",
				fontFamily: "var(--font-sans-custom)",
			}}
		>
			<div
				style={{
					height: "36px",
					width: "240px",
					borderRadius: "8px",
					background: "var(--color-surface-stroke)",
					marginBottom: "12px",
					animation: "pulse 1.5s ease-in-out infinite",
				}}
			/>
			<div
				style={{
					height: "20px",
					width: "320px",
					borderRadius: "6px",
					background: "var(--color-surface-stroke)",
					marginBottom: "28px",
					opacity: 0.6,
					animation: "pulse 1.5s ease-in-out infinite",
				}}
			/>
			<div
				style={{
					display: "grid",
					gridTemplateColumns: "1fr 1fr",
					gap: "10px",
					marginBottom: "28px",
				}}
			>
				{Array.from({ length: 6 }).map((_, i) => (
					<div
						key={i}
						style={{
							height: "72px",
							borderRadius: "16px",
							background: "var(--color-surface-stroke)",
							animation: "pulse 1.5s ease-in-out infinite",
							animationDelay: `${i * 0.1}s`,
						}}
					/>
				))}
			</div>
			<style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }`}</style>
		</div>
	);
}
