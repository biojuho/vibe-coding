import { Suspense } from "react";
import LegalReturnLink, {
	LegalReturnLinkFallback,
} from "@/components/layout/LegalReturnLink";

function normalizeLegalDocumentLayoutOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

export default function LegalDocumentLayout(options = {}) {
	const { eyebrow, title, subtitle, lastUpdated, children } =
		normalizeLegalDocumentLayoutOptions(options);

	return (
		<main id="main-content" className="clay-shell">
			<div className="clay-page-card p-6 md:p-8">
				<div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
					<div className="max-w-2xl">
						<div className="clay-page-eyebrow mb-4">{eyebrow}</div>
						<h1 className="clay-page-title mb-3">{title}</h1>
						<p className="clay-page-subtitle">{subtitle}</p>
					</div>
					<div className="clay-stat-chip">{lastUpdated}</div>
				</div>

				<nav className="mb-6 flex justify-start" aria-label="문서 상단 복귀">
					<Suspense fallback={<LegalReturnLinkFallback />}>
						<LegalReturnLink />
					</Suspense>
				</nav>

				<div className="grid gap-4">{children}</div>

				<nav className="mt-8 flex justify-center" aria-label="문서 하단 복귀">
					<Suspense fallback={<LegalReturnLinkFallback />}>
						<LegalReturnLink />
					</Suspense>
				</nav>
			</div>
		</main>
	);
}
