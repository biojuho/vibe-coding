import PaymentWidget from "@/components/payment/PaymentWidget";
import { requireAuthenticatedSession } from "@/lib/auth-guard";
import { buildCustomerKey, PREMIUM_SUBSCRIPTION } from "@/lib/subscription";

const clientKey = process.env.NEXT_PUBLIC_TOSS_PAYMENTS_CLIENT_KEY || "";

export default async function SubscriptionPage() {
	const session = await requireAuthenticatedSession({ redirectToLogin: true });
	const customerKey = buildCustomerKey(session.user.id);

	return (
		<div
			style={{
				maxWidth: "640px",
				margin: "0 auto",
				padding: "48px 20px 120px",
				fontFamily: "var(--font-sans-custom)",
				color: "var(--color-text)",
			}}
		>
			<h1
				style={{
					fontSize: "28px",
					fontWeight: "800",
					marginBottom: "10px",
					color: "var(--color-text)",
					fontFamily: "var(--font-display-custom)",
					letterSpacing: "0.04em",
				}}
			>
				Joolife 프리미엄 구독
			</h1>
			<p style={{ marginBottom: "24px", color: "var(--color-text-secondary)" }}>
				월 9,900원으로 농장 운영 기록과 AI 보조 기능을 더 안정적으로 사용해 주세요.
			</p>

			<div
				style={{
					display: "grid",
					gridTemplateColumns: "1fr 1fr",
					gap: "10px",
					marginBottom: "30px",
				}}
			>
				{[
					{ icon: "🤖", title: "AI 인사이트", desc: "매일 농장 상태 분석·조언" },
					{ icon: "📊", title: "수익성 분석", desc: "개체별 예상 수익 자동 계산" },
					{ icon: "📈", title: "실시간 시세", desc: "KAPE 한우 시세 자동 연동" },
					{ icon: "📋", title: "엑셀 내보내기", desc: "개체 대장 원클릭 다운로드" },
					{ icon: "🔔", title: "스마트 알림", desc: "발정·분만·재고 부족 즉시 알림" },
					{ icon: "☁️", title: "클라우드 동기화", desc: "오프라인 작업 자동 백업" },
				].map((feature) => (
					<div
						key={feature.title}
						style={{
							background: "var(--color-surface-elevated)",
							border: "1px solid var(--color-surface-stroke)",
							borderRadius: "16px",
							padding: "14px",
							display: "flex",
							alignItems: "flex-start",
							gap: "10px",
						}}
					>
						<span style={{ fontSize: "20px", lineHeight: 1, flexShrink: 0 }}>{feature.icon}</span>
						<div>
							<div style={{ fontSize: "13px", fontWeight: 700, color: "var(--color-text)", marginBottom: "2px" }}>
								{feature.title}
							</div>
							<div style={{ fontSize: "11px", color: "var(--color-text-secondary)", lineHeight: 1.4 }}>
								{feature.desc}
							</div>
						</div>
					</div>
				))}
			</div>

			<PaymentWidget
				clientKey={clientKey}
				isClientKeyConfigured={Boolean(clientKey)}
				customerKey={customerKey}
				amount={PREMIUM_SUBSCRIPTION.amount}
				orderName={PREMIUM_SUBSCRIPTION.displayName}
				customerName={
					session.user.name || session.user.username || "Joolife 사용자"
				}
			/>
		</div>
	);
}
