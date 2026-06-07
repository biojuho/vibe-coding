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
			<p style={{ marginBottom: "30px", color: "var(--color-text-secondary)" }}>
				월 9,900원으로 농장 운영 기록과 AI 보조 기능을 더 안정적으로 사용해 주세요.
			</p>

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
