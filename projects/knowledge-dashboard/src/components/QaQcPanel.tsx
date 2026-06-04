"use client";

import {
	Activity,
	AlertTriangle,
	CheckCircle,
	HardDrive,
	Server,
	Shield,
	XCircle,
} from "lucide-react";
import { useMemo } from "react";
import {
	Area,
	AreaChart,
	Bar,
	BarChart,
	CartesianGrid,
	Legend,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import { buildInfraEntries, resolveVerdict } from "@/lib/qaqc-view";

// ── Types ────────────────────────────────────────────
interface ProjectResult {
	passed: number;
	failed: number;
	skipped: number;
	errors: number;
	status: string;
}

interface AstCheck {
	total: number;
	ok: number;
	failures: Array<{ file: string; error: string }>;
}

interface SecurityScan {
	status: string;
	status_detail?: string;
	issues: Array<{ file: string; pattern: string; match_preview?: string }>;
	triaged_issues?: Array<{
		file: string;
		pattern: string;
		match_preview?: string;
	}>;
	actionable_issue_count?: number;
	triaged_issue_count?: number;
}

interface Infrastructure {
	docker?: boolean;
	ollama?: boolean;
	scheduler?: { ready: number; total: number };
	disk_gb_free?: number;
}

interface TrendPoint {
	date: string;
	passed: number;
	failed: number;
}

export interface QaQcData {
	timestamp: string;
	verdict: string;
	elapsed_sec: number;
	projects: Record<string, ProjectResult>;
	total: { passed: number; failed: number };
	ast_check: AstCheck;
	security_scan: SecurityScan;
	infrastructure: Infrastructure;
	trend?: TrendPoint[];
}

interface QaQcPanelProps {
	data: QaQcData;
}

// ── Colors & Config ──────────────────────────────────
const tooltipStyle = {
	backgroundColor: "#1e293b",
	borderColor: "#334155",
	color: "#f8fafc",
};

const INFRA_ICONS: Record<string, React.ReactNode> = {
	docker: <Server className="w-4 h-4" aria-hidden="true" />,
	ollama: <Activity className="w-4 h-4" aria-hidden="true" />,
	scheduler: <Activity className="w-4 h-4" aria-hidden="true" />,
	disk: <HardDrive className="w-4 h-4" aria-hidden="true" />,
};

// ── Verdict Badge ────────────────────────────────────
function VerdictBadge({ verdict }: { verdict: string }) {
	const config = {
		APPROVED: {
			icon: <CheckCircle className="w-6 h-6" aria-hidden="true" />,
			label: "승인 (APPROVED)",
			bg: "bg-emerald-500/10",
			border: "border-emerald-500/30",
		},
		CONDITIONALLY_APPROVED: {
			icon: <AlertTriangle className="w-6 h-6" aria-hidden="true" />,
			label: "조건부 승인",
			bg: "bg-amber-500/10",
			border: "border-amber-500/30",
		},
		REJECTED: {
			icon: <XCircle className="w-6 h-6" aria-hidden="true" />,
			label: "반려 (REJECTED)",
			bg: "bg-red-500/10",
			border: "border-red-500/30",
		},
	} as const;
	const c = config[resolveVerdict(verdict)];

	return (
		<div
			className={`flex items-center gap-3 px-6 py-4 rounded-2xl border ${c.bg} ${c.border}`}
		>
			{c.icon}
			<div>
				<p className="text-lg font-bold text-white">{c.label}</p>
				<p className="text-xs text-slate-400">최종 QC 판정</p>
			</div>
		</div>
	);
}

// ── Infrastructure Status ────────────────────────────
function InfraStatus({ infra }: { infra: Infrastructure }) {
	const items = buildInfraEntries(infra);

	return (
		<div className="grid grid-cols-2 md:grid-cols-4 gap-3">
			{items.map((item) => (
				<div
					key={item.key}
					className={`flex items-center gap-2 px-4 py-3 rounded-xl border ${
						item.ok
							? "bg-emerald-500/5 border-emerald-500/20 text-emerald-400"
							: "bg-red-500/5 border-red-500/20 text-red-400"
					}`}
				>
					{INFRA_ICONS[item.key]}
					<span className="text-sm font-medium">{item.label}</span>
					<span className="ml-auto text-lg" aria-hidden="true">
						{item.ok ? "🟢" : "🔴"}
					</span>
					<span className="sr-only">{item.ok ? "정상" : "점검 필요"}</span>
				</div>
			))}
		</div>
	);
}

// ── Main Component ───────────────────────────────────
export default function QaQcPanel({ data }: QaQcPanelProps) {
	// Bar chart data for project tests
	const projectBarData = useMemo(() => {
		return Object.entries(data.projects).map(([name, result]) => ({
			name,
			passed: result.passed,
			failed: result.failed,
			skipped: result.skipped,
		}));
	}, [data.projects]);

	// Trend data (if available)
	const trendData = data.trend || [];
	const securityStatusLabel =
		data.security_scan.status_detail || data.security_scan.status;
	const triagedIssues = data.security_scan.triaged_issues || [];

	return (
		<div className="space-y-6">
			{/* Verdict Banner + Meta */}
			<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
				<div className="md:col-span-2">
					<VerdictBadge verdict={data.verdict} />
				</div>
				<div className="grid grid-cols-2 gap-3">
					<div className="bg-slate-900/40 border border-white/5 rounded-xl p-4 text-center">
						<p className="text-2xl font-bold text-blue-400">
							{data.total.passed}
						</p>
						<p className="text-xs text-slate-400">Passed</p>
					</div>
					<div className="bg-slate-900/40 border border-white/5 rounded-xl p-4 text-center">
						<p className="text-2xl font-bold text-red-400">
							{data.total.failed}
						</p>
						<p className="text-xs text-slate-400">Failed</p>
					</div>
				</div>
			</div>

			{/* Project Tests Bar Chart */}
			<div className="bg-slate-900/40 border border-white/5 rounded-2xl p-6 backdrop-blur-sm">
				<h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
					<span className="w-2 h-6 bg-blue-500 rounded-sm" aria-hidden="true" />
					프로젝트별 테스트 결과
				</h3>
				<div
					className="h-[220px] min-w-0 w-full overflow-hidden"
					role="img"
					aria-label={`프로젝트별 테스트 결과: 총 ${data.total.passed}건 통과, ${data.total.failed}건 실패, ${projectBarData.length}개 프로젝트`}
				>
					<ResponsiveContainer width="100%" height={220} minWidth={1}>
						<BarChart
							data={projectBarData}
							layout="vertical"
							margin={{ left: 80, right: 30 }}
						>
							<CartesianGrid
								strokeDasharray="3 3"
								horizontal={false}
								stroke="#334155"
							/>
							<XAxis type="number" stroke="#94a3b8" />
							<YAxis
								dataKey="name"
								type="category"
								width={100}
								stroke="#94a3b8"
								tick={{ fontSize: 13 }}
							/>
							<Tooltip contentStyle={tooltipStyle} />
							<Bar
								dataKey="passed"
								stackId="tests"
								fill="#10b981"
								radius={[0, 0, 0, 0]}
								name="Passed"
							/>
							<Bar
								dataKey="failed"
								stackId="tests"
								fill="#ef4444"
								radius={[0, 0, 0, 0]}
								name="Failed"
							/>
							<Bar
								dataKey="skipped"
								stackId="tests"
								fill="#6b7280"
								radius={[0, 4, 4, 0]}
								name="Skipped"
							/>
							<Legend />
						</BarChart>
					</ResponsiveContainer>
				</div>
			</div>

			{/* AST + Security Row */}
			<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
				{/* AST Check */}
				<div className="bg-slate-900/40 border border-white/5 rounded-2xl p-6">
					<h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
						<span
							className="w-2 h-6 bg-emerald-500 rounded-sm"
							aria-hidden="true"
						/>
						AST 구문 검증
					</h3>
					<div className="flex items-center gap-4">
						<span className="text-3xl font-bold text-emerald-400">
							{data.ast_check.ok}/{data.ast_check.total}
						</span>
						<span className="text-sm text-slate-400">파일 통과</span>
					</div>
					{data.ast_check.failures.length > 0 && (
						<div className="mt-3 space-y-1">
							{data.ast_check.failures.map((f) => (
								<p
									key={`${f.file}-${f.error}`}
									className="text-xs text-red-400 font-mono"
								>
									<span aria-hidden="true">❌ </span>
									{f.file}: {f.error}
								</p>
							))}
						</div>
					)}
				</div>

				{/* Security Scan */}
				<div className="bg-slate-900/40 border border-white/5 rounded-2xl p-6">
					<h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
						<Shield className="w-5 h-5 text-purple-400" aria-hidden="true" />
						보안 스캔
					</h3>
					<p
						className={`text-xl font-bold ${
							data.security_scan.status === "CLEAR"
								? "text-emerald-400"
								: "text-amber-400"
						}`}
					>
						{securityStatusLabel}
					</p>
					{data.security_scan.issues.length > 0 && (
						<div className="mt-3 space-y-1">
							{data.security_scan.issues.slice(0, 5).map((iss) => (
								<p
									key={`${iss.file}-${iss.pattern}`}
									className="text-xs text-amber-300 font-mono truncate"
								>
									<span aria-hidden="true">⚠️ </span>
									{iss.file}: {iss.pattern}
								</p>
							))}
						</div>
					)}
					{data.security_scan.issues.length === 0 &&
						triagedIssues.length > 0 && (
							<p className="mt-3 text-xs text-emerald-300">
								Triaged false positives:{" "}
								{data.security_scan.triaged_issue_count ?? triagedIssues.length}
							</p>
						)}
				</div>
			</div>

			{/* Infrastructure Health */}
			<div className="bg-slate-900/40 border border-white/5 rounded-2xl p-6">
				<h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
					<span className="w-2 h-6 bg-cyan-500 rounded-sm" aria-hidden="true" />
					인프라 헬스
				</h3>
				<InfraStatus infra={data.infrastructure} />
			</div>

			{/* Trend Chart (30 days) */}
			{trendData.length > 1 && (
				<div className="bg-slate-900/40 border border-white/5 rounded-2xl p-6">
					<h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
						<span
							className="w-2 h-6 bg-indigo-500 rounded-sm"
							aria-hidden="true"
						/>
						테스트 추이 (30일)
					</h3>
					<div
						className="h-[200px] min-w-0 w-full overflow-hidden"
						role="img"
						aria-label={`최근 ${trendData.length}일 테스트 통과/실패 추이`}
					>
						<ResponsiveContainer width="100%" height={200} minWidth={1}>
							<AreaChart data={trendData}>
								<CartesianGrid strokeDasharray="3 3" stroke="#334155" />
								<XAxis
									dataKey="date"
									stroke="#94a3b8"
									tick={{ fontSize: 11 }}
								/>
								<YAxis stroke="#94a3b8" />
								<Tooltip contentStyle={tooltipStyle} />
								<Area
									type="monotone"
									dataKey="passed"
									stroke="#10b981"
									fill="#10b981"
									fillOpacity={0.15}
									name="Passed"
								/>
								<Area
									type="monotone"
									dataKey="failed"
									stroke="#ef4444"
									fill="#ef4444"
									fillOpacity={0.15}
									name="Failed"
								/>
								<Legend />
							</AreaChart>
						</ResponsiveContainer>
					</div>
				</div>
			)}

			{/* Footer meta */}
			<p className="text-xs text-slate-400 text-right">
				마지막 실행: {data.timestamp?.replace("T", " ")} · 소요:{" "}
				{data.elapsed_sec}s
			</p>
		</div>
	);
}
