import Link from "next/link";

const FEATURES = [
	{
		icon: "🐄",
		title: "개체 관리",
		desc: "소 정보, 이력번호, 체중 변화를 한 곳에서 관리하세요.",
	},
	{
		icon: "🤖",
		title: "AI 인사이트",
		desc: "매일 농장 상태를 분석해 최적의 사육 조언을 제공합니다.",
	},
	{
		icon: "📈",
		title: "실시간 시세",
		desc: "KAPE 한우 경락가격을 자동으로 연동해 수익성을 비교합니다.",
	},
	{
		icon: "📊",
		title: "수익성 분석",
		desc: "개체별 사료비·출하 예상 수익을 자동으로 계산합니다.",
	},
	{
		icon: "🔔",
		title: "스마트 알림",
		desc: "발정·분만·재고 부족을 놓치지 않도록 즉시 알려드립니다.",
	},
	{
		icon: "📋",
		title: "엑셀 내보내기",
		desc: "개체 대장을 원클릭으로 다운로드해 보조금 신청에 활용하세요.",
	},
];

export default function LandingPage() {
	return (
		<div
			style={{
				minHeight: "100dvh",
				background: "var(--color-background)",
				color: "var(--color-text)",
				fontFamily: "var(--font-sans-custom)",
			}}
		>
			{/* Header */}
			<header
				role="banner"
				aria-label="Joolife 한우 사이트 헤더"
				style={{
					borderBottom: "1px solid var(--color-surface-stroke)",
					padding: "0 24px",
					height: "60px",
					display: "flex",
					alignItems: "center",
					justifyContent: "space-between",
					background: "var(--color-surface)",
				}}
			>
				<span
					style={{
						fontFamily: "var(--font-display-custom)",
						fontWeight: 800,
						fontSize: "20px",
						letterSpacing: "0.04em",
						color: "var(--color-primary-custom)",
					}}
				>
					Joolife 한우
				</span>
				<div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
					<Link
						href="/login"
						style={{
							color: "var(--color-text-secondary)",
							fontSize: "14px",
							fontWeight: 600,
							textDecoration: "none",
						}}
					>
						로그인
					</Link>
					<Link
						href="/register"
						style={{
							background: "var(--color-primary-custom)",
							color: "#fff",
							border: "none",
							borderRadius: "10px",
							padding: "8px 20px",
							fontSize: "14px",
							fontWeight: 700,
							textDecoration: "none",
						}}
					>
						무료 시작
					</Link>
				</div>
			</header>

			<main id="main-content">
			{/* Hero */}
			<section
				style={{
					textAlign: "center",
					padding: "80px 24px 60px",
					maxWidth: "680px",
					margin: "0 auto",
				}}
			>
				<div
					style={{ fontSize: "48px", lineHeight: 1, marginBottom: "20px" }}
					aria-hidden="true"
				>
					🐄
				</div>
				<h1
					style={{
						fontFamily: "var(--font-display-custom)",
						fontSize: "clamp(28px, 5vw, 42px)",
						fontWeight: 800,
						lineHeight: 1.2,
						letterSpacing: "0.04em",
						marginBottom: "16px",
					}}
				>
					한우 농장 관리,
					<br />
					스마트하게 시작하세요
				</h1>
				<p
					style={{
						fontSize: "17px",
						color: "var(--color-text-secondary)",
						lineHeight: 1.65,
						marginBottom: "36px",
					}}
				>
					개체 관리부터 수익성 분석, AI 인사이트까지.
					<br />
					Joolife 한우가 농장 운영의 모든 것을 도와드립니다.
				</p>
				<Link
					href="/register"
					style={{
						display: "inline-block",
						background: "var(--color-primary-custom)",
						color: "#fff",
						borderRadius: "14px",
						padding: "14px 36px",
						fontSize: "16px",
						fontWeight: 800,
						textDecoration: "none",
						boxShadow: "0 4px 16px color-mix(in srgb, var(--color-primary-custom) 30%, transparent)",
					}}
				>
					무료로 시작하기
				</Link>
				<p
					style={{
						marginTop: "12px",
						fontSize: "13px",
						color: "var(--color-text-secondary)",
						fontWeight: 600,
					}}
				>
					14일 무료 체험 · 이후 월 9,900원 · 언제든 해지 가능
				</p>
			</section>

			{/* Features grid */}
			<section
				aria-label="주요 기능"
				style={{
					maxWidth: "720px",
					margin: "0 auto",
					padding: "0 20px 80px",
				}}
			>
				<div
					style={{
						display: "grid",
						gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
						gap: "14px",
					}}
				>
					{FEATURES.map((f) => (
						<div
							key={f.title}
							style={{
								background: "var(--color-surface-elevated)",
								border: "1px solid var(--color-surface-stroke)",
								borderRadius: "18px",
								padding: "20px 16px",
							}}
						>
							<div
								style={{ fontSize: "28px", lineHeight: 1, marginBottom: "10px" }}
								aria-hidden="true"
							>
								{f.icon}
							</div>
							<div
								role="heading"
								aria-level={3}
								style={{
									fontWeight: 700,
									fontSize: "14px",
									marginBottom: "6px",
									color: "var(--color-text)",
								}}
							>
								{f.title}
							</div>
							<div
								style={{
									fontSize: "12px",
									color: "var(--color-text-secondary)",
									lineHeight: 1.5,
								}}
							>
								{f.desc}
							</div>
						</div>
					))}
				</div>
			</section>

			{/* Pricing callout */}
			<section
				aria-label="요금 안내"
				style={{
					background: "var(--color-surface)",
					borderTop: "1px solid var(--color-surface-stroke)",
					borderBottom: "1px solid var(--color-surface-stroke)",
					textAlign: "center",
					padding: "48px 24px",
				}}
			>
				<p
					role="heading"
					aria-level={2}
					style={{
						fontSize: "13px",
						color: "var(--color-text-secondary)",
						marginBottom: "8px",
						textTransform: "uppercase",
						letterSpacing: "0.08em",
						fontWeight: 600,
					}}
				>
					심플한 요금제
				</p>
				<div
					style={{
						fontFamily: "var(--font-display-custom)",
						fontSize: "clamp(32px, 6vw, 48px)",
						fontWeight: 800,
						color: "var(--color-primary-custom)",
						marginBottom: "4px",
					}}
				>
					9,900원
				</div>
				<p style={{ color: "var(--color-text-secondary)", marginBottom: "8px" }}>
					/ 월 · 모든 기능 포함 · 언제든 해지 가능
				</p>
				<div
					style={{
						display: "inline-block",
						background: "color-mix(in srgb, var(--color-success) 12%, transparent)",
						color: "var(--color-success)",
						borderRadius: "100px",
						padding: "5px 14px",
						fontSize: "13px",
						fontWeight: 700,
						marginBottom: "20px",
					}}
				>
					✓ 14일 무료 체험 시작 · 카드 등록 불필요
				</div>
				<Link
					href="/register"
					style={{
						display: "inline-block",
						background: "var(--color-primary-custom)",
						color: "#fff",
						borderRadius: "12px",
						padding: "12px 32px",
						fontSize: "15px",
						fontWeight: 700,
						textDecoration: "none",
					}}
				>
					지금 시작하기
				</Link>
			</section>
			</main>

			{/* Footer */}
			<footer
				style={{
					textAlign: "center",
					padding: "32px 24px",
					fontSize: "12px",
					color: "var(--color-text-secondary)",
				}}
			>
				<div style={{ marginBottom: "8px" }}>
					<Link
						href="/terms"
						style={{
							color: "var(--color-text-secondary)",
							textDecoration: "none",
							marginRight: "16px",
						}}
					>
						이용약관
					</Link>
					<Link
						href="/privacy"
						style={{ color: "var(--color-text-secondary)", textDecoration: "none" }}
					>
						개인정보처리방침
					</Link>
				</div>
				<div>© {new Date().getFullYear()} Joolife. All rights reserved.</div>
			</footer>
		</div>
	);
}
