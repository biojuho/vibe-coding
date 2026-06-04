"use client";

import { useMemo } from "react";
import {
	Bar,
	BarChart,
	CartesianGrid,
	Cell,
	Pie,
	PieChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import {
	buildDashboardInsights,
	type GithubRepoLike,
	type InsightBadge,
	type NotebookLike,
	type RecommendedAction,
} from "@/lib/dashboard-insights";

interface DashboardChartsProps {
	githubData?: GithubRepoLike[] | null;
	notebookData?: NotebookLike[] | null;
	query?: string | string[] | null;
}

const EMPTY_GITHUB_DATA: GithubRepoLike[] = [];
const EMPTY_NOTEBOOK_DATA: NotebookLike[] = [];

const PIE_COLORS = [
	"#38bdf8",
	"#60a5fa",
	"#818cf8",
	"#a78bfa",
	"#f472b6",
	"#f59e0b",
];
const BAR_COLORS = ["#8b5cf6", "#9f67ff", "#b489ff", "#c9aaff", "#ddd1ff"];
const TOOLTIP_STYLE = {
	backgroundColor: "#0f172a",
	borderColor: "#334155",
	color: "#f8fafc",
	borderRadius: 12,
};

const BADGE_STYLES: Record<InsightBadge["tone"], string> = {
	blue: "border-blue-400/20 bg-blue-500/10 text-blue-100",
	emerald: "border-emerald-400/20 bg-emerald-500/10 text-emerald-100",
	amber: "border-amber-400/20 bg-amber-500/10 text-amber-100",
	rose: "border-rose-400/20 bg-rose-500/10 text-rose-100",
	violet: "border-violet-400/20 bg-violet-500/10 text-violet-100",
};

const ACTION_STYLES: Record<RecommendedAction["tone"], string> = {
	blue: "border-blue-400/20 bg-blue-500/10",
	emerald: "border-emerald-400/20 bg-emerald-500/10",
	amber: "border-amber-400/20 bg-amber-500/10",
	rose: "border-rose-400/20 bg-rose-500/10",
	violet: "border-violet-400/20 bg-violet-500/10",
};

const PRIORITY_LABELS: Record<RecommendedAction["priority"], string> = {
	now: "지금",
	next: "다음",
	watch: "관찰",
};

const getSafeProgress = (value?: number | null): number => {
	if (typeof value !== "number" || Number.isNaN(value)) return 0;
	return Math.max(0, Math.min(value, 100));
};

function EmptyState({
	title,
	description,
}: {
	title: string;
	description: string;
}) {
	return (
		<div className="flex h-[280px] items-center justify-center rounded-2xl border border-dashed border-white/10 bg-slate-950/30 p-6 text-center">
			<div className="max-w-sm space-y-2">
				<p className="text-sm font-semibold text-white">{title}</p>
				<p className="text-sm leading-6 text-slate-400">{description}</p>
			</div>
		</div>
	);
}

function StatCard({
	label,
	value,
	caption,
	progress,
}: {
	label: string;
	value: string;
	caption: string;
	progress?: number;
}) {
	const safeProgress = getSafeProgress(progress);

	return (
		<div className="rounded-2xl border border-white/5 bg-slate-950/40 p-4">
			<p className="text-xs uppercase tracking-[0.24em] text-slate-400">
				{label}
			</p>
			<p className="mt-3 text-2xl font-semibold text-white">{value}</p>
			<p className="mt-2 text-sm leading-6 text-slate-400">{caption}</p>
			{typeof progress === "number" ? (
				<div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800">
					<div
						className="h-full rounded-full bg-linear-to-r from-blue-400 via-violet-400 to-emerald-400 transition-all duration-500 ease-in-out"
						style={{ width: `${safeProgress}%` }}
					/>
				</div>
			) : null}
		</div>
	);
}

function ActionCard({ action }: { action: RecommendedAction }) {
	return (
		<div className={`rounded-2xl border p-4 ${ACTION_STYLES[action.tone]}`}>
			<div className="flex items-start justify-between gap-3">
				<div>
					<p className="text-xs uppercase tracking-[0.24em] text-slate-400">
						{PRIORITY_LABELS[action.priority]}
					</p>
					<h4 className="mt-2 text-lg font-semibold text-white">
						{action.title}
					</h4>
				</div>
				<div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm text-slate-100">
					{action.metricLabel}: {action.metricValue}
				</div>
			</div>
			<p className="mt-3 text-sm leading-6 text-slate-300">
				{action.description}
			</p>
		</div>
	);
}

export default function DashboardCharts({
	githubData,
	notebookData,
	query,
}: DashboardChartsProps) {
	const safeGithubData = Array.isArray(githubData)
		? githubData
		: EMPTY_GITHUB_DATA;
	const safeNotebookData = Array.isArray(notebookData)
		? notebookData
		: EMPTY_NOTEBOOK_DATA;

	const safeQuery =
		typeof query === "string"
			? query.trim()
			: Array.isArray(query)
				? query.join(" ").trim()
				: "";

	// Normalize all chart input through the shared insight engine so
	// cards, badges, actions, and graphs cannot drift out of sync.
	const insights = useMemo(
		() => buildDashboardInsights(safeGithubData, safeNotebookData, safeQuery),
		[safeGithubData, safeNotebookData, safeQuery],
	);

	const renderableNotebookData = useMemo(() => {
		return insights.notebookData.slice(0, 50);
	}, [insights.notebookData]);

	const isEmpty =
		insights.summary.repoCount === 0 && insights.summary.notebookCount === 0;

	if (isEmpty) {
		return (
			<div className="mb-6 rounded-3xl border border-white/5 bg-slate-900/30 p-6 backdrop-blur-sm">
				<EmptyState
					title="이 화면에 표시할 분석이 없습니다"
					description="검색어를 지우거나 데이터를 더 동기화하면 포트폴리오 분석과 추천 작업이 표시됩니다."
				/>
			</div>
		);
	}

	const languageChartLabel = `언어 분포: ${insights.languageData
		.map((d) => `${d.name} ${d.share}%`)
		.join(", ")}`;
	const notebookChartLabel = `노트북 소스 밀도: ${renderableNotebookData
		.map((d) => `${d.fullTitle} ${d.sources}개`)
		.join(", ")}`;

	return (
		<div className="mb-6 space-y-6">
			<section className="rounded-3xl border border-white/5 bg-slate-900/35 p-6 backdrop-blur-sm">
				<div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
					<div className="space-y-2">
						<p className="text-xs uppercase tracking-[0.28em] text-slate-400">
							포트폴리오 인텔리전스
						</p>
						<h3 className="text-2xl font-semibold text-white">
							행동으로 이어지는 검색 연동 분석
						</h3>
						<p className="max-w-2xl text-sm leading-6 text-slate-400">
							차트, 건강 점수, 추천이 현재 보이는 항목과 항상 일치하도록
							유지됩니다.
						</p>
					</div>
					{safeQuery ? (
						<div className="rounded-full border border-blue-400/20 bg-blue-500/10 px-4 py-2 text-sm text-blue-100">
							필터: &quot;{safeQuery}&quot;
						</div>
					) : null}
				</div>

				<div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
					<StatCard
						label="포트폴리오 건강도"
						value={`${insights.summary.healthScore}`}
						caption="언어 균형, 노트북 커버리지, 소스 깊이를 가중 합산한 점수입니다."
						progress={insights.summary.healthScore}
					/>
					<StatCard
						label="다양성 점수"
						value={`${insights.summary.diversityScore}`}
						caption={
							insights.summary.languageCount > 1
								? `현재 결과에 ${insights.summary.languageCount}개 언어가 보입니다.`
								: "현재 한 가지 언어만 보여 포트폴리오가 편중되어 있습니다."
						}
						progress={insights.summary.diversityScore}
					/>
					<StatCard
						label="주력 스택"
						value={insights.summary.dominantLanguage ?? "혼합"}
						caption={
							insights.summary.dominantLanguage
								? `표시된 저장소의 ${insights.summary.dominantLanguageShare}%가 이 스택을 사용합니다.`
								: "현재 범위에서 특정 스택이 두드러지지 않습니다."
						}
						progress={100 - (insights.summary.dominantLanguageShare || 0)}
					/>
					<StatCard
						label="노트북 커버리지"
						value={`${insights.summary.sourceCoverageRatio}%`}
						caption={
							insights.summary.zeroSourceNotebookCount > 0
								? `${insights.summary.zeroSourceNotebookCount}개 노트북에 아직 연결된 소스가 없습니다.`
								: "표시된 모든 노트북에 소스가 한 개 이상 연결되어 있습니다."
						}
						progress={insights.summary.sourceCoverageRatio}
					/>
				</div>

				{insights.badges.length > 0 ? (
					<div className="mt-4 flex flex-wrap gap-3">
						{insights.badges.map((badge) => (
							<div
								key={badge.title}
								className={`rounded-2xl border px-4 py-3 ${BADGE_STYLES[badge.tone]}`}
							>
								<p className="text-sm font-semibold">{badge.title}</p>
								<p className="mt-1 text-sm leading-6 opacity-90">
									{badge.description}
								</p>
							</div>
						))}
					</div>
				) : null}
			</section>

			<section className="rounded-3xl border border-white/5 bg-slate-900/35 p-6 backdrop-blur-sm">
				<div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
					<div>
						<p className="text-xs uppercase tracking-[0.28em] text-slate-400">
							추천 플레이북
						</p>
						<h3 className="mt-2 text-xl font-semibold text-white">
							다음 개선 항목
						</h3>
					</div>
					<p className="max-w-xl text-sm leading-6 text-slate-400">
						현재 검색 범위를 기준으로 생성된 작업이라, 모든 차트를 직접
						확인하지 않아도 무엇을 해야 할지 알 수 있습니다.
					</p>
				</div>

				<div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-3">
					{insights.actions.map((action) => (
						<ActionCard
							key={`${action.priority}-${action.title}`}
							action={action}
						/>
					))}
				</div>
			</section>

			<div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
				<section className="rounded-3xl border border-white/5 bg-slate-900/35 p-6 backdrop-blur-sm">
					<div className="mb-5 flex items-start justify-between gap-4">
						<div>
							<p className="text-xs uppercase tracking-[0.24em] text-slate-400">
								저장소 구성
							</p>
							<h3 className="mt-2 text-lg font-semibold text-white">
								언어 분포
							</h3>
						</div>
						<div className="text-right text-sm text-slate-400">
							<p>{insights.summary.repoCount}개 저장소</p>
							<p>{insights.summary.languageCount}개 언어</p>
						</div>
					</div>

					{insights.languageData.length > 0 ? (
						<>
							<div
								className="h-[280px] min-w-0 w-full overflow-hidden"
								role="img"
								aria-label={languageChartLabel}
							>
								<ResponsiveContainer width="100%" height={280} minWidth={1}>
									<PieChart>
										<Pie
											data={insights.languageData}
											cx="50%"
											cy="50%"
											innerRadius={72}
											outerRadius={102}
											paddingAngle={3}
											dataKey="value"
											stroke="rgba(15, 23, 42, 0.8)"
											strokeWidth={3}
										>
											{insights.languageData.map((entry, index) => (
												<Cell
													key={entry.name}
													fill={PIE_COLORS[index % PIE_COLORS.length]}
												/>
											))}
										</Pie>
										<Tooltip
											contentStyle={TOOLTIP_STYLE}
											formatter={(value, _name, item) => {
												const share = item?.payload?.share;
												return [
													`${value}개 (${share}%)`,
													item?.payload?.name ?? "언어",
												];
											}}
										/>
									</PieChart>
								</ResponsiveContainer>
							</div>

							<div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
								{insights.languageData.map((entry, index) => (
									<div
										key={entry.name}
										className="flex items-center justify-between rounded-2xl border border-white/5 bg-slate-950/40 px-4 py-3"
									>
										<div className="flex items-center gap-3">
											<span
												className="h-3 w-3 rounded-full"
												style={{
													backgroundColor:
														PIE_COLORS[index % PIE_COLORS.length],
												}}
											/>
											<span className="text-sm text-slate-200">
												{entry.name}
											</span>
										</div>
										<span className="text-sm font-medium text-slate-300">
											{entry.value}개 · {entry.share}%
										</span>
									</div>
								))}
							</div>
						</>
					) : (
						<EmptyState
							title="저장소 언어 데이터 없음"
							description="언어가 감지되지 않은 저장소는 더 신선한 메타데이터가 동기화되면 여기에 표시됩니다."
						/>
					)}
				</section>

				<section className="rounded-3xl border border-white/5 bg-slate-900/35 p-6 backdrop-blur-sm">
					<div className="mb-5 flex items-start justify-between gap-4">
						<div>
							<p className="text-xs uppercase tracking-[0.24em] text-slate-400">
								지식 깊이
							</p>
							<h3 className="mt-2 text-lg font-semibold text-white">
								노트북 소스 밀도
							</h3>
						</div>
						<div className="text-right text-sm text-slate-400">
							<p>{insights.summary.notebookCount}개 노트북</p>
							<p>{insights.summary.totalSources}개 연결 소스</p>
						</div>
					</div>

					{insights.notebookData.length > 0 ? (
						<>
							<div
								className="h-[280px] min-w-0 w-full overflow-hidden"
								role="img"
								aria-label={notebookChartLabel}
							>
								<ResponsiveContainer width="100%" height={280} minWidth={1}>
									<BarChart
										data={renderableNotebookData}
										layout="vertical"
										margin={{ top: 0, right: 16, left: 8, bottom: 0 }}
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
											width={120}
											stroke="#94a3b8"
											tick={{ fontSize: 12 }}
										/>
										<Tooltip
											cursor={{ fill: "rgba(255,255,255,0.04)" }}
											contentStyle={TOOLTIP_STYLE}
											formatter={(value) => [`${value}개 소스`, "밀도"]}
											labelFormatter={(_label, payload) =>
												payload?.[0]?.payload?.fullTitle ?? ""
											}
										/>
										<Bar dataKey="sources" radius={[0, 8, 8, 0]}>
											{renderableNotebookData.map((entry, index) => (
												<Cell
													key={entry.fullTitle}
													fill={BAR_COLORS[index % BAR_COLORS.length]}
												/>
											))}
										</Bar>
									</BarChart>
								</ResponsiveContainer>
							</div>

							<div className="mt-4 rounded-2xl border border-white/5 bg-slate-950/40 p-4">
								<div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
									<div>
										<p className="text-xs uppercase tracking-[0.24em] text-slate-400">
											중앙값 소스 수
										</p>
										<p className="mt-2 text-2xl font-semibold text-white">
											{insights.summary.medianSourcesPerNotebook}
										</p>
									</div>
									<p className="max-w-md text-sm leading-6 text-slate-400">
										한 노트북의 소스가 유난히 많을 때는 평균보다 중앙값이 더
										안정적입니다.
									</p>
								</div>
							</div>
						</>
					) : (
						<EmptyState
							title="노트북 밀도 데이터 없음"
							description="노트북이 동기화되면, 신뢰할 만큼 풍부한 지식 베이스와 큐레이션이 더 필요한 곳을 이 패널에서 보여줍니다."
						/>
					)}
				</section>
			</div>
		</div>
	);
}
