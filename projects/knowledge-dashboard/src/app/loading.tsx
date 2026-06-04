// Route-level fallback shown while the dashboard segment streams in, before the
// client component mounts its own data-loading state.
export default function Loading() {
	return (
		<div
			className="flex min-h-screen items-center justify-center bg-[#0f172a]"
			role="status"
			aria-live="polite"
		>
			<div className="flex flex-col items-center gap-4">
				<div className="h-12 w-12 animate-spin rounded-full border-b-2 border-blue-500 motion-reduce:animate-none" />
				<p className="text-sm text-slate-400">대시보드를 불러오는 중…</p>
			</div>
			<span className="sr-only">대시보드 로딩 중</span>
		</div>
	);
}
