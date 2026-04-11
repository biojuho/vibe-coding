import assert from 'node:assert/strict';
import test from 'node:test';

import {
  DASHBOARD_PAGINATION_MAX_PAGES,
  getNextDashboardPaginationState,
  sanitizeDashboardPageInfoTransition,
} from './pagination-guard.mjs';

test('sanitizeDashboardPageInfoTransition preserves valid next cursors', () => {
  const result = sanitizeDashboardPageInfoTransition({
    currentPageInfo: { nextCursor: 'cursor-1' },
    receivedPageInfo: { hasMore: true, nextCursor: 'cursor-2', limit: 50 },
    source: 'cattle',
  });

  assert.equal(result.hasMore, true);
  assert.equal(result.nextCursor, 'cursor-2');
  assert.equal(result.paginationError, null);
});

test('sanitizeDashboardPageInfoTransition stops pagination when hasMore lacks a cursor', () => {
  const result = sanitizeDashboardPageInfoTransition({
    receivedPageInfo: { hasMore: true, nextCursor: null, limit: 50 },
    source: 'sales',
  });

  assert.equal(result.hasMore, false);
  assert.equal(result.nextCursor, null);
  assert.match(result.paginationError, /without a next cursor/i);
});

test('sanitizeDashboardPageInfoTransition stops pagination when the cursor repeats', () => {
  const result = sanitizeDashboardPageInfoTransition({
    currentPageInfo: { nextCursor: 'cursor-2' },
    receivedPageInfo: { hasMore: true, nextCursor: 'cursor-2', limit: 50 },
    source: 'sales',
  });

  assert.equal(result.hasMore, false);
  assert.equal(result.nextCursor, null);
  assert.match(result.paginationError, /same cursor twice/i);
});

test('getNextDashboardPaginationState throws when the loop exceeds the page cap', () => {
  assert.throws(
    () =>
      getNextDashboardPaginationState({
        receivedPageInfo: { hasMore: true, nextCursor: 'cursor-3' },
        pageCount: DASHBOARD_PAGINATION_MAX_PAGES,
        source: 'cattle',
      }),
    /exceeded 100 pages/i,
  );
});

test('getNextDashboardPaginationState throws when a previously seen cursor reappears', () => {
  assert.throws(
    () =>
      getNextDashboardPaginationState({
        receivedPageInfo: { hasMore: true, nextCursor: 'cursor-4' },
        seenCursors: new Set(['cursor-4']),
        pageCount: 2,
        source: 'sales',
      }),
    /repeated cursor/i,
  );
});
