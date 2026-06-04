// Pure view helpers for the dashboard page: smart tagging, search filtering,
// language stats, and timestamp/freshness formatting. Framework-free and unit
// tested in dashboard-view.test.mts.
import type { GithubRepo, Notebook } from "@/lib/dashboard-types";

export interface TagChip {
	label: string;
	color: string;
}

// Bilingual keyword → tag rules. Order is preserved; at most 3 tags per item.
const TAG_RULES: Array<{ keywords: string[]; tag: TagChip }> = [
	{
		keywords: ["analysis", "report", "study", "연구"],
		tag: { label: "연구 (Research)", color: "bg-indigo-500/20 text-indigo-300" },
	},
	{
		keywords: ["project", "app", "web", "dev", "코딩"],
		tag: { label: "개발 (Dev)", color: "bg-emerald-500/20 text-emerald-300" },
	},
	{
		keywords: ["meeting", "plan", "회의", "기획"],
		tag: { label: "기획 (Plan)", color: "bg-orange-500/20 text-orange-300" },
	},
	{
		keywords: ["paper", "pdf", "논문"],
		tag: { label: "자료 (Docs)", color: "bg-sky-500/20 text-sky-300" },
	},
];

function taggableText(item: GithubRepo | Notebook): string {
	if ("name" in item) {
		return `${item.name} ${item.description || ""} ${item.language || ""}`.toLowerCase();
	}
	const sourceTitles = item.sources?.map((s) => s.title).join(" ") || "";
	return `${item.title} ${sourceTitles}`.toLowerCase();
}

export function getTags(item: GithubRepo | Notebook): TagChip[] {
	const text = taggableText(item);
	const tags: TagChip[] = [];
	for (const rule of TAG_RULES) {
		if (rule.keywords.some((keyword) => text.includes(keyword))) {
			tags.push(rule.tag);
		}
	}
	return tags.slice(0, 3);
}

export interface FilteredDashboard {
	github: GithubRepo[];
	notebooklm: Notebook[];
}

export function filterDashboard(
	data: { github: GithubRepo[]; notebooklm: Notebook[] } | null,
	term: string,
): FilteredDashboard {
	if (!data) return { github: [], notebooklm: [] };

	const lowerTerm = term.trim().toLowerCase();
	if (!lowerTerm) {
		return { github: data.github, notebooklm: data.notebooklm };
	}

	return {
		github: data.github.filter(
			(repo) =>
				repo.name.toLowerCase().includes(lowerTerm) ||
				(repo.description &&
					repo.description.toLowerCase().includes(lowerTerm)) ||
				(repo.language && repo.language.toLowerCase().includes(lowerTerm)),
		),
		notebooklm: data.notebooklm.filter((nb) =>
			nb.title.toLowerCase().includes(lowerTerm),
		),
	};
}

export interface LanguageStats {
	sortedLangs: Array<[string, number]>;
	// Count of repos that actually declare a language — the correct denominator
	// for proportional bars (repos with language === null are excluded so the
	// visible bars sum to ~100% of classified repos).
	classifiedCount: number;
	totalSources: number;
}

export function computeLanguageStats(
	github: GithubRepo[],
	notebooklm: Notebook[],
): LanguageStats {
	const languages: Record<string, number> = {};
	for (const repo of github) {
		if (repo.language) {
			languages[repo.language] = (languages[repo.language] || 0) + 1;
		}
	}
	const sortedLangs = Object.entries(languages).sort(([, a], [, b]) => b - a);
	const classifiedCount = sortedLangs.reduce((sum, [, count]) => sum + count, 0);
	const totalSources = notebooklm.reduce(
		(acc, nb) => acc + nb.source_count,
		0,
	);
	return { sortedLangs, classifiedCount, totalSources };
}

// ── Timestamp & freshness ────────────────────────────────────────────────────

const timeFormatter = new Intl.DateTimeFormat("ko-KR", {
	dateStyle: "medium",
	timeStyle: "short",
});

// Locale-stable absolute time, with an explicit fallback for unparseable input.
export function formatTimestamp(iso: string | undefined | null): string {
	if (!iso) return "—";
	const date = new Date(iso);
	if (Number.isNaN(date.getTime())) return "—";
	return timeFormatter.format(date);
}

export function formatRelativeTime(
	iso: string | undefined | null,
	now: number = Date.now(),
): string {
	if (!iso) return "—";
	const then = new Date(iso).getTime();
	if (Number.isNaN(then)) return "—";

	const diffSec = Math.round((now - then) / 1000);
	if (diffSec < 0) return "방금";
	if (diffSec < 60) return "방금";
	const diffMin = Math.floor(diffSec / 60);
	if (diffMin < 60) return `${diffMin}분 전`;
	const diffHr = Math.floor(diffMin / 60);
	if (diffHr < 24) return `${diffHr}시간 전`;
	const diffDay = Math.floor(diffHr / 24);
	return `${diffDay}일 전`;
}

export type FreshnessTone = "fresh" | "recent" | "stale";

export interface Freshness {
	tone: FreshnessTone;
	label: string;
	relative: string;
	absolute: string;
}

const ONE_HOUR_MS = 60 * 60 * 1000;
const ONE_DAY_MS = 24 * ONE_HOUR_MS;

// Classifies how stale the synced data is so the header can stop showing a
// permanent green "active" pulse on day-old data.
export function getDataFreshness(
	iso: string | undefined | null,
	now: number = Date.now(),
): Freshness {
	const relative = formatRelativeTime(iso, now);
	const absolute = formatTimestamp(iso);
	const then = iso ? new Date(iso).getTime() : Number.NaN;

	if (Number.isNaN(then)) {
		return { tone: "stale", label: "동기화 필요", relative: "—", absolute };
	}

	const age = now - then;
	if (age < ONE_HOUR_MS) {
		return { tone: "fresh", label: "실시간", relative, absolute };
	}
	if (age < ONE_DAY_MS) {
		return { tone: "recent", label: "최근 동기화", relative, absolute };
	}
	return { tone: "stale", label: "갱신 권장", relative, absolute };
}
