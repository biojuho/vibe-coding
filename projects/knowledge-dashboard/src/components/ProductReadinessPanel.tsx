"use client";

import {
	AlertTriangle,
	CheckCircle2,
	CircleDot,
	GitBranch,
	ShieldCheck,
	SquareActivity,
	Wrench,
	XCircle,
} from "lucide-react";
import {
	type ReadinessState,
	resolveReadinessState,
	resolveSkillStatusState,
} from "@/lib/readiness-view";

interface ReadinessTask {
	id: string;
	task: string;
	owner: string;
	section: string;
}

interface ReadinessProject {
	name: string;
	path: string;
	score: number;
	state: ReadinessState;
	qc: {
		available: boolean;
		status: string;
		passed: number;
		failed: number;
		skipped: number;
		checked_at?: string | null;
		age_days?: number | null;
		stale?: boolean;
	};
	tasks: ReadinessTask[];
	dirty_paths: string[];
	docs: Array<{ path: string; present: boolean }>;
	env: {
		available: boolean;
		score: number;
		checks: Array<{
			name: string;
			ok: boolean;
			severity: string;
			message: string;
		}>;
	};
	recommendations: string[];
}

interface NextAction {
	project: string;
	state: ReadinessState;
	score: number;
	action: string;
}

export interface ProductReadinessData {
	generated_at: string;
	overall: {
		score: number;
		state: ReadinessState;
		project_count: number;
		blocked_count: number;
		workspace_blocker_count: number;
	};
	projects: ReadinessProject[];
	workspace_blockers: ReadinessTask[];
	next_actions: NextAction[];
}

export interface SkillLintData {
	generated_at: string;
	summary: {
		status: "pass" | "warn" | "fail";
		score: number;
		skill_count: number;
		healthy_count: number;
		warning_count: number;
		error_count: number;
		issue_count: number;
	};
	top_issues: Array<{ code: string; count: number }>;
	issues: Array<{
		skill: string;
		path: string;
		severity: "warning" | "error";
		code: string;
		message: string;
	}>;
}

interface ProductReadinessPanelProps {
	data: ProductReadinessData;
	skillLint?: SkillLintData;
}

const stateConfig: Record<
	ReadinessState,
	{
		label: string;
		border: string;
		text: string;
		bar: string;
		icon: React.ReactNode;
	}
> = {
	ready: {
		label: "준비됨",
		border: "border-emerald-500/30",
		text: "text-emerald-300",
		bar: "bg-emerald-400",
		icon: <CheckCircle2 className="h-4 w-4" aria-hidden="true" />,
	},
	"needs-review": {
		label: "검토 필요",
		border: "border-amber-500/30",
		text: "text-amber-300",
		bar: "bg-amber-400",
		icon: <AlertTriangle className="h-4 w-4" aria-hidden="true" />,
	},
	blocked: {
		label: "차단됨",
		border: "border-rose-500/30",
		text: "text-rose-300",
		bar: "bg-rose-400",
		icon: <XCircle className="h-4 w-4" aria-hidden="true" />,
	},
	"at-risk": {
		label: "위험",
		border: "border-orange-500/30",
		text: "text-orange-300",
		bar: "bg-orange-400",
		icon: <AlertTriangle className="h-4 w-4" aria-hidden="true" />,
	},
};

