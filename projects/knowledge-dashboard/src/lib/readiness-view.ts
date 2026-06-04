// Pure helpers for ProductReadinessPanel — readiness-state normalization and the
// skill-lint status derivation, extracted so the fallback paths are unit tested
// and cannot silently break when a new state/status value appears.

export type ReadinessState = "ready" | "needs-review" | "blocked" | "at-risk";

const KNOWN_STATES: ReadinessState[] = [
	"ready",
	"needs-review",
	"blocked",
	"at-risk",
];

// Any unknown state defaults to "at-risk" so a config lookup never returns
// undefined (which previously could throw on `.border`).
export function resolveReadinessState(state: unknown): ReadinessState {
	return (KNOWN_STATES as unknown[]).includes(state)
		? (state as ReadinessState)
		: "at-risk";
}

export function resolveSkillStatusState(
	skillLint: { summary: { status: "pass" | "warn" | "fail" } } | undefined,
): ReadinessState {
	if (!skillLint) return "needs-review";
	if (skillLint.summary.status === "pass") return "ready";
	if (skillLint.summary.status === "warn") return "needs-review";
	return "blocked";
}
