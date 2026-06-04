// Pure helpers for ActivityTimeline — extracted so the bilingual tool/verdict
// mappings (the parts most likely to silently drift when a tool or verdict label
// is added) are unit tested.
import type { SessionEntry } from "@/lib/dashboard-types";

const TOOL_COLORS: Record<string, string> = {
	antigravity: "bg-blue-500/20 text-blue-300 border-blue-500/30",
	gemini: "bg-blue-500/20 text-blue-300 border-blue-500/30",
	claude: "bg-orange-500/20 text-orange-300 border-orange-500/30",
	codex: "bg-green-500/20 text-green-300 border-green-500/30",
	cursor: "bg-purple-500/20 text-purple-300 border-purple-500/30",
};

const DEFAULT_TOOL_COLOR = "bg-slate-500/20 text-slate-300 border-slate-500/30";

export function getToolColor(tool: string): string {
	const lower = tool.toLowerCase();
	for (const [key, color] of Object.entries(TOOL_COLORS)) {
		if (lower.includes(key)) return color;
	}
	return DEFAULT_TOOL_COLOR;
}

export type VerdictKind = "approved" | "conditional" | "rejected" | null;

// Maps a free-text verdict (Korean or English) to a normalized kind.
// Order matters: "조건부 승인" contains "승인", so conditional is checked first.
export function getVerdictKind(verdict?: string): VerdictKind {
	if (!verdict) return null;
	if (verdict.includes("조건부") || verdict.includes("CONDITIONALLY")) {
		return "conditional";
	}
	if (verdict.includes("반려") || verdict.includes("REJECTED")) {
		return "rejected";
	}
	if (verdict.includes("승인") || verdict.includes("APPROVED")) {
		return "approved";
	}
	return null;
}

// Groups sessions by date and returns date-descending entries.
export function groupSessionsByDate(
	sessions: SessionEntry[] | undefined | null,
): Array<[string, SessionEntry[]]> {
	const groups: Record<string, SessionEntry[]> = {};
	for (const session of sessions ?? []) {
		if (!groups[session.date]) {
			groups[session.date] = [];
		}
		groups[session.date].push(session);
	}
	return Object.entries(groups).sort(([a], [b]) => b.localeCompare(a));
}
