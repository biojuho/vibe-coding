// Pure builders for the export feature (CSV / summary text). Kept framework-free
// so the escaping and formatting are unit tested; the DOM download/clipboard
// side effects live in components/ExportMenu.tsx.
import type { DashboardData, GithubRepo, Notebook } from "@/lib/dashboard-types";

// RFC-4180-ish CSV cell: wrap in quotes and double internal quotes when the cell
// contains a comma, quote, or newline.
export function csvCell(value: unknown): string {
	const str = value == null ? "" : String(value);
	if (/[",\n\r]/.test(str)) {
		return `"${str.replace(/"/g, '""')}"`;
	}
	return str;
}

export function toCsv(headers: string[], rows: Array<Array<unknown>>): string {
	const lines = [headers.map(csvCell).join(",")];
	for (const row of rows) {
		lines.push(row.map(csvCell).join(","));
	}
	return lines.join("\r\n");
}

export function buildReposCsv(repos: GithubRepo[]): string {
	return toCsv(
		["name", "language", "stars", "updated_at", "url", "description"],
		repos.map((repo) => [
			repo.name,
			repo.language ?? "",
			repo.stargazers_count,
			repo.updated_at,
			repo.html_url,
			repo.description ?? "",
		]),
	);
}

export function buildNotebooksCsv(notebooks: Notebook[]): string {
	return toCsv(
		["title", "source_count", "ownership", "url"],
		notebooks.map((nb) => [nb.title, nb.source_count, nb.ownership, nb.url]),
	);
}

// A short, human-readable clipboard summary of the current dashboard state.
export function buildSummaryText(data: DashboardData): string {
	const lines: string[] = [];
	lines.push("# 지식 관리 대시보드 요약");
	lines.push(`업데이트: ${data.last_updated}`);
	lines.push(
		`연동 자산: 저장소 ${data.github.length}개, 노트북 ${data.notebooklm.length}개`,
	);

	const totalSources = data.notebooklm.reduce(
		(sum, nb) => sum + nb.source_count,
		0,
	);
	lines.push(`참조 소스: ${totalSources}개`);

	if (data.qaqc) {
		lines.push(
			`QA/QC: ${data.qaqc.verdict} (통과 ${data.qaqc.total.passed} / 실패 ${data.qaqc.total.failed})`,
		);
	}
	if (data.readiness) {
		lines.push(
			`출시 준비도: ${data.readiness.overall.score} (${data.readiness.overall.state}), 블로커 ${data.readiness.overall.blocked_count}`,
		);
	}

	return lines.join("\n");
}
