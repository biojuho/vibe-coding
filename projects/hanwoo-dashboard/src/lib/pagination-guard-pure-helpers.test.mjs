/**
 * Behavioral tests for pagination-guard.mjs
 *
 * Tests for sanitizeDashboardPageInfoTransition and getNextDashboardPaginationState.
 * Both exports are pure (no external deps), so we import them directly.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
	DASHBOARD_PAGINATION_MAX_PAGES,
	getNextDashboardPaginationState,
	sanitizeDashboardPageInfoTransition,
} from "../lib/dashboard/pagination-guard.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(
	path.join(SRC_ROOT, "lib/dashboard/pagination-guard.mjs"),
	"utf8",
);

// ── Source-grep guards ────────────────────────────────────────────────────────

test("pagination-guard: DASHBOARD_PAGINATION_MAX_PAGES = 100", () => {
	assert.match(src, /export const DASHBOARD_PAGINATION_MAX_PAGES = 100;/);
});

test("pagination-guard: isPlainObject checks !== null, typeof object, !Array.isArray", () => {
	assert.match(src, /function isPlainObject\(value\) \{/);
	assert.match(src, /value !== null/);
	assert.match(src, /typeof value === ["']object["']/);
	assert.match(src, /!Array\.isArray\(value\)/);
});

test("pagination-guard: normalizePageInfo spreads pageInfo and coerces hasMore via Boolean()", () => {
	assert.match(src, /function normalizePageInfo\(pageInfo = \{\}\) \{/);
	assert.match(src, /hasMore: Boolean\(safePageInfo\.hasMore\)/);
	assert.match(src, /nextCursor: safePageInfo\.nextCursor \?\? null/);
});

test("pagination-guard: sanitizeDashboardPageInfoTransition detects repeated cursor", () => {
	assert.match(
		src,
		/normalized\.nextCursor === currentCursor/,
	);
	assert.match(src, /same cursor twice/);
});

test("pagination-guard: getNextDashboardPaginationState throws when seenCursors has the cursor", () => {
	assert.match(src, /safeSeenCursors\.has\(normalized\.nextCursor\)/);
	assert.match(src, /repeated cursor/);
});

test("pagination-guard: getNextDashboardPaginationState throws when pageCount >= maxPages", () => {
	assert.match(src, /pageCount >= maxPages/);
	assert.match(src, /exceeded .* pages/);
});

// ── DASHBOARD_PAGINATION_MAX_PAGES ───────────────────────────────────────────

test("DASHBOARD_PAGINATION_MAX_PAGES is 100", () => {
	assert.equal(DASHBOARD_PAGINATION_MAX_PAGES, 100);
});

// ── sanitizeDashboardPageInfoTransition ──────────────────────────────────────

test("sanitizeDashboardPageInfoTransition: hasMore=false returns paginationError=null", () => {
	const result = sanitizeDashboardPageInfoTransition({
		receivedPageInfo: { hasMore: false, nextCursor: null },
	});
	assert.equal(result.hasMore, false);
	assert.equal(result.paginationError, null);
});

test("sanitizeDashboardPageInfoTransition: hasMore=true without cursor sets hasMore=false + error", () => {
	const result = sanitizeDashboardPageInfoTransition({
		receivedPageInfo: { hasMore: true, nextCursor: null },
		source: "cattle",
	});
	assert.equal(result.hasMore, false);
	assert.equal(result.nextCursor, null);
	assert.ok(result.paginationError !== null);
	assert.ok(result.paginationError.includes("cattle"));
});

test("sanitizeDashboardPageInfoTransition: valid hasMore=true with new cursor passes", () => {
	const result = sanitizeDashboardPageInfoTransition({
		currentPageInfo: { nextCursor: "cursor-A" },
		receivedPageInfo: { hasMore: true, nextCursor: "cursor-B" },
	});
	assert.equal(result.hasMore, true);
	assert.equal(result.nextCursor, "cursor-B");
	assert.equal(result.paginationError, null);
});

test("sanitizeDashboardPageInfoTransition: repeated cursor sets hasMore=false + error", () => {
	const result = sanitizeDashboardPageInfoTransition({
		currentPageInfo: { nextCursor: "cursor-A" },
		receivedPageInfo: { hasMore: true, nextCursor: "cursor-A" },
		source: "cattle",
	});
	assert.equal(result.hasMore, false);
	assert.equal(result.nextCursor, null);
	assert.ok(result.paginationError !== null);
	assert.ok(result.paginationError.includes("same cursor twice"));
});

test("sanitizeDashboardPageInfoTransition: null currentPageInfo allows first page cursor", () => {
	const result = sanitizeDashboardPageInfoTransition({
		currentPageInfo: null,
		receivedPageInfo: { hasMore: true, nextCursor: "cursor-1" },
	});
	assert.equal(result.hasMore, true);
	assert.equal(result.paginationError, null);
});

test("sanitizeDashboardPageInfoTransition: uses 'dashboard' as default source in error message", () => {
	const result = sanitizeDashboardPageInfoTransition({
		receivedPageInfo: { hasMore: true, nextCursor: null },
	});
	assert.ok(result.paginationError.includes("dashboard"));
});

test("sanitizeDashboardPageInfoTransition: non-object input treated as empty options", () => {
	const result = sanitizeDashboardPageInfoTransition(null);
	assert.equal(result.hasMore, false);
	assert.equal(result.paginationError, null);
});

test("sanitizeDashboardPageInfoTransition: coerces truthy hasMore via Boolean()", () => {
	// hasMore: 1 (truthy) should be treated as true
	const result = sanitizeDashboardPageInfoTransition({
		currentPageInfo: null,
		receivedPageInfo: { hasMore: 1, nextCursor: "cursor-x" },
	});
	assert.equal(result.hasMore, true);
	assert.equal(result.paginationError, null);
});

test("sanitizeDashboardPageInfoTransition: coerces falsy hasMore (0) via Boolean()", () => {
	const result = sanitizeDashboardPageInfoTransition({
		receivedPageInfo: { hasMore: 0, nextCursor: "cursor-y" },
	});
	assert.equal(result.hasMore, false);
	assert.equal(result.paginationError, null);
});

// ── getNextDashboardPaginationState ──────────────────────────────────────────

test("getNextDashboardPaginationState: returns normalized result when hasMore=false", () => {
	const result = getNextDashboardPaginationState({
		receivedPageInfo: { hasMore: false, nextCursor: null },
	});
	assert.equal(result.hasMore, false);
	assert.equal(result.paginationError, null);
});

test("getNextDashboardPaginationState: returns cursor when hasMore=true and cursor is new", () => {
	const seenCursors = new Set();
	const result = getNextDashboardPaginationState({
		currentCursor: null,
		receivedPageInfo: { hasMore: true, nextCursor: "cursor-1" },
		seenCursors,
		pageCount: 1,
		maxPages: 100,
	});
	assert.equal(result.hasMore, true);
	assert.equal(result.nextCursor, "cursor-1");
});

test("getNextDashboardPaginationState: throws when hasMore=true but no cursor", () => {
	assert.throws(() => {
		getNextDashboardPaginationState({
			receivedPageInfo: { hasMore: true, nextCursor: null },
			pageCount: 1,
		});
	}, /pagination returned hasMore without a next cursor/);
});

test("getNextDashboardPaginationState: throws when same cursor repeated in currentCursor", () => {
	assert.throws(() => {
		getNextDashboardPaginationState({
			currentCursor: "cursor-A",
			receivedPageInfo: { hasMore: true, nextCursor: "cursor-A" },
			pageCount: 1,
		});
	}, /same cursor twice/);
});

test("getNextDashboardPaginationState: throws when seenCursors contains the new cursor", () => {
	const seenCursors = new Set(["cursor-B"]);
	assert.throws(() => {
		getNextDashboardPaginationState({
			currentCursor: "cursor-A",
			receivedPageInfo: { hasMore: true, nextCursor: "cursor-B" },
			seenCursors,
			pageCount: 1,
		});
	}, /repeated cursor/);
});

test("getNextDashboardPaginationState: throws when pageCount >= maxPages", () => {
	assert.throws(() => {
		getNextDashboardPaginationState({
			receivedPageInfo: { hasMore: true, nextCursor: "cursor-new" },
			seenCursors: new Set(),
			pageCount: 100,
			maxPages: 100,
		});
	}, /exceeded 100 pages/);
});

test("getNextDashboardPaginationState: throws at pageCount=maxPages (exact boundary)", () => {
	assert.throws(() => {
		getNextDashboardPaginationState({
			receivedPageInfo: { hasMore: true, nextCursor: "cursor-new" },
			seenCursors: new Set(),
			pageCount: 50,
			maxPages: 50,
		});
	}, /exceeded/);
});

test("getNextDashboardPaginationState: allows pageCount < maxPages", () => {
	const result = getNextDashboardPaginationState({
		receivedPageInfo: { hasMore: true, nextCursor: "cursor-next" },
		seenCursors: new Set(),
		pageCount: 49,
		maxPages: 50,
	});
	assert.equal(result.hasMore, true);
});

test("getNextDashboardPaginationState: uses 'dashboard' default source in error message", () => {
	assert.throws(() => {
		getNextDashboardPaginationState({
			receivedPageInfo: { hasMore: true, nextCursor: null },
			pageCount: 1,
		});
	}, /dashboard pagination/);
});

test("getNextDashboardPaginationState: custom source appears in error message", () => {
	assert.throws(() => {
		getNextDashboardPaginationState({
			receivedPageInfo: { hasMore: true, nextCursor: null },
			source: "cattle-list",
			pageCount: 1,
		});
	}, /cattle-list pagination/);
});

test("getNextDashboardPaginationState: non-Set seenCursors falls back to new Set()", () => {
	// Should not throw for a new cursor even when seenCursors is invalid
	const result = getNextDashboardPaginationState({
		receivedPageInfo: { hasMore: true, nextCursor: "cursor-fresh" },
		seenCursors: null, // invalid, should be treated as empty Set
		pageCount: 1,
		maxPages: 100,
	});
	assert.equal(result.nextCursor, "cursor-fresh");
});
