import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export default function LegalDocumentLayout({ eyebrow, title, subtitle, lastUpdated, children }) {
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
            className="clay-pressable inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm font-semibold text-[color:var(--color-text)] no-underline"
          >
            <ArrowLeft className="h-4 w-4" />
            홈으로 돌아가기
          </Link>
        </div>
      </div>
    </div>
  );
}
