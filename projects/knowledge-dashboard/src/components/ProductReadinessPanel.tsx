"use client";

import {
  AlertTriangle,
  CheckCircle2,
  CircleDot,
  GitBranch,
  ShieldCheck,
  SquareActivity,
  XCircle,
} from "lucide-react";


type ReadinessState = "ready" | "needs-review" | "blocked" | "at-risk";

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
  };
  tasks: ReadinessTask[];
  dirty_paths: string[];
  docs: Array<{ path: string; present: boolean }>;
  env: {
    available: boolean;
    score: number;
    checks: Array<{ name: string; ok: boolean; severity: string; message: string }>;
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

interface ProductReadinessPanelProps {
  data: ProductReadinessData;
}

const stateConfig: Record<ReadinessState, { label: string; border: string; text: string; bar: string; icon: React.ReactNode }> = {
  ready: {
    label: "Ready",
    border: "border-emerald-500/30",
    text: "text-emerald-300",
    bar: "bg-emerald-400",
    icon: <CheckCircle2 className="h-4 w-4" />,
  },
  "needs-review": {
    label: "Needs review",
    border: "border-amber-500/30",
    text: "text-amber-300",
    bar: "bg-amber-400",
    icon: <AlertTriangle className="h-4 w-4" />,
  },
  blocked: {
    label: "Blocked",
    border: "border-rose-500/30",
    text: "text-rose-300",
    bar: "bg-rose-400",
    icon: <XCircle className="h-4 w-4" />,
  },
  "at-risk": {
    label: "At risk",
    border: "border-orange-500/30",
    text: "text-orange-300",
    bar: "bg-orange-400",
    icon: <AlertTriangle className="h-4 w-4" />,
  },
};

function StatePill({ state }: { state: ReadinessState }) {
  const config = stateConfig[state] ?? stateConfig["at-risk"];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${config.border} ${config.text}`}>
      {config.icon}
      {config.label}
    </span>
  );
}

function ScoreBar({ score, state }: { score: number; state: ReadinessState }) {
  const config = stateConfig[state] ?? stateConfig["at-risk"];
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
      <div className={`h-full rounded-full ${config.bar}`} style={{ width: `${Math.max(4, Math.min(100, score))}%` }} />
    </div>
  );
}

function MetricTile({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="rounded-lg border border-white/5 bg-slate-950/40 px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${tone}`}>{value}</p>
    </div>
  );
}

export default function ProductReadinessPanel({ data }: ProductReadinessPanelProps) {
  const generatedAt = new Date(data.generated_at).toLocaleString();

  return (
    <div className="space-y-6">
      <section className={`rounded-lg border bg-slate-950/50 p-6 ${stateConfig[data.overall.state].border}`}>
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 flex items-center gap-3">
              <div className="rounded-lg border border-white/10 bg-white/5 p-2 text-cyan-300">
                <SquareActivity className="h-5 w-5" />
              </div>
              <StatePill state={data.overall.state} />
            </div>
            <h2 className="text-2xl font-semibold text-white">Product operations console</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
              Release confidence is scored from QC freshness, open blockers, documentation, worktree hygiene, and runtime readiness.
            </p>
          </div>
          <div className="min-w-[220px] rounded-lg border border-white/5 bg-slate-900/60 p-5">
            <div className="flex items-end justify-between gap-4">
              <span className="text-sm text-slate-400">Overall score</span>
              <span className="text-4xl font-semibold text-white">{data.overall.score}</span>
            </div>
            <div className="mt-4">
              <ScoreBar score={data.overall.score} state={data.overall.state} />
            </div>
            <p className="mt-3 text-xs text-slate-500">Generated {generatedAt}</p>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricTile label="Projects" value={`${data.overall.project_count}`} tone="text-cyan-300" />
        <MetricTile label="Blocked" value={`${data.overall.blocked_count}`} tone="text-rose-300" />
        <MetricTile label="Workspace tasks" value={`${data.overall.workspace_blocker_count}`} tone="text-amber-300" />
        <MetricTile
          label="Ready projects"
          value={`${data.projects.filter((project) => project.state === "ready").length}`}
          tone="text-emerald-300"
        />
      </div>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-4">
          {data.projects.map((project) => (
            <article key={project.name} className="rounded-lg border border-white/5 bg-slate-900/40 p-5">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-3">
                    <h3 className="text-lg font-semibold text-white">{project.name}</h3>
                    <StatePill state={project.state} />
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{project.path}</p>
                </div>
                <div className="w-full md:w-48">
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span className="text-slate-400">Readiness</span>
                    <span className="font-semibold text-white">{project.score}</span>
                  </div>
                  <ScoreBar score={project.score} state={project.state} />
                </div>
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-4">
                <div className="rounded-lg border border-white/5 bg-slate-950/35 p-3">
                  <p className="text-xs text-slate-500">QC</p>
                  <p className="mt-1 text-sm font-medium text-white">{project.qc.status}</p>
                  <p className="text-xs text-slate-500">{project.qc.passed} passed / {project.qc.failed} failed</p>
                </div>
                <div className="rounded-lg border border-white/5 bg-slate-950/35 p-3">
                  <p className="text-xs text-slate-500">Open tasks</p>
                  <p className="mt-1 text-sm font-medium text-white">{project.tasks.length}</p>
                  <p className="text-xs text-slate-500">{project.tasks[0]?.owner || "No owner block"}</p>
                </div>
                <div className="rounded-lg border border-white/5 bg-slate-950/35 p-3">
                  <p className="text-xs text-slate-500">Dirty files</p>
                  <p className="mt-1 text-sm font-medium text-white">{project.dirty_paths.length}</p>
                  <p className="truncate text-xs text-slate-500">{project.dirty_paths[0] || "Clean"}</p>
                </div>
                <div className="rounded-lg border border-white/5 bg-slate-950/35 p-3">
                  <p className="text-xs text-slate-500">Docs</p>
                  <p className="mt-1 text-sm font-medium text-white">
                    {project.docs.filter((item) => item.present).length}/{project.docs.length}
                  </p>
                  <p className="text-xs text-slate-500">required files</p>
                </div>
              </div>

              <ul className="mt-4 space-y-2">
                {project.recommendations.map((recommendation) => (
                  <li key={recommendation} className="flex gap-2 text-sm leading-6 text-slate-300">
                    <CircleDot className="mt-1 h-3.5 w-3.5 shrink-0 text-cyan-300" />
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
              <ShieldCheck className="h-5 w-5 text-emerald-300" />
              Next actions
            </h3>
            <div className="mt-4 space-y-3">
              {data.next_actions.map((action) => (
                <div key={`${action.project}-${action.action}`} className="rounded-lg border border-white/5 bg-slate-950/35 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium text-white">{action.project}</span>
                    <StatePill state={action.state} />
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-400">{action.action}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-white/5 bg-slate-900/40 p-5">
            <h3 className="flex items-center gap-2 text-lg font-semibold text-white">
              <GitBranch className="h-5 w-5 text-cyan-300" />
              Workspace blockers
            </h3>
            <div className="mt-4 space-y-3">
              {data.workspace_blockers.length > 0 ? (
                data.workspace_blockers.map((task) => (
                  <div key={task.id} className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
                    <p className="text-xs font-medium text-amber-300">{task.id} / {task.owner}</p>
                    <p className="mt-1 text-sm leading-6 text-slate-300">{task.task}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm leading-6 text-slate-400">No workspace-level release blockers are currently listed.</p>
              )}
            </div>
          </div>
        </aside>
      </section>
    </div>
  );
}
