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
	return (
		isObject(value) &&
		typeof value.generated_at === "string" &&
		isObject(value.overall) &&
		Array.isArray(value.projects) &&
		Array.isArray(value.next_actions) &&
		// The panel reads data.workspace_blockers.length unconditionally.
		Array.isArray(value.workspace_blockers)
	);
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
