import { Compass } from "lucide-react";
import Link from "next/link";

// 404 page matching the dashboard's dark theme.
export default function NotFound() {
	return (
		<div className="flex min-h-screen items-center justify-center bg-[#0f172a] p-4 font-sans text-white">
			<div className="w-full max-w-md space-y-6 rounded-2xl border border-white/10 bg-slate-900/60 p-8 text-center backdrop-blur-md">
				<Compass className="mx-auto h-12 w-12 text-blue-400" />
				<div className="space-y-2">
					<h1 className="text-2xl font-bold">페이지를 찾을 수 없습니다</h1>
					<p className="text-sm text-slate-400">
						요청하신 페이지가 존재하지 않거나 이동되었습니다.
					</p>
				</div>
				<Link
					href="/"
					className="inline-block rounded-md bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
				>
					대시보드로 돌아가기
				</Link>
			</div>
		</div>
	);
}
