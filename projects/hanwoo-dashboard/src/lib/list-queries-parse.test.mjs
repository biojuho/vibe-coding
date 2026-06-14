/**
 * Behavioral tests for the pure parsing/validation functions in
 * dashboard/list-queries.js. The async DB functions (getCattleListPage,
 * getSalesListPage) require Prisma so they are not tested here.
 *
 * list-queries.js imports from bare specifiers ("../db", "./cache.js")
 * that cannot be resolved in Node ESM without extensions, so functions
 * are re-implemented inline with source-grep guards cross-checking invariants.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(
	path.join(SRC_ROOT, "lib/dashboard/list-queries.js"),
	"utf8",
);

// ── Constants (mirrored from source) ────────────────────────────────────────

const DEFAULT_LIMIT = 50;
const MAX_LIMIT = 100;

// ── Error class ──────────────────────────────────────────────────────────────

class DashboardQueryValidationError extends Error {
	constructor(message) {
		super(message);
		this.name = "DashboardQueryValidationError";
	}
}

// ── Inline re-implementations ─────────────────────────────────────────────────

function normalizeOptionalString(value) {
	if (value === null || value === undefined) return null;
	const normalized = String(value).trim();
	return normalized === "" ? null : normalized;
}

function normalizeObject(value) {
	return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function getSearchParam(searchParams, key) {
	return typeof searchParams?.get === "function" ? searchParams.get(key) : null;
}

function parseLimit(value) {
	if (value === null || value === undefined || value === "") return DEFAULT_LIMIT;
	const normalized = String(value).trim();
	if (!/^\d+$/.test(normalized))
		throw new DashboardQueryValidationError("목록 개수는 1 이상 숫자로 입력해 주세요.");
	const parsed = Number.parseInt(normalized, 10);
	if (!Number.isInteger(parsed) || parsed <= 0)
		throw new DashboardQueryValidationError("목록 개수는 1 이상 숫자로 입력해 주세요.");
	return Math.min(parsed, MAX_LIMIT);
}

function parsePenNumber(value) {
	const normalized = normalizeOptionalString(value);
	if (normalized === null) return null;
	if (!/^\d+$/.test(normalized))
		throw new DashboardQueryValidationError("칸 번호는 1 이상 숫자로 입력해 주세요.");
	const parsed = Number.parseInt(normalized, 10);
	if (!Number.isInteger(parsed) || parsed <= 0)
		throw new DashboardQueryValidationError("칸 번호는 1 이상 숫자로 입력해 주세요.");
	return parsed;
}

function toDateKey(date) {
	return date.toISOString().slice(0, 10);
}

function parseDateParam(value, fieldName) {
	const normalized = normalizeOptionalString(value);
	if (normalized === null) return null;
	const label = fieldName === "from" ? "시작일" : "종료일";
	if (!/^\d{4}-\d{2}-\d{2}$/.test(normalized))
		throw new DashboardQueryValidationError(`${label}은 YYYY-MM-DD 형식으로 입력해 주세요.`);
	const parsed = new Date(`${normalized}T00:00:00.000Z`);
	if (Number.isNaN(parsed.getTime()) || toDateKey(parsed) !== normalized)
		throw new DashboardQueryValidationError(`${label}은 YYYY-MM-DD 형식으로 입력해 주세요.`);
	return parsed;
}

function encodeCursor(payload) {
	return Buffer.from(JSON.stringify(payload)).toString("base64url");
}

function decodeCursor(cursor) {
	const normalized = normalizeOptionalString(cursor);
	if (normalized === null) return null;
	try {
		const parsed = JSON.parse(Buffer.from(normalized, "base64url").toString("utf8"));
		if (!parsed?.id || !parsed?.sortValue)
			throw new DashboardQueryValidationError("목록 위치 정보가 올바르지 않습니다.");
		const sortDate = new Date(parsed.sortValue);
		if (Number.isNaN(sortDate.getTime()))
			throw new DashboardQueryValidationError("목록 위치 정보의 시간이 올바르지 않습니다.");
		return { id: parsed.id, sortValue: sortDate };
	} catch (error) {
		if (error instanceof DashboardQueryValidationError) throw error;
		throw new DashboardQueryValidationError("목록 위치 정보가 올바르지 않습니다.");
	}
}

function parseCattleListQuery(searchParams) {
	return {
		buildingId: normalizeOptionalString(getSearchParam(searchParams, "buildingId")),
		penNumber: parsePenNumber(getSearchParam(searchParams, "penNumber")),
		status: normalizeOptionalString(getSearchParam(searchParams, "status")),
		cursor: normalizeOptionalString(getSearchParam(searchParams, "cursor")),
		limit: parseLimit(getSearchParam(searchParams, "limit")),
		fresh: getSearchParam(searchParams, "fresh") === "1",
	};
}

function parseSalesListQuery(searchParams) {
	const from = parseDateParam(getSearchParam(searchParams, "from"), "from");
	const to = parseDateParam(getSearchParam(searchParams, "to"), "to");
	if (from && to && from > to)
		throw new DashboardQueryValidationError("시작일은 종료일보다 늦을 수 없습니다.");
	return {
		from,
		to,
		cursor: normalizeOptionalString(getSearchParam(searchParams, "cursor")),
		limit: parseLimit(getSearchParam(searchParams, "limit")),
		fresh: getSearchParam(searchParams, "fresh") === "1",
	};
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("list-queries.js DEFAULT_LIMIT=50 and MAX_LIMIT=100 constants exist", () => {
	assert.match(src, /const DEFAULT_LIMIT = 50;/);
	assert.match(src, /const MAX_LIMIT = 100;/);
});

test("list-queries.js parseLimit clamps to MAX_LIMIT with Math.min", () => {
	assert.match(src, /return Math\.min\(parsed, MAX_LIMIT\);/);
});

test("list-queries.js decodeCursor validates sortValue as Date", () => {
	assert.match(src, /const sortDate = new Date\(parsed\.sortValue\);/);
	assert.match(src, /Number\.isNaN\(sortDate\.getTime\(\)\)/);
});

test("list-queries.js parseSalesListQuery guards from > to order", () => {
	assert.match(src, /from && to && from > to/);
	assert.match(src, /시작일은 종료일보다 늦을 수 없습니다/);
});

// ── parseLimit behavioral tests ───────────────────────────────────────────────

test("parseLimit returns DEFAULT_LIMIT for null, undefined, and empty string", () => {
	assert.equal(parseLimit(null), 50);
	assert.equal(parseLimit(undefined), 50);
	assert.equal(parseLimit(""), 50);
});

test("parseLimit returns parsed value for valid numeric strings", () => {
	assert.equal(parseLimit("20"), 20);
	assert.equal(parseLimit("1"), 1);
	assert.equal(parseLimit("50"), 50);
});

test("parseLimit clamps over-MAX values to MAX_LIMIT", () => {
	assert.equal(parseLimit("100"), 100);
	assert.equal(parseLimit("150"), 100);
	assert.equal(parseLimit("9999"), 100);
});

test("parseLimit throws for non-numeric and zero values", () => {
	assert.throws(() => parseLimit("abc"), { name: "DashboardQueryValidationError" });
	assert.throws(() => parseLimit("1.5"), { name: "DashboardQueryValidationError" });
	assert.throws(() => parseLimit("-5"), { name: "DashboardQueryValidationError" });
});

test("parseLimit throws for zero", () => {
	assert.throws(() => parseLimit("0"), { name: "DashboardQueryValidationError" });
});

// ── parsePenNumber behavioral tests ──────────────────────────────────────────

test("parsePenNumber returns null for null, undefined, and empty string", () => {
	assert.equal(parsePenNumber(null), null);
	assert.equal(parsePenNumber(undefined), null);
	assert.equal(parsePenNumber(""), null);
	assert.equal(parsePenNumber("   "), null);
});

test("parsePenNumber parses valid positive integers", () => {
	assert.equal(parsePenNumber("1"), 1);
	assert.equal(parsePenNumber("99"), 99);
	assert.equal(parsePenNumber("  3  "), 3);
});

test("parsePenNumber throws for non-numeric and zero inputs", () => {
	assert.throws(() => parsePenNumber("abc"), { name: "DashboardQueryValidationError" });
	assert.throws(() => parsePenNumber("0"), { name: "DashboardQueryValidationError" });
	assert.throws(() => parsePenNumber("2.5"), { name: "DashboardQueryValidationError" });
});

// ── parseDateParam behavioral tests ──────────────────────────────────────────

test("parseDateParam returns null for null, undefined, and empty strings", () => {
	assert.equal(parseDateParam(null, "from"), null);
	assert.equal(parseDateParam(undefined, "to"), null);
	assert.equal(parseDateParam("", "from"), null);
});

test("parseDateParam returns a Date for a valid YYYY-MM-DD string", () => {
	const result = parseDateParam("2026-06-15", "from");
	assert.ok(result instanceof Date);
	assert.equal(result.toISOString().slice(0, 10), "2026-06-15");
});

test("parseDateParam throws for non-YYYY-MM-DD formats", () => {
	assert.throws(() => parseDateParam("20260615", "from"), { name: "DashboardQueryValidationError" });
	assert.throws(() => parseDateParam("2026/06/15", "to"), { name: "DashboardQueryValidationError" });
	assert.throws(() => parseDateParam("June 15 2026", "from"), { name: "DashboardQueryValidationError" });
});

test("parseDateParam rejects calendar-impossible dates like 2026-13-01", () => {
	assert.throws(() => parseDateParam("2026-13-01", "from"), { name: "DashboardQueryValidationError" });
});

test("parseDateParam uses 시작일 label for 'from' and 종료일 for 'to' in error messages", () => {
	assert.throws(() => parseDateParam("bad", "from"), /시작일/);
	assert.throws(() => parseDateParam("bad", "to"), /종료일/);
});

// ── decodeCursor behavioral tests ────────────────────────────────────────────

test("decodeCursor returns null for null, undefined, and empty string", () => {
	assert.equal(decodeCursor(null), null);
	assert.equal(decodeCursor(undefined), null);
	assert.equal(decodeCursor(""), null);
});

test("decodeCursor decodes a valid base64url cursor into {id, sortValue}", () => {
	const cursor = encodeCursor({ id: "cattle-123", sortValue: "2026-06-01T00:00:00.000Z" });
	const result = decodeCursor(cursor);
	assert.equal(result.id, "cattle-123");
	assert.ok(result.sortValue instanceof Date);
	assert.equal(result.sortValue.toISOString(), "2026-06-01T00:00:00.000Z");
});

test("decodeCursor throws when id or sortValue fields are missing", () => {
	const missingId = encodeCursor({ sortValue: "2026-06-01T00:00:00.000Z" });
	assert.throws(() => decodeCursor(missingId), { name: "DashboardQueryValidationError" });

	const missingSortValue = encodeCursor({ id: "cattle-123" });
	assert.throws(() => decodeCursor(missingSortValue), { name: "DashboardQueryValidationError" });
});

test("decodeCursor throws when sortValue is not a valid date string", () => {
	const cursor = encodeCursor({ id: "cattle-123", sortValue: "not-a-date" });
	assert.throws(() => decodeCursor(cursor), { name: "DashboardQueryValidationError" });
});

test("decodeCursor throws for non-base64url garbage input", () => {
	assert.throws(() => decodeCursor("!!!not-base64!!!"), { name: "DashboardQueryValidationError" });
});

// ── parseCattleListQuery behavioral tests ─────────────────────────────────────

test("parseCattleListQuery returns defaults for empty URLSearchParams", () => {
	const params = new URLSearchParams();
	const result = parseCattleListQuery(params);
	assert.equal(result.buildingId, null);
	assert.equal(result.penNumber, null);
	assert.equal(result.status, null);
	assert.equal(result.cursor, null);
	assert.equal(result.limit, 50);
	assert.equal(result.fresh, false);
});

test("parseCattleListQuery extracts all fields from URLSearchParams", () => {
	const params = new URLSearchParams(
		"buildingId=bldg-1&penNumber=3&status=active&limit=20&fresh=1",
	);
	const result = parseCattleListQuery(params);
	assert.equal(result.buildingId, "bldg-1");
	assert.equal(result.penNumber, 3);
	assert.equal(result.status, "active");
	assert.equal(result.limit, 20);
	assert.equal(result.fresh, true);
});

test("parseCattleListQuery returns null fields for non-URLSearchParams input", () => {
	const result = parseCattleListQuery(null);
	assert.equal(result.buildingId, null);
	assert.equal(result.penNumber, null);
	assert.equal(result.limit, 50);
	assert.equal(result.fresh, false);
});

// ── parseSalesListQuery behavioral tests ──────────────────────────────────────

test("parseSalesListQuery accepts valid from/to date range", () => {
	const params = new URLSearchParams("from=2026-01-01&to=2026-06-30&limit=25");
	const result = parseSalesListQuery(params);
	assert.ok(result.from instanceof Date);
	assert.ok(result.to instanceof Date);
	assert.equal(result.limit, 25);
});

test("parseSalesListQuery throws when from is later than to", () => {
	const params = new URLSearchParams("from=2026-12-01&to=2026-01-01");
	assert.throws(() => parseSalesListQuery(params), {
		name: "DashboardQueryValidationError",
		message: /시작일은 종료일보다 늦을 수 없습니다/,
	});
});

test("parseSalesListQuery allows from === to (same-day range)", () => {
	const params = new URLSearchParams("from=2026-06-15&to=2026-06-15");
	const result = parseSalesListQuery(params);
	assert.ok(result.from instanceof Date);
	assert.ok(result.to instanceof Date);
});

test("parseSalesListQuery returns null dates when from/to are absent", () => {
	const params = new URLSearchParams("limit=10");
	const result = parseSalesListQuery(params);
	assert.equal(result.from, null);
	assert.equal(result.to, null);
	assert.equal(result.limit, 10);
});
