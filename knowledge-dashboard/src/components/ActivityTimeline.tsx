"use client";

import { useMemo } from "react";
import { Clock, GitCommit, CheckCircle, AlertTriangle, XCircle, FileText } from "lucide-react";

// ── Types ────────────────────────────────────────────
interface SessionEntry {
  date: string;
  tool: string;
  summary: string;
  verdict?: string;
  files_changed?: number;
}

interface ActivityTimelineProps {
  sessions: SessionEntry[];
}

// ── Tool Badge Colors ────────────────────────────────
const TOOL_COLORS: Record<string, string> = {
  "antigravity": "bg-blue-500/20 text-blue-300 border-blue-500/30",
  "gemini": "bg-blue-500/20 text-blue-300 border-blue-500/30",
  "claude": "bg-orange-500/20 text-orange-300 border-orange-500/30",
  "codex": "bg-green-500/20 text-green-300 border-green-500/30",
  "cursor": "bg-purple-500/20 text-purple-300 border-purple-500/30",
};

function getToolColor(tool: string): string {
  const lower = tool.toLowerCase();
  for (const [key, color] of Object.entries(TOOL_COLORS)) {
    if (lower.includes(key)) return color;
  }
  return "bg-slate-500/20 text-slate-300 border-slate-500/30";
}

function VerdictIcon({ verdict }: { verdict?: string }) {
  if (!verdict) return null;
  if (verdict.includes("승인") || verdict.includes("APPROVED"))
    return <CheckCircle className="w-4 h-4 text-emerald-400" />;
  if (verdict.includes("조건부") || verdict.includes("CONDITIONALLY"))
    return <AlertTriangle className="w-4 h-4 text-amber-400" />;
  if (verdict.includes("반려") || verdict.includes("REJECTED"))
    return <XCircle className="w-4 h-4 text-red-400" />;
  return null;
}

// ── Main Component ───────────────────────────────────
export default function ActivityTimeline({ sessions }: ActivityTimelineProps) {
  if (!sessions || sessions.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        <Clock className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>세션 활동 데이터가 없습니다.</p>
        <p className="text-xs">sync_data.py를 실행하면 SESSION_LOG.md에서 데이터를 수집합니다.</p>
      </div>
    );
  }

  // Group by date
  const grouped = useMemo(() => {
    const groups: Record<string, SessionEntry[]> = {};
    for (const s of sessions) {
      const date = s.date;
      if (!groups[date]) groups[date] = [];
      groups[date].push(s);
    }
    // Sort dates descending
    return Object.entries(groups).sort(([a], [b]) => b.localeCompare(a));
  }, [sessions]);

  return (
    <div className="space-y-6">
      {grouped.map(([date, entries]) => (
        <div key={date} className="relative">
          {/* Date header */}
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-indigo-500/20 rounded-lg text-indigo-400">
              <Clock className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-semibold text-white">{date}</h3>
            <span className="text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">
              {entries.length}개 세션
            </span>
          </div>

          {/* Timeline entries */}
          <div className="ml-4 border-l-2 border-slate-700/50 space-y-4 pl-6">
            {entries.map((entry, idx) => (
              <div
                key={idx}
                className="group relative p-5 bg-slate-900/40 border border-white/5 hover:border-indigo-500/20 rounded-xl transition-all duration-300"
              >
                {/* Timeline dot */}
                <div className="absolute -left-[33px] top-6 w-3 h-3 bg-indigo-500 rounded-full border-2 border-slate-900 group-hover:scale-125 transition-transform" />

                {/* Tool + verdict */}
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-xs px-2.5 py-1 rounded-full border ${getToolColor(entry.tool)}`}>
                    {entry.tool}
                  </span>
                  {entry.verdict && (
                    <span className="flex items-center gap-1 text-xs text-slate-400">
                      <VerdictIcon verdict={entry.verdict} />
                      {entry.verdict}
                    </span>
                  )}
                </div>

                {/* Summary */}
                <p className="text-sm text-slate-300 leading-relaxed">{entry.summary}</p>

                {/* Files changed */}
                {entry.files_changed !== undefined && entry.files_changed > 0 && (
                  <div className="flex items-center gap-1.5 mt-2 text-xs text-slate-500">
                    <FileText className="w-3.5 h-3.5" />
                    {entry.files_changed}개 파일 변경
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
