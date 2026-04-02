"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  Cell,
  CartesianGrid,
  PieChart,
  Pie,
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

const PIE_COLORS = ["#38bdf8", "#60a5fa", "#818cf8", "#a78bfa", "#f472b6", "#f59e0b"];
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
  now: "Now",
  next: "Next",
  watch: "Watch",
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
      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{label}</p>
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
          <h4 className="mt-2 text-lg font-semibold text-white">{action.title}</h4>
        </div>
        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm text-slate-100">
          {action.metricLabel}: {action.metricValue}
        </div>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-300">{action.description}</p>
    </div>
  );
}

export default function DashboardCharts({
  githubData,
  notebookData,
  query,
}: DashboardChartsProps) {
  const safeGithubData = Array.isArray(githubData) ? githubData : EMPTY_GITHUB_DATA;
  const safeNotebookData = Array.isArray(notebookData) ? notebookData : EMPTY_NOTEBOOK_DATA;
  
  const safeQuery = typeof query === "string" 
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

  const isEmpty = insights.summary.repoCount === 0 && insights.summary.notebookCount === 0;

  if (isEmpty) {
    return (
      <div className="mb-6 rounded-3xl border border-white/5 bg-slate-900/30 p-6 backdrop-blur-sm">
        <EmptyState
          title="No analytics available for this view"
          description="Clear the search term or sync more data to unlock portfolio analytics and action recommendations."
        />
      </div>
    );
  }

  return (
    <div className="mb-6 space-y-6">
      <section className="rounded-3xl border border-white/5 bg-slate-900/35 p-6 backdrop-blur-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Portfolio intelligence</p>
            <h3 className="text-2xl font-semibold text-white">Search-aware analytics that lead to action</h3>
            <p className="max-w-2xl text-sm leading-6 text-slate-400">
              The dashboard now keeps its charts, health score, and recommendations aligned with the visible slice.
            </p>
          </div>
          {safeQuery ? (
            <div className="rounded-full border border-blue-400/20 bg-blue-500/10 px-4 py-2 text-sm text-blue-100">
              Filtered by &quot;{safeQuery}&quot;
            </div>
          ) : null}
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Portfolio health"
            value={`${insights.summary.healthScore}`}
            caption="A weighted score that combines language balance, notebook coverage, and source depth."
            progress={insights.summary.healthScore}
          />
          <StatCard
            label="Diversity score"
            value={`${insights.summary.diversityScore}`}
            caption={
              insights.summary.languageCount > 1
                ? `${insights.summary.languageCount} languages are visible in the current result set.`
                : "Only one language is visible, so the portfolio is concentrated right now."
            }
            progress={insights.summary.diversityScore}
          />
          <StatCard
            label="Dominant stack"
            value={insights.summary.dominantLanguage ?? "Mixed"}
            caption={
              insights.summary.dominantLanguage
                ? `${insights.summary.dominantLanguageShare}% of visible repositories share this stack.`
                : "No single stack dominates the current slice."
            }
            progress={100 - (insights.summary.dominantLanguageShare || 0)}
          />
          <StatCard
            label="Notebook coverage"
            value={`${insights.summary.sourceCoverageRatio}%`}
            caption={
              insights.summary.zeroSourceNotebookCount > 0
                ? `${insights.summary.zeroSourceNotebookCount} notebook(s) still have zero linked sources.`
                : "Every visible notebook has at least one source attached."
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
                <p className="mt-1 text-sm leading-6 opacity-90">{badge.description}</p>
              </div>
            ))}
          </div>
        ) : null}
      </section>

      <section className="rounded-3xl border border-white/5 bg-slate-900/35 p-6 backdrop-blur-sm">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Recommended playbook</p>
            <h3 className="mt-2 text-xl font-semibold text-white">What to improve next</h3>
          </div>
          <p className="max-w-xl text-sm leading-6 text-slate-400">
            These actions are generated from the current search slice, so users do not need to manually inspect every chart before deciding what to do.
          </p>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-3">
          {insights.actions.map((action) => (
            <ActionCard key={`${action.priority}-${action.title}`} action={action} />
          ))}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <section className="rounded-3xl border border-white/5 bg-slate-900/35 p-6 backdrop-blur-sm">
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Repository mix</p>
              <h3 className="mt-2 text-lg font-semibold text-white">Language distribution</h3>
            </div>
            <div className="text-right text-sm text-slate-400">
              <p>{insights.summary.repoCount} repos</p>
              <p>{insights.summary.languageCount} distinct languages</p>
            </div>
          </div>

          {insights.languageData.length > 0 ? (
            <>
              <div className="h-[280px] w-full">
                <ResponsiveContainer width="100%" height="100%">
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
                        <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={TOOLTIP_STYLE}
                      formatter={(value, _name, item) => {
                        const share = item?.payload?.share;
                        return [`${value} repos (${share}%)`, item?.payload?.name ?? "Language"];
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
                        style={{ backgroundColor: PIE_COLORS[index % PIE_COLORS.length] }}
                      />
                      <span className="text-sm text-slate-200">{entry.name}</span>
                    </div>
                    <span className="text-sm font-medium text-slate-300">{entry.share}%</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <EmptyState
              title="No repository language data"
              description="Repositories without detected languages will appear here once fresher metadata is synced."
            />
          )}
        </section>

        <section className="rounded-3xl border border-white/5 bg-slate-900/35 p-6 backdrop-blur-sm">
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Knowledge depth</p>
              <h3 className="mt-2 text-lg font-semibold text-white">Notebook source density</h3>
            </div>
            <div className="text-right text-sm text-slate-400">
              <p>{insights.summary.notebookCount} notebooks</p>
              <p>{insights.summary.totalSources} linked sources</p>
            </div>
          </div>

          {insights.notebookData.length > 0 ? (
            <>
              <div className="h-[280px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={renderableNotebookData}
                    layout="vertical"
                    margin={{ top: 0, right: 16, left: 8, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#334155" />
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
                      formatter={(value) => [`${value} linked sources`, "Density"]}
                      labelFormatter={(_label, payload) => payload?.[0]?.payload?.fullTitle ?? ""}
                    />
                    <Bar dataKey="sources" radius={[0, 8, 8, 0]}>
                      {renderableNotebookData.map((entry, index) => (
                        <Cell key={entry.fullTitle} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="mt-4 rounded-2xl border border-white/5 bg-slate-950/40 p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Median notebook depth</p>
                    <p className="mt-2 text-2xl font-semibold text-white">
                      {insights.summary.medianSourcesPerNotebook}
                    </p>
                  </div>
                  <p className="max-w-md text-sm leading-6 text-slate-400">
                    Median is more stable than average when one notebook has an unusually large source bundle.
                  </p>
                </div>
              </div>
            </>
          ) : (
            <EmptyState
              title="No notebook density data"
              description="Once notebooks are synced, this panel will show which knowledge bases are rich enough to trust and which still need curation."
            />
          )}
        </section>
      </div>
    </div>
  );
}
