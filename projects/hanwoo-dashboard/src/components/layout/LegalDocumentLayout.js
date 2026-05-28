import { ArrowLeft } from "lucide-react";
import Link from "next/link";

function normalizeLegalDocumentLayoutOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

export default function LegalDocumentLayout(options = {}) {
	const { eyebrow, title, subtitle, lastUpdated, children } =
		normalizeLegalDocumentLayoutOptions(options);

	return (
		<div className="clay-shell">
			<div className="clay-page-card p-6 md:p-8">
				<div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
					<div className="max-w-2xl">
						<div className="clay-page-eyebrow mb-4">{eyebrow}</div>
						<h1 className="clay-page-title mb-3">{title}</h1>
						<p className="clay-page-subtitle">{subtitle}</p>
					</div>
					<div className="clay-stat-chip">{lastUpdated}</div>
				</div>

				<div className="grid gap-4">{children}</div>

				<div className="mt-8 flex justify-center">
					<Link
						href="/"
						aria-label="홈으로 돌아가기"
						title="홈으로 돌아가기"
						className="clay-pressable inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm font-semibold text-[color:var(--color-text)] no-underline"
					>
						<ArrowLeft className="h-4 w-4" aria-hidden="true" />
						홈으로 돌아가기
					</Link>
				</div>
			</div>
		</div>
	);
}
