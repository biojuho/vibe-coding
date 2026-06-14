"use client";

import { useTransition, useState } from "react";
import { cancelSubscription } from "@/lib/actions/subscription";

export default function CancelSubscriptionButton() {
	const [confirming, setConfirming] = useState(false);
	const [isPending, startTransition] = useTransition();

	const handleCancel = () => {
		startTransition(async () => {
			await cancelSubscription();
		});
	};

	if (!confirming) {
		return (
			<button
				type="button"
				onClick={() => setConfirming(true)}
				aria-label="구독 해지 확인 단계 열기"
				title="구독 해지 확인 단계 열기"
				style={{
					marginTop: "16px",
					background: "none",
					border: "none",
					color: "var(--color-text-muted)",
					fontSize: "12px",
					cursor: "pointer",
					textDecoration: "underline",
					padding: 0,
				}}
			>
				구독 해지
			</button>
		);
	}

	return (
		<div
			style={{
				marginTop: "16px",
				padding: "14px",
				background: "color-mix(in srgb, var(--color-danger) 8%, transparent)",
				border: "1px solid color-mix(in srgb, var(--color-danger) 30%, transparent)",
				borderRadius: "12px",
				fontSize: "13px",
				textAlign: "left",
			}}
		>
			<p style={{ color: "var(--color-text)", fontWeight: 700, marginBottom: "6px" }}>
				구독을 해지하시겠습니까?
			</p>
			<p style={{ color: "var(--color-text-secondary)", marginBottom: "12px", lineHeight: 1.5 }}>
				해지 즉시 AI 인사이트·수익성 분석·엑셀 내보내기 등 프리미엄 기능을 사용할 수 없게 됩니다.
			</p>
			<div style={{ display: "flex", gap: "8px" }}>
				<button
					type="button"
					onClick={handleCancel}
					disabled={isPending}
					aria-busy={isPending}
					aria-label={isPending ? "구독 해지 처리 중" : "구독 해지 최종 확인"}
					style={{
						padding: "8px 16px",
						background: "var(--color-danger)",
						color: "#fff",
						border: "none",
						borderRadius: "8px",
						fontSize: "13px",
						fontWeight: 700,
						cursor: isPending ? "not-allowed" : "pointer",
						opacity: isPending ? 0.7 : 1,
					}}
				>
					{isPending ? "처리 중..." : "해지 확인"}
				</button>
				<button
					type="button"
					onClick={() => setConfirming(false)}
					disabled={isPending}
					aria-label="구독 해지 취소"
					title="구독 해지 취소"
					style={{
						padding: "8px 16px",
						background: "var(--color-surface-elevated)",
						color: "var(--color-text)",
						border: "1px solid var(--color-surface-stroke)",
						borderRadius: "8px",
						fontSize: "13px",
						fontWeight: 600,
						cursor: isPending ? "not-allowed" : "pointer",
					}}
				>
					취소
				</button>
			</div>
		</div>
	);
}
