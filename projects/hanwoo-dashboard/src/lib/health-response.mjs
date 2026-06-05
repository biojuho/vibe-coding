const DEFAULT_DATABASE_WARNING = "Database connectivity issue";
const BUILD_PHASE_WARNING = "health check skipped during build";

function normalizeOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeTimestamp(value) {
	return typeof value === "string" && value.trim().length > 0
		? value.trim()
		: new Date().toISOString();
}

export function normalizeHealthWarning(value) {
	if (value instanceof Error && value.message.trim().length > 0) {
		return value.message;
	}

	if (typeof value === "string" && value.trim().length > 0) {
		return value.trim();
	}

	return DEFAULT_DATABASE_WARNING;
}

export function buildHealthResponse(options = {}) {
	const safeOptions = normalizeOptions(options);
	const timestamp = normalizeTimestamp(safeOptions.timestamp);

	if (safeOptions.skipped) {
		return {
			body: {
				status: "healthy",
				database: "disconnected",
				warning: normalizeHealthWarning(
					safeOptions.warning ?? BUILD_PHASE_WARNING,
				),
				timestamp,
			},
			init: { status: 200 },
		};
	}

	if (safeOptions.connected) {
		return {
			body: {
				status: "healthy",
				database: "connected",
				timestamp,
			},
			init: { status: 200 },
		};
	}

	return {
		body: {
			status: "degraded",
			database: "disconnected",
			warning: normalizeHealthWarning(safeOptions.warning),
			timestamp,
		},
		init: { status: 503 },
	};
}
