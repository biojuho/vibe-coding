"use client";

import { AlertTriangle } from "lucide-react";
import { useEffect } from "react";

// App Router error boundary for the dashboard segment. Catches render/runtime
// errors that escape the page's own try/catch so users get a recoverable screen
// instead of a blank page.
export default function Error({
	error,
	reset,
}: {
	error: Error & { digest?: string };
	reset: () => void;
}) {
	useEffect(() => {
		// Surfaces in server logs / browser console for diagnostics.
		console.error("Dashboard route error:", error);
	}, [error]);

	return (
		<div className="flex min-h-screen items-center justify-center bg-[#0f172a] p-4 font-sans text-white">
			<div className="w-full max-w-md space-y-6 rounded-2xl border border-white/10 bg-slate-900/60 p-8 text-center backdrop-blur-md">
				<AlertTriangle className="mx-auto h-12 w-12 text-amber-400" />
				<div className="space-y-2">
					<h1 className="text-2xl font-bold">문제가 발생했습니다</h1>
					<p className="text-sm text-slate-400">
						대시보드를 표시하는 중 예기치 못한 오류가 발생했습니다. 다시
						시도해 주세요.
					</p>
					{error.digest ? (
						<p className="font-mono text-xs text-slate-600">
							오류 코드: {error.digest}
						</p>
					) : null}
				</div>
				<button
					type="button"
					onClick={() => reset()}
					className="w-full rounded-md bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
				>
					다시 시도
				</button>
			</div>
		</div>
	);
}