function StatePill({ state }: { state: ReadinessState }) {
	const config = stateConfig[resolveReadinessState(state)];
	return (
		<span
			className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${config.border} ${config.text}`}
		>
			{config.icon}
			{config.label}
		</span>
	);
}

function ScoreBar({ score, state }: { score: number; state: ReadinessState }) {
	const config = stateConfig[resolveReadinessState(state)];
	return (
		<div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
			<div
				className={`h-full rounded-full ${config.bar}`}
				style={{ width: `${Math.max(4, Math.min(100, score))}%` }}
			/>
		</div>
	);
}

function MetricTile({
	label,
	value,
	tone,
}: {
	label: string;
	value: string;
	tone: string;
}) {
	return (
		<div className="rounded-lg border border-white/5 bg-slate-950/40 px-4 py-3">
			<p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
			<p className={`mt-1 text-2xl font-semibold ${tone}`}>{value}</p>
		</div>
	);
}

function QcFreshness({ qc }: { qc: ReadinessProject["qc"] }) {
	if (!qc.available) {
		return <p className="text-xs text-slate-400">QC 미실행</p>;
	}
	if (qc.stale) {
		const age =
			typeof qc.age_days === "number" ? `${qc.age_days}일 경과` : "오래됨";
		return <p className="text-xs text-amber-300">{age}</p>;
	}
	if (typeof qc.age_days === "number") {
		return <p className="text-xs text-emerald-300">{qc.age_days}일 경과</p>;
	}
	return <p className="text-xs text-slate-400">신선도 불명</p>;
}

export default function ProductReadinessPanel({
	data,
	skillLint,
}: ProductReadinessPanelProps) {
	const generatedAt = new Date(data.generated_at).toLocaleString();
	const overallState = resolveReadinessState(data.overall.state);
	const skillStatusState = resolveSkillStatusState(skillLint);
	const workspaceBlockers = data.workspace_blockers ?? [];

	return (
		<div className="space-y-6">
			<section
				className={`rounded-lg border bg-slate-950/50 p-6 ${stateConfig[overallState].border}`}
			>
				<div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
					<div>
						<div className="mb-3 flex items-center gap-3">
							<div className="rounded-lg border border-white/10 bg-white/5 p-2 text-cyan-300">
								<SquareActivity className="h-5 w-5" aria-hidden="true" />
							</div>
							<StatePill state={overallState} />
						</div>
						<h2 className="text-2xl font-semibold text-white">
							제품 운영 콘솔
						</h2>
						<p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
							출시 신뢰도는 QC 신선도, 미해결 블로커, 문서화, 워크트리 정리
							상태, 런타임 준비도를 종합해 산출됩니다.
						</p>
					</div>
					<div className="min-w-[220px] rounded-lg border border-white/5 bg-slate-900/60 p-5">
						<div className="flex items-end justify-between gap-4">
							<span className="text-sm text-slate-400">종합 점수</span>
							<span className="text-4xl font-semibold text-white">
								{data.overall.score}
							</span>
						</div>
						<div className="mt-4">
							<ScoreBar score={data.overall.score} state={overallState} />
						</div>
						<p className="mt-3 text-xs text-slate-400">생성: {generatedAt}</p>
					</div>
				</div>
			</section>

			<div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
				<MetricTile
					label="프로젝트"
					value={`${data.overall.project_count}`}
					tone="text-cyan-300"
				/>
				<MetricTile
					label="차단됨"
					value={`${data.overall.blocked_count}`}
					tone="text-rose-300"
				/>
				<MetricTile
					label="워크스페이스 작업"
					value={`${data.overall.workspace_blocker_count}`}
					tone="text-amber-300"
				/>
				<MetricTile
					label="준비된 프로젝트"
					value={`${data.projects.filter((project) => project.state === "ready").length}`}
					tone="text-emerald-300"
				/>
			</div>

			<section className="rounded-lg border border-white/5 bg-slate-900/40 p-5">
				<div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
					<div>
						<h3 className="flex items-center gap-2 text-lg font-semibold text-white">
							<Wrench className="h-5 w-5 text-cyan-300" aria-hidden="true" />
							에이전트 스킬 상태
						</h3>
						<p className="mt-1 text-sm leading-6 text-slate-400">
							스킬 메타데이터, 트리거 가이드, 중복 이름, 로컬 참조를 자동화
							드리프트가 되기 전에 점검합니다.
						</p>
					</div>
					<div className="flex items-center gap-3">
						<StatePill state={skillStatusState} />
						<span className="text-3xl font-semibold text-white">
							{skillLint?.summary.score ?? "--"}
						</span>
					</div>
				</div>

				{skillLint ? (
					<div className="mt-5 grid gap-3 lg:grid-cols-[0.8fr_1.2fr]">
						<div className="grid grid-cols-2 gap-3">
							<MetricTile
								label="스킬"
								value={`${skillLint.summary.skill_count}`}
								tone="text-cyan-300"
							/>
							<MetricTile
								label="정상"
								value={`${skillLint.summary.healthy_count}`}
								tone="text-emerald-300"
							/>
							<MetricTile
								label="경고"
								value={`${skillLint.summary.warning_count}`}
								tone="text-amber-300"
							/>
							<MetricTile
								label="오류"
								value={`${skillLint.summary.error_count}`}
								tone="text-rose-300"
							/>
						</div>
						<div className="grid gap-3 md:grid-cols-2">
							{skillLint.issues.slice(0, 4).map((issue) => (
								<div
									key={`${issue.path}-${issue.code}-${issue.message}`}
									className="rounded-lg border border-white/5 bg-slate-950/35 p-3"
								>
									<div className="flex items-center justify-between gap-3">
										<span className="truncate text-sm font-medium text-white">
											{issue.skill}
										</span>
										<span
											className={
												issue.severity === "error"
													? "text-xs text-rose-300"
													: "text-xs text-amber-300"
											}
										>
											{issue.code}
										</span>
									</div>
									<p className="mt-1 truncate text-xs text-slate-400">
										{issue.path}
									</p>
									<p className="mt-2 text-sm leading-6 text-slate-400">
										{issue.message}
									</p>
								</div>
							))}
							{skillLint.issues.length === 0 && (
								<p className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 text-sm leading-6 text-emerald-200">
									모든 로컬 스킬이 메타데이터 및 참조 검사를 통과했습니다.
								</p>
							)}
						</div>
					</div>
				) : (
					<p className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-sm text-amber-100">
						스킬 린트 데이터가 아직 생성되지 않았습니다.
					</p>
				)}
			</section>

			<section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
				<div className="space-y-4">
					{data.projects.map((project) => (
						<article
							key={project.name}
							className="rounded-lg border border-white/5 bg-slate-900/40 p-5"
						>
							<div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
								<div className="min-w-0">
									<div className="flex flex-wrap items-center gap-3">
										<h3 className="text-lg font-semibold text-white">
											{project.name}
										</h3>
										<StatePill state={project.state} />
									</div>
									<p className="mt-1 text-xs text-slate-400">{project.path}</p>
								</div>
								<div className="w-full md:w-48">
									<div className="mb-2 flex items-center justify-between text-sm">
										<span className="text-slate-400">준비도</span>
										<span className="font-semibold text-white">
											{project.score}
										</span>
									</div>
									<ScoreBar score={project.score} state={project.state} />
								</div>
							</div>

							<div className="mt-5 grid gap-3 md:grid-cols-4">
								<div className="rounded-lg border border-white/5 bg-slate-950/35 p-3">
									<p className="text-xs text-slate-400">QC</p>
									<p className="mt-1 text-sm font-medium text-white">
										{project.qc?.status ?? "—"}
									</p>
									<p className="text-xs text-slate-400">
										{project.qc?.passed ?? 0} 통과 / {project.qc?.failed ?? 0} 실패
									</p>
									<QcFreshness qc={project.qc} />
								</div>
								<div className="rounded-lg border border-white/5 bg-slate-950/35 p-3">
									<p className="text-xs text-slate-400">미해결 작업</p>
									<p className="mt-1 text-sm font-medium text-white">
										{project.tasks?.length ?? 0}
									</p>
									<p className="text-xs text-slate-400">
										{project.tasks?.[0]?.owner || "담당자 없음"}
									</p>
								</div>
								<div className="rounded-lg border border-white/5 bg-slate-950/35 p-3">
									<p className="text-xs text-slate-400">변경된 파일</p>
									<p className="mt-1 text-sm font-medium text-white">
										{project.dirty_paths?.length ?? 0}
									</p>
									<p className="truncate text-xs text-slate-400">
										{project.dirty_paths?.[0] || "깨끗함"}
									</p>
								</div>
								<div className="rounded-lg border border-white/5 bg-slate-950/35 p-3">
									<p className="text-xs text-slate-400">문서</p>
									<p className="mt-1 text-sm font-medium text-white">
										{(project.docs ?? []).filter((item) => item.present).length}/
										{project.docs?.length ?? 0}
									</p>
									<p className="text-xs text-slate-400">필수 파일</p>
								</div>
							</div>

							<ul className="mt-4 space-y-2">
								{(project.recommendations ?? []).map((recommendation) => (
									<li
										key={recommendation}
										className="flex gap-2 text-sm leading-6 text-slate-300"
									>
										<CircleDot
											className="mt-1 h-3.5 w-3.5 shrink-0 text-cyan-300"
											aria-hidden="true"
										/>
										<span>{recommendation}</span>
									</li>
								))}
							</ul>
						</article>
					))}
				</div>

				<aside className="space-y-4">
					<div className="rounded-lg border border-white/5 bg-slate-900/40 p-5">
						<h3 className="flex items-center gap-2 text-lg font-semibold text-white">
							<ShieldCheck
								className="h-5 w-5 text-emerald-300"
								aria-hidden="true"
							/>
							다음 작업
						</h3>
						<div className="mt-4 space-y-3">
							{data.next_actions.map((action) => (
								<div
									key={`${action.project}-${action.action}`}
									className="rounded-lg border border-white/5 bg-slate-950/35 p-3"
								>
									<div className="flex items-center justify-between gap-3">
										<span className="text-sm font-medium text-white">
											{action.project}
										</span>
										<StatePill state={action.state} />
									</div>
									<p className="mt-2 text-sm leading-6 text-slate-400">
										{action.action}
									</p>
								</div>
							))}
						</div>
					</div>

					<div className="rounded-lg border border-white/5 bg-slate-900/40 p-5">
						<h3 className="flex items-center gap-2 text-lg font-semibold text-white">
							<GitBranch className="h-5 w-5 text-cyan-300" aria-hidden="true" />
							워크스페이스 블로커
						</h3>
						<div className="mt-4 space-y-3">
							{workspaceBlockers.length > 0 ? (
								workspaceBlockers.map((task) => (
									<div
										key={task.id}
										className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3"
									>
										<p className="text-xs font-medium text-amber-300">
											{task.id} / {task.owner}
										</p>
										<p className="mt-1 text-sm leading-6 text-slate-300">
											{task.task}
										</p>
									</div>
								))
							) : (
								<p className="text-sm leading-6 text-slate-400">
									현재 워크스페이스 수준의 출시 블로커가 없습니다.
								</p>
							)}
						</div>
					</div>
				</aside>
			</section>
		</div>
	);
}
