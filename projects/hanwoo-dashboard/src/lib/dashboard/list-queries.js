import prisma from "../db";
import {
	buildCattleListKey,
	buildSalesListKey,
	DASHBOARD_CACHE_TTLS,
	getCachedJson,
	setCachedJson,
} from "./cache.js";

const DEFAULT_LIMIT = 50;
const MAX_LIMIT = 100;

export class DashboardQueryValidationError extends Error {
	constructor(message) {
		super(message);
		this.name = "DashboardQueryValidationError";
	}
}

function normalizeOptionalString(value) {
	if (value === null || value === undefined) {
		return null;
	}

	const normalized = String(value).trim();
	return normalized === "" ? null : normalized;
}

function normalizeObject(value) {
	return value && typeof value === "object" ? value : {};
}

function getSearchParam(searchParams, key) {
	return typeof searchParams?.get === "function" ? searchParams.get(key) : null;
}

function parseLimit(value) {
	if (value === null || value === undefined || value === "") {
		return DEFAULT_LIMIT;
	}

	const normalized = String(value).trim();
	if (!/^\d+$/.test(normalized)) {
		throw new DashboardQueryValidationError(
			"목록 개수는 1 이상 숫자로 입력해 주세요.",
		);
	}

	const parsed = Number.parseInt(normalized, 10);
	if (!Number.isInteger(parsed) || parsed <= 0) {
		throw new DashboardQueryValidationError(
			"목록 개수는 1 이상 숫자로 입력해 주세요.",
		);
	}

	return Math.min(parsed, MAX_LIMIT);
}

function parsePenNumber(value) {
	const normalized = normalizeOptionalString(value);
	if (normalized === null) {
		return null;
	}

	if (!/^\d+$/.test(normalized)) {
		throw new DashboardQueryValidationError(
			"칸 번호는 1 이상 숫자로 입력해 주세요.",
		);
	}

	const parsed = Number.parseInt(normalized, 10);
	if (!Number.isInteger(parsed) || parsed <= 0) {
		throw new DashboardQueryValidationError(
			"칸 번호는 1 이상 숫자로 입력해 주세요.",
		);
	}

	return parsed;
}

function parseDateParam(value, fieldName) {
	const normalized = normalizeOptionalString(value);
	if (normalized === null) {
		return null;
	}

	const label = fieldName === "from" ? "시작일" : "종료일";
	if (!/^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
		throw new DashboardQueryValidationError(
			`${label}은 YYYY-MM-DD 형식으로 입력해 주세요.`,
		);
	}

	const parsed = new Date(`${normalized}T00:00:00.000Z`);
	if (Number.isNaN(parsed.getTime()) || toDateKey(parsed) !== normalized) {
		throw new DashboardQueryValidationError(
			`${label}은 YYYY-MM-DD 형식으로 입력해 주세요.`,
		);
	}

	return parsed;
}

function toDateKey(date) {
	return date.toISOString().slice(0, 10);
}

function endOfDay(date) {
	const value = new Date(date);
	value.setUTCHours(23, 59, 59, 999);
	return value;
}

function encodeCursor(payload) {
	return Buffer.from(JSON.stringify(payload)).toString("base64url");
}

function decodeCursor(cursor) {
	const normalized = normalizeOptionalString(cursor);
	if (normalized === null) {
		return null;
	}

	try {
		const parsed = JSON.parse(
			Buffer.from(normalized, "base64url").toString("utf8"),
		);
		if (!parsed?.id || !parsed?.sortValue) {
			throw new DashboardQueryValidationError(
				"목록 위치 정보가 올바르지 않습니다.",
			);
		}

		const sortDate = new Date(parsed.sortValue);
		if (Number.isNaN(sortDate.getTime())) {
			throw new DashboardQueryValidationError(
				"목록 위치 정보의 시간이 올바르지 않습니다.",
			);
		}

		return {
			id: parsed.id,
			sortValue: sortDate,
		};
	} catch (error) {
		if (error instanceof DashboardQueryValidationError) {
			throw error;
		}

		throw new DashboardQueryValidationError(
			"목록 위치 정보가 올바르지 않습니다.",
		);
	}
}

function buildDescendingCursorWhere(fieldName, cursor) {
	if (!cursor) {
		return undefined;
	}

	return {
		OR: [
			{
				[fieldName]: {
					lt: cursor.sortValue,
				},
			},
			{
				AND: [
					{
						[fieldName]: cursor.sortValue,
					},
					{
						id: {
							lt: cursor.id,
						},
					},
				],
			},
		],
	};
}

