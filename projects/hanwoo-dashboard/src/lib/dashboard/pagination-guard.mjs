export const DASHBOARD_PAGINATION_MAX_PAGES = 100;

function isPlainObject(value) {
	return (
		value !== null &&
		typeof value === "object" &&
		!Array.isArray(value)
	);
}

function normalizePageInfo(pageInfo = {}) {
	const safePageInfo = isPlainObject(pageInfo) ? pageInfo : {};

	return {
		...safePageInfo,
		hasMore: Boolean(safePageInfo.hasMore),
		nextCursor: safePageInfo.nextCursor ?? null,
	};
}

export function sanitizeDashboardPageInfoTransition(input = {}) {
	const safeInput = isPlainObject(input) ? input : {};
	const {
		currentPageInfo = null,
		receivedPageInfo = null,
		source = "dashboard",
	} = safeInput;
	const normalized = normalizePageInfo(receivedPageInfo);

	if (!normalized.hasMore) {
		return {
			...normalized,
			paginationError: null,
		};
	}

	if (!normalized.nextCursor) {
		return {
			...normalized,
			hasMore: false,
			nextCursor: null,
			paginationError: `${source} pagination returned hasMore without a next cursor.`,
		};
	}

	const currentCursor = currentPageInfo?.nextCursor ?? null;
	if (currentCursor && normalized.nextCursor === currentCursor) {
		return {
			...normalized,
			hasMore: false,
			nextCursor: null,
			paginationError: `${source} pagination returned the same cursor twice.`,
		};
	}

	return {
		...normalized,
		paginationError: null,
	};
}

export function getNextDashboardPaginationState(input = {}) {
	const safeInput = isPlainObject(input) ? input : {};
	const {
		currentCursor = null,
		receivedPageInfo = null,
		seenCursors = new Set(),
		pageCount = 1,
		maxPages = DASHBOARD_PAGINATION_MAX_PAGES,
		source = "dashboard",
	} = safeInput;
	const safeSeenCursors = seenCursors instanceof Set ? seenCursors : new Set();
	const normalized = sanitizeDashboardPageInfoTransition({
		currentPageInfo: currentCursor ? { nextCursor: currentCursor } : null,
		receivedPageInfo,
		source,
	});

	if (normalized.paginationError) {
		throw new Error(normalized.paginationError);
	}

	if (!normalized.hasMore) {
		return normalized;
	}

	if (pageCount >= maxPages) {
		throw new Error(`${source} pagination exceeded ${maxPages} pages.`);
	}

	if (safeSeenCursors.has(normalized.nextCursor)) {
		throw new Error(`${source} pagination returned a repeated cursor.`);
	}

	return normalized;
}
