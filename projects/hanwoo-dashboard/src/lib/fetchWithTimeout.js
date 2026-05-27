export class TimeoutError extends Error {
	constructor(message, timeoutMs) {
		super(message);
		this.name = "TimeoutError";
		this.timeoutMs = timeoutMs;
	}
}

export function isTimeoutError(error) {
	return error instanceof TimeoutError || error?.name === "TimeoutError";
}

function normalizeOptions(options) {
	return options && typeof options === "object" ? options : {};
}

export async function fetchWithTimeout(input, init = {}, options = {}) {
	const safeOptions = normalizeOptions(options);
	const timeoutMs = Number.isFinite(safeOptions.timeoutMs)
		? safeOptions.timeoutMs
		: 10000;
	const message =
		safeOptions.errorMessage || `Request timed out after ${timeoutMs}ms.`;
	const controller = new AbortController();
	const timeoutError = new TimeoutError(message, timeoutMs);
	let timeoutId = null;
	try {
		timeoutId = setTimeout(() => controller.abort(timeoutError), timeoutMs);
	} catch (error) {
		console.error("Failed to schedule fetch timeout:", error);
		controller.abort(timeoutError);
	}

	try {
		return await fetch(input, {
			...init,
			signal: controller.signal,
		});
	} catch (error) {
		if (error?.name === "AbortError" || isTimeoutError(error)) {
			throw timeoutError;
		}

		throw error;
	} finally {
		if (timeoutId !== null) {
			try {
				clearTimeout(timeoutId);
			} catch {}
		}
	}
}