function toCursorSortValue(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function buildPageInfo(items, hasMore, limit, sortField) {
	if (!hasMore || items.length === 0) {
		return {
			hasMore: false,
			nextCursor: null,
			limit,
			returnedCount: items.length,
		};
	}

	const lastItem = items[items.length - 1];
	const sortValue = toCursorSortValue(lastItem[sortField]);
	if (!sortValue) {
		return {
			hasMore: false,
			nextCursor: null,
			limit,
			returnedCount: items.length,
		};
	}

	return {
		hasMore: true,
		nextCursor: encodeCursor({
			id: lastItem.id,
			sortValue,
		}),
		limit,
		returnedCount: items.length,
	};
}

export function parseCattleListQuery(searchParams) {
	return {
		buildingId: normalizeOptionalString(getSearchParam(searchParams, "buildingId")),
		penNumber: parsePenNumber(getSearchParam(searchParams, "penNumber")),
		status: normalizeOptionalString(getSearchParam(searchParams, "status")),
		cursor: normalizeOptionalString(getSearchParam(searchParams, "cursor")),
		limit: parseLimit(getSearchParam(searchParams, "limit")),
		fresh: getSearchParam(searchParams, "fresh") === "1",
	};
}

export function parseSalesListQuery(searchParams) {
	const from = parseDateParam(getSearchParam(searchParams, "from"), "from");
	const to = parseDateParam(getSearchParam(searchParams, "to"), "to");

	if (from && to && from > to) {
		throw new DashboardQueryValidationError(
			"시작일은 종료일보다 늦을 수 없습니다.",
		);
	}

	return {
		from,
		to,
		cursor: normalizeOptionalString(getSearchParam(searchParams, "cursor")),
		limit: parseLimit(getSearchParam(searchParams, "limit")),
		fresh: getSearchParam(searchParams, "fresh") === "1",
	};
}

export async function getCattleListPage(input = {}) {
	const {
		farmId = "default",
		buildingId = null,
		penNumber = null,
		status = null,
		cursor = null,
		limit = DEFAULT_LIMIT,
		bypassCache = false,
	} = normalizeObject(input);

	const cacheKey = buildCattleListKey({
		farmId,
		buildingId,
		penNumber,
		status,
		cursor,
		limit,
	});

	if (!bypassCache) {
		const cached = await getCachedJson(cacheKey);
		if (cached) {
			return {
				...cached,
				meta: {
					...(cached.meta ?? {}),
					source: "cache",
				},
			};
		}
	}

	const decodedCursor = decodeCursor(cursor);
	const cursorWhere = buildDescendingCursorWhere("updatedAt", decodedCursor);
	const records = await prisma.cattle.findMany({
		where: {
			isArchived: false,
			...(buildingId ? { buildingId } : {}),
			...(penNumber ? { penNumber } : {}),
			...(status ? { status } : {}),
			...(cursorWhere ?? {}),
		},
		select: {
			id: true,
			tagNumber: true,
			name: true,
			birthDate: true,
			gender: true,
			status: true,
			weight: true,
			buildingId: true,
			penNumber: true,
			memo: true,
			geneticFather: true,
			geneticMother: true,
			geneticGrade: true,
			weightHistory: true,
			lastEstrus: true,
			pregnancyDate: true,
			purchasePrice: true,
			purchaseDate: true,
			createdAt: true,
			updatedAt: true,
			building: {
				select: {
					id: true,
					name: true,
				},
			},
		},
		orderBy: [{ updatedAt: "desc" }, { id: "desc" }],
		take: limit + 1,
	});

	const hasMore = records.length > limit;
	const items = hasMore ? records.slice(0, limit) : records;
	const response = {
		items,
		filters: {
			buildingId,
			penNumber,
			status,
		},
		pageInfo: buildPageInfo(items, hasMore, limit, "updatedAt"),
		meta: {
			source: "db",
			fetchedAt: new Date().toISOString(),
		},
	};

	await setCachedJson(cacheKey, response, DASHBOARD_CACHE_TTLS.cattleList);
	return response;
}

export async function getSalesListPage(input = {}) {
	const {
		farmId = "default",
		from = null,
		to = null,
		cursor = null,
		limit = DEFAULT_LIMIT,
		bypassCache = false,
	} = normalizeObject(input);

	const fromKey = from ? toDateKey(from) : null;
	const toKey = to ? toDateKey(to) : null;
	const cacheKey = buildSalesListKey({
		farmId,
		from: fromKey,
		to: toKey,
		cursor,
		limit,
	});

	if (!bypassCache) {
		const cached = await getCachedJson(cacheKey);
		if (cached) {
			return {
				...cached,
				meta: {
					...(cached.meta ?? {}),
					source: "cache",
				},
			};
		}
	}

	const decodedCursor = decodeCursor(cursor);
	const cursorWhere = buildDescendingCursorWhere("saleDate", decodedCursor);
	const saleDateWhere = {};

	if (from) {
		saleDateWhere.gte = from;
	}

	if (to) {
		saleDateWhere.lte = endOfDay(to);
	}

	const records = await prisma.salesRecord.findMany({
		where: {
			...(Object.keys(saleDateWhere).length > 0
				? { saleDate: saleDateWhere }
				: {}),
			...(cursorWhere ?? {}),
		},
		select: {
			id: true,
			saleDate: true,
			price: true,
			purchaser: true,
			grade: true,
			cattleId: true,
			createdAt: true,
			updatedAt: true,
			cattle: {
				select: {
					id: true,
					name: true,
					tagNumber: true,
					purchasePrice: true,
				},
			},
		},
		orderBy: [{ saleDate: "desc" }, { id: "desc" }],
		take: limit + 1,
	});

	const hasMore = records.length > limit;
	const items = hasMore ? records.slice(0, limit) : records;
	const response = {
		items,
		filters: {
			from: fromKey,
			to: toKey,
		},
		pageInfo: buildPageInfo(items, hasMore, limit, "saleDate"),
		meta: {
			source: "db",
			fetchedAt: new Date().toISOString(),
		},
	};

	await setCachedJson(cacheKey, response, DASHBOARD_CACHE_TTLS.salesList);
	return response;
}
