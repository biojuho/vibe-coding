// Shared data shapes for the dashboard. Kept framework-free so the runtime type
// guards (dashboard-payload.ts) and view helpers (dashboard-view.ts) can be unit
// tested without importing React/Next.
import type { ProductReadinessData, SkillLintData } from "@/components/ProductReadinessPanel";
import type { QaQcData } from "@/components/QaQcPanel";

export interface GithubRepo {
	id: number;
	name: string;
	description: string;
	html_url: string;
	language: string | null;
	stargazers_count: number;
	updated_at: string;
}

export interface Source {
	id: string;
	title: string;
	type?: string;
}

export interface Notebook {
	id: string;
	title: string;
	source_count: number;
	url: string;
	ownership: string;
	sources?: Source[];
}

export interface SessionEntry {
	date: string;
	tool: string;
	summary: string;
	verdict?: string;
	files_changed?: number;
}

export interface DashboardData {
	last_updated: string;
	github: GithubRepo[];
	notebooklm: Notebook[];
	qaqc?: QaQcData;
	readiness?: ProductReadinessData;
	skill_lint?: SkillLintData;
	sessions?: SessionEntry[];
}

export type TabId = "operations" | "knowledge" | "qaqc" | "activity";
