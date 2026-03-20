"use client";

import { useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, AreaChart, Area, Legend,
} from "recharts";
import { Shield, CheckCircle, AlertTriangle, XCircle, Server, HardDrive, Activity } from "lucide-react";

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
  issues: Array<{ file: string; pattern: string; match_preview?: string }>;
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
const PROJECT_COLORS = ["#3b82f6", "#8b5cf6", "#10b981"];
const tooltipStyle = { backgroundColor: "#1e293b", borderColor: "#334155", color: "#f8fafc" };

// ── Verdict Badge ────────────────────────────────────
function VerdictBadge({ verdict }: { verdict: string }) {
  const config: Record<string, { icon: React.ReactNode; label: string; bg: string; border: string }> = {
    APPROVED: {
      icon: <CheckCircle className="w-6 h-6" />,
      label: "✅ 승인 (APPROVED)",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/30",
    },
    CONDITIONALLY_APPROVED: {
      icon: <AlertTriangle className="w-6 h-6" />,
      label: "⚠️ 조건부 승인",
      bg: "bg-amber-500/10",
      border: "border-amber-500/30",
    },
    REJECTED: {
      icon: <XCircle className="w-6 h-6" />,
      label: "❌ 반려 (REJECTED)",
      bg: "bg-red-500/10",
      border: "border-red-500/30",
    },
  };
  const c = config[verdict] || config.REJECTED;

  return (
    <div className={`flex items-center gap-3 px-6 py-4 rounded-2xl border ${c.bg} ${c.border}`}>
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
  const items = [
    { label: "Docker", ok: infra.docker, icon: <Server className="w-4 h-4" /> },
    { label: "Ollama", ok: infra.ollama, icon: <Activity className="w-4 h-4" /> },
    {
      label: `Scheduler ${infra.scheduler?.ready ?? 0}/${infra.scheduler?.total ?? 0}`,
      ok: (infra.scheduler?.ready ?? 0) > 0,
      icon: <Activity className="w-4 h-4" />,
    },
    {
      label: `${infra.disk_gb_free ?? "?"} GB Free`,
      ok: (infra.disk_gb_free ?? 0) > 10,
      icon: <HardDrive className="w-4 h-4" />,
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {items.map((item) => (
        <div
          key={item.label}
          className={`flex items-center gap-2 px-4 py-3 rounded-xl border ${
            item.ok
              ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-400"
              : "bg-red-500/5 border-red-500/20 text-red-400"
          }`}
        >
          {item.icon}
          <span className="text-sm font-medium">{item.label}</span>
          <span className="ml-auto text-lg">{item.ok ? "🟢" : "🔴"}</span>
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

  return (
    <div className="space-y-6">
      {/* Verdict Banner + Meta */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2">
          <VerdictBadge verdict={data.verdict} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-900/40 border border-white/5 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-blue-400">{data.total.passed}</p>
            <p className="text-xs text-slate-500">Passed</p>
          </div>
          <div className="bg-slate-900/40 border border-white/5 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-red-400">{data.total.failed}</p>
            <p className="text-xs text-slate-500">Failed</p>
          </div>
        </div>
      </div>

      {/* Project Tests Bar Chart */}
      <div className="bg-slate-900/40 border border-white/5 rounded-2xl p-6 backdrop-blur-sm">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span className="w-2 h-6 bg-blue-500 rounded-sm" />
          프로젝트별 테스트 결과
        </h3>
        <div className="h-[220px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={projectBarData} layout="vertical" margin={{ left: 80, right: 30 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#334155" />
              <XAxis type="number" stroke="#94a3b8" />
              <YAxis dataKey="name" type="category" width={100} stroke="#94a3b8" tick={{ fontSize: 13 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="passed" stackId="tests" fill="#10b981" radius={[0, 0, 0, 0]} name="Passed" />
              <Bar dataKey="failed" stackId="tests" fill="#ef4444" radius={[0, 0, 0, 0]} name="Failed" />
              <Bar dataKey="skipped" stackId="tests" fill="#6b7280" radius={[0, 4, 4, 0]} name="Skipped" />
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
            <span className="w-2 h-6 bg-emerald-500 rounded-sm" />
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
              {data.ast_check.failures.map((f, i) => (
                <p key={i} className="text-xs text-red-400 font-mono">
                  ❌ {f.file}: {f.error}
                </p>
              ))}
            </div>
          )}
        </div>

        {/* Security Scan */}
        <div className="bg-slate-900/40 border border-white/5 rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <Shield className="w-5 h-5 text-purple-400" />
            보안 스캔
          </h3>
          <p className={`text-xl font-bold ${
            data.security_scan.status === "CLEAR" ? "text-emerald-400" : "text-amber-400"
          }`}>
            {data.security_scan.status}
          </p>
          {data.security_scan.issues.length > 0 && (
            <div className="mt-3 space-y-1">
              {data.security_scan.issues.slice(0, 5).map((iss, i) => (
                <p key={i} className="text-xs text-amber-300 font-mono truncate">
                  ⚠️ {iss.file}: {iss.pattern}
                </p>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Infrastructure Health */}
      <div className="bg-slate-900/40 border border-white/5 rounded-2xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span className="w-2 h-6 bg-cyan-500 rounded-sm" />
          인프라 헬스
        </h3>
        <InfraStatus infra={data.infrastructure} />
      </div>

      {/* Trend Chart (30 days) */}
      {trendData.length > 1 && (
        <div className="bg-slate-900/40 border border-white/5 rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <span className="w-2 h-6 bg-indigo-500 rounded-sm" />
            테스트 추이 (30일)
          </h3>
          <div className="h-[200px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={tooltipStyle} />
                <Area type="monotone" dataKey="passed" stroke="#10b981" fill="#10b981" fillOpacity={0.15} name="Passed" />
                <Area type="monotone" dataKey="failed" stroke="#ef4444" fill="#ef4444" fillOpacity={0.15} name="Failed" />
                <Legend />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Footer meta */}
      <p className="text-xs text-slate-600 text-right">
        마지막 실행: {data.timestamp?.replace("T", " ")} · 소요: {data.elapsed_sec}s
      </p>
    </div>
  );
}
