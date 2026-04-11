export const DASHBOARD_PAGINATION_MAX_PAGES = 100;

function normalizePageInfo(pageInfo = {}) {
  return {
    ...pageInfo,
    hasMore: Boolean(pageInfo?.hasMore),
    nextCursor: pageInfo?.nextCursor ?? null,
  };
}

export function sanitizeDashboardPageInfoTransition({
  currentPageInfo = null,
  receivedPageInfo = null,
  source = 'dashboard',
} = {}) {
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

export function getNextDashboardPaginationState({
  currentCursor = null,
  receivedPageInfo = null,
  seenCursors = new Set(),
  pageCount = 1,
  maxPages = DASHBOARD_PAGINATION_MAX_PAGES,
  source = 'dashboard',
} = {}) {
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

  if (seenCursors.has(normalized.nextCursor)) {
    throw new Error(`${source} pagination returned a repeated cursor.`);
  }

  return normalized;
}
