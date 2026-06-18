// Runtime validation for untrusted API responses. These guards are the only
// contract enforced on the /api/data/* payloads before they reach render, so
// they are deliberately strict: every field a panel dereferences must be proven
// here. A payload that fails a guard degrades to the panel's "no data" empty
// state instead of throwing mid-render and (absent an error boundary) blanking
// the whole tree.
import type {
	ProductReadinessData,
	SkillLintData,
} from "@/components/ProductReadinessPanel";
import type { QaQcData } from "@/components/QaQcPanel";
import type { DashboardData } from "@/lib/dashboard-types";

export function isObject(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null;
}

function isNumber(value: unknown): value is number {
	return typeof value === "number" && !Number.isNaN(value);
}

export function isDashboardDataPayload(value: unknown): value is DashboardData {
	return (
		isObject(value) &&
		typeof value.last_updated === "string" &&
		Array.isArray(value.github) &&
		Array.isArray(value.notebooklm) &&
		(value.notebooklm as unknown[]).every(
			(nb) =>
				isObject(nb) &&
				typeof nb.title === "string" &&
				isNumber(nb.source_count),
		)
	);
}

export function isQaQcPayload(value: unknown): value is QaQcData {
	if (!isObject(value)) return false;
	if (typeof value.timestamp !== "string") return false;
	if (typeof value.verdict !== "string") return false;

	// total.passed / total.failed are read directly by the panel.
	if (!isObject(value.total)) return false;
	if (!isNumber(value.total.passed) || !isNumber(value.total.failed)) {
		return false;
	}

	// projects is iterated with Object.entries.
	if (!isObject(value.projects)) return false;

	// ast_check.ok / .total / .failures[] are all dereferenced.
	if (!isObject(value.ast_check)) return false;
	if (!Array.isArray(value.ast_check.failures)) return false;
	if (!isNumber(value.ast_check.ok) || !isNumber(value.ast_check.total)) return false;

	// security_scan.status / .issues[] are dereferenced.
	if (!isObject(value.security_scan)) return false;
	if (!Array.isArray(value.security_scan.issues)) return false;

	// infrastructure is passed to InfraStatus which reads nested fields safely.
	if (!isObject(value.infrastructure)) return false;

	return true;
}

export function isProductReadinessPayload(
	value: unknown,
): value is ProductReadinessData {
	if (!isObject(value)) return false;
	if (typeof value.generated_at !== "string") return false;
	if (!isObject(value.overall)) return false;
	// overall.score / project_count / blocked_count / workspace_blocker_count are
	// rendered directly — validate them to prevent "undefined" strings and NaN CSS.
	const overall = value.overall as Record<string, unknown>;
	if (
		!isNumber(overall.score) ||
		!isNumber(overall.project_count) ||
		!isNumber(overall.blocked_count) ||
		!isNumber(overall.workspace_blocker_count)
	)
		return false;
	if (!Array.isArray(value.projects)) return false;
	if (!Array.isArray(value.next_actions)) return false;
	// The panel reads data.workspace_blockers.length unconditionally.
	if (!Array.isArray(value.workspace_blockers)) return false;
	return true;
}

export function isSkillLintPayload(value: unknown): value is SkillLintData {
	return (
		isObject(value) &&
		typeof value.generated_at === "string" &&
		isObject(value.summary) &&
		Array.isArray(value.issues)
	);
}

export function getApiErrorMessage(value: unknown, fallback: string) {
	if (isObject(value) && typeof value.error === "string") {
		return value.error;
	}

	return fallback;
}
