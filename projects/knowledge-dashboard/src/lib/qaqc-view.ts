// Pure helpers for QaQcPanel — the verdict resolution and infrastructure
// threshold logic, extracted so the boundary conditions (disk > 10GB, scheduler
// ready > 0) and the unknown-verdict fallback are unit tested.

export type VerdictKey = "APPROVED" | "CONDITIONALLY_APPROVED" | "REJECTED";

const KNOWN_VERDICTS: VerdictKey[] = [
	"APPROVED",
	"CONDITIONALLY_APPROVED",
	"REJECTED",
];

// Unknown/garbage verdicts fall back to REJECTED (fail-closed for a QC banner).
export function resolveVerdict(verdict: string): VerdictKey {
	return (KNOWN_VERDICTS as string[]).includes(verdict)
		? (verdict as VerdictKey)
		: "REJECTED";
}

export interface Infrastructure {
	docker?: boolean;
	ollama?: boolean;
	scheduler?: { ready: number; total: number };
	disk_gb_free?: number;
}

export interface InfraEntry {
	key: "docker" | "ollama" | "scheduler" | "disk";
	label: string;
	ok: boolean;
}

const DISK_FREE_FLOOR_GB = 10;

// Builds the infra status rows with their pass/fail evaluation. Disk is OK only
// strictly above the floor; scheduler is OK only when at least one job is ready.
export function buildInfraEntries(infra: Infrastructure): InfraEntry[] {
	const ready = infra.scheduler?.ready ?? 0;
	const total = infra.scheduler?.total ?? 0;
	const diskFree = infra.disk_gb_free;

	return [
		{ key: "docker", label: "Docker", ok: Boolean(infra.docker) },
		{ key: "ollama", label: "Ollama", ok: Boolean(infra.ollama) },
		{ key: "scheduler", label: `Scheduler ${ready}/${total}`, ok: ready > 0 },
		{
			key: "disk",
			label: `${diskFree ?? "?"} GB Free`,
			ok: (diskFree ?? 0) > DISK_FREE_FLOOR_GB,
		},
	];
}
