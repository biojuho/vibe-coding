export const MAX_OFFLINE_SYNC_RETRIES = 3;

const PERMANENT_FAILURE_PATTERNS = [
	/validation/i,
	/invalid/i,
	/required/i,
	/missing/i,
	/not found/i,
	/unknown action/i,
	/unsupported/i,
	/유효하지/i,
	/필수/i,
	/찾을 수 없/i,
	/존재하지 않/i,
];

function normalizeTimestamp(value) {
	return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function normalizeRetryCount(value) {
	return Number.isInteger(value) && value > 0 ? value : 0;
}

function normalizeObject(value) {
	return value && typeof value === "object" ? value : {};
}

export function normalizeOfflineQueueMetadata(item = {}) {
	const safeItem = normalizeObject(item);

	return {
		retryCount: normalizeRetryCount(safeItem.retryCount),
		lastAttemptAt: normalizeTimestamp(safeItem.lastAttemptAt),
		lastError:
			typeof safeItem.lastError === "string" && safeItem.lastError.length > 0
				? safeItem.lastError
				: null,
		deadLetteredAt: normalizeTimestamp(safeItem.deadLetteredAt),
	};
}

export function isPermanentOfflineQueueFailure(message) {
	if (typeof message !== "string" || message.trim().length === 0) {
		return false;
	}

	return PERMANENT_FAILURE_PATTERNS.some((pattern) => pattern.test(message));
}

export function createFailedQueueItemState(
	item,
	options = {},
) {
	const safeItem = normalizeObject(item);
	const {
		errorMessage = "",
		attemptedAt = Date.now(),
		permanent = false,
		maxRetries = MAX_OFFLINE_SYNC_RETRIES,
	} = normalizeObject(options);
	const nextRetryCount = normalizeRetryCount(safeItem.retryCount) + 1;
	const nextItem = {
		...safeItem,
		retryCount: nextRetryCount,
		lastAttemptAt: attemptedAt,
		lastError:
			typeof errorMessage === "string" && errorMessage.length > 0
				? errorMessage
				: null,
	};

	if (permanent || nextRetryCount >= maxRetries) {
		return {
			disposition: "dead-letter",
			item: {
				...nextItem,
				deadLetteredAt: attemptedAt,
			},
		};
	}

	return {
		disposition: "retry",
		item: {
			...nextItem,
			deadLetteredAt: null,
		},
	};
}
