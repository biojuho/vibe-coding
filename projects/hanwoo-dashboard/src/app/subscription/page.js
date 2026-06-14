import PaymentWidget from "@/components/payment/PaymentWidget";
import CancelSubscriptionButton from "@/components/subscription/CancelSubscriptionButton";
import { requireAuthenticatedSession } from "@/lib/auth-guard";
import { buildCustomerKey, PREMIUM_SUBSCRIPTION } from "@/lib/subscription";
import { getSubscriptionStatus } from "@/lib/subscription-queries";

const clientKey = process.env.NEXT_PUBLIC_TOSS_PAYMENTS_CLIENT_KEY || "";

function ActiveSubscriptionView({ daysLeft, nextPaymentDate, cancelSuccess }) {
	const nextDate =
		nextPaymentDate instanceof Date
			? nextPaymentDate.toLocaleDateString("ko-KR")
			: nextPaymentDate
				? new Date(nextPaymentDate).toLocaleDateString("ko-KR")
				: null;

	return (
		<div
			style={{
				background: "var(--color-surface-elevated)",
				border: "1px solid var(--color-surface-stroke)",
				borderRadius: "20px",
				padding: "24px",
				textAlign: "center",
			}}
		>
			<div style={{ fontSize: "40px", marginBottom: "12px" }}>✅</div>
			<div
				style={{
					fontSize: "18px",
					fontWeight: "800",
					color: "var(--color-text)",
					marginBottom: "8px",
				}}
			>
				프리미엄 구독 중
			</div>
			<p style={{ color: "var(--color-text-secondary)", fontSize: "14px", marginBottom: "4px" }}>
				모든 기능을 제한 없이 사용하실 수 있습니다.
			</p>
			{nextDate && (
				<p style={{ color: "var(--color-text-secondary)", fontSize: "13px" }}>
					다음 결제일: <strong style={{ color: "var(--color-text)" }}>{nextDate}</strong>
					{daysLeft != null && ` (${daysLeft}일 후)`}
				</p>
			)}
			{cancelSuccess && (
				<p
					role="alert"
					style={{
						marginTop: "12px",
						fontSize: "13px",
						color: "var(--color-danger)",
						fontWeight: 600,
					}}
				>
					구독이 해지되었습니다. 이미 결제된 기간은 환불되지 않습니다.
				</p>
			)}
			<CancelSubscriptionButton />
		</div>
	);
}

function TrialSubscriptionView({ daysLeft, customerKey, amount, orderName, customerName }) {
	return (
		<div>
			<div
				style={{
					background: "var(--color-surface-elevated)",
					border: "1px solid var(--color-accent)",
					borderRadius: "20px",
					padding: "20px 24px",
					marginBottom: "24px",
					display: "flex",
					alignItems: "center",
					gap: "14px",
				}}
			>
				<span style={{ fontSize: "32px" }}>🎉</span>
				<div>
					<div style={{ fontSize: "15px", fontWeight: "800", color: "var(--color-text)", marginBottom: "4px" }}>
						무료 체험판 사용 중
					</div>
					<div style={{ fontSize: "13px", color: "var(--color-text-secondary)" }}>
						{daysLeft != null && daysLeft > 0
							? `${daysLeft}일 남았습니다. 체험이 끝나기 전에 구독하세요.`
							: "체험 기간이 오늘 만료됩니다."}
					</div>
				</div>
			</div>
			<PaymentWidget
				clientKey={clientKey}
				isClientKeyConfigured={Boolean(clientKey)}
				customerKey={customerKey}
				amount={amount}
				orderName={orderName}
				customerName={customerName}
			/>
		</div>
	);
}

export default async function SubscriptionPage({ searchParams }) {
	const session = await requireAuthenticatedSession({ redirectToLogin: true });
	const params = await Promise.resolve(searchParams);
	const cancelStatus = params?.cancel ?? null;
	const customerKey = buildCustomerKey(session.user.id);
	const subscriptionStatus = await getSubscriptionStatus(session.user.id).catch(() => ({
		status: "INACTIVE",
		daysLeft: null,
	}));

	const customerName = session.user.name || session.user.username || "Joolife 사용자";

	const features = [
		{ icon: "🤖", title: "AI 인사이트", desc: "매일 농장 상태 분석·조언" },
		{ icon: "📊", title: "수익성 분석", desc: "개체별 예상 수익 자동 계산" },
		{ icon: "📈", title: "실시간 시세", desc: "KAPE 한우 시세 자동 연동" },
		{ icon: "📋", title: "엑셀 내보내기", desc: "개체 대장 원클릭 다운로드" },
		{ icon: "🔔", title: "스마트 알림", desc: "발정·분만·재고 부족 즉시 알림" },
		{ icon: "☁️", title: "클라우드 동기화", desc: "오프라인 작업 자동 백업" },
	];

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
				{features.map((feature) => (
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
							<div
								style={{
									fontSize: "13px",
									fontWeight: 700,
									color: "var(--color-text)",
									marginBottom: "2px",
								}}
							>
								{feature.title}
							</div>
							<div
								style={{
									fontSize: "11px",
									color: "var(--color-text-secondary)",
									lineHeight: 1.4,
								}}
							>
								{feature.desc}
							</div>
						</div>
					</div>
				))}
			</div>

			{subscriptionStatus.status === "ACTIVE" ? (
				<ActiveSubscriptionView
					daysLeft={subscriptionStatus.daysLeft}
					nextPaymentDate={subscriptionStatus.nextPaymentDate}
					cancelSuccess={cancelStatus === "success"}
				/>
			) : subscriptionStatus.status === "TRIAL" ? (
				<TrialSubscriptionView
					daysLeft={subscriptionStatus.daysLeft}
					customerKey={customerKey}
					amount={PREMIUM_SUBSCRIPTION.amount}
					orderName={PREMIUM_SUBSCRIPTION.displayName}
					customerName={customerName}
				/>
			) : (
				<PaymentWidget
					clientKey={clientKey}
					isClientKeyConfigured={Boolean(clientKey)}
					customerKey={customerKey}
					amount={PREMIUM_SUBSCRIPTION.amount}
					orderName={PREMIUM_SUBSCRIPTION.displayName}
					customerName={customerName}
				/>
			)}
		</div>
	);
}
