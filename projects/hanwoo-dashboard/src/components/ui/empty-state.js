import { PremiumButton } from "@/components/ui/premium-button";

export default function EmptyState({
	icon: Icon,
	title,
	description,
	actionLabel,
	onAction,
	disabled = false,
}) {
	return (
		<div className="clay-inset rounded-[24px] px-5 py-8 text-center">
			{Icon ? (
				<div
					className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full"
					style={{
						background: "var(--surface-gradient)",
						boxShadow: "var(--shadow-sm)",
						color: "var(--color-primary-custom)",
					}}
				>
					<Icon size={22} strokeWidth={2.2} aria-hidden="true" />
				</div>
			) : null}
			<div className="text-sm font-extrabold text-[color:var(--color-text)]">
				{title}
			</div>
			<div className="mx-auto mt-2 max-w-[280px] text-[13px] leading-5 text-[color:var(--color-text-muted)]">
				{description}
			</div>
			{actionLabel && onAction ? (
				<PremiumButton
					type="button"
					variant="secondary"
					size="sm"
					onClick={onAction}
					disabled={disabled}
					aria-busy={disabled}
					aria-label={actionLabel}
					title={actionLabel}
					className="mt-4 rounded-xl px-4"
				>
					{actionLabel}
				</PremiumButton>
			) : null}
		</div>
	);
}
