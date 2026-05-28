"use server";

import { revalidatePath } from "next/cache";
import { requireAuthenticatedSession } from "@/lib/auth-guard";
import { toFiniteNumber } from "@/lib/utils";
import { validateExpenseRecordInput } from "../action-validation.mjs";
import {
	createOutboxEvent,
	DASHBOARD_EVENT_TOPICS,
	invalidateHomeCaches,
	prisma,
} from "./_helpers";

// ============================================================
// Expense Actions
// ============================================================

function isPlainObject(value) {
	return (
		value !== null &&
		typeof value === "object" &&
		!Array.isArray(value)
	);
}

function parseOptionalDateFilter(value) {
	if (!value) {
		return null;
	}

	if (value instanceof Date) {
		return Number.isNaN(value.getTime()) ? null : value;
	}

	if (typeof value === "string") {
		const normalized = value.trim();
		if (!/^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
			return null;
		}

		const parsed = new Date(`${normalized}T00:00:00.000Z`);
		return Number.isNaN(parsed.getTime()) ||
			parsed.toISOString().slice(0, 10) !== normalized
			? null
			: parsed;
	}

	return null;
}

function normalizeExpenseRows(expenses) {
	return Array.isArray(expenses)
		? expenses.filter((expense) => isPlainObject(expense))
		: [];
}

function normalizeExpenseCategory(value) {
	return typeof value === "string" && value.trim() ? value.trim() : "Other";
}

export async function getExpenseRecords(filters = {}) {
	await requireAuthenticatedSession();
	try {
		const safeFilters = isPlainObject(filters) ? filters : {};
		const where = {};
		if (safeFilters.cattleId) where.cattleId = safeFilters.cattleId;
		if (safeFilters.buildingId) where.buildingId = safeFilters.buildingId;
		if (safeFilters.category) where.category = safeFilters.category;
		const fromDate = parseOptionalDateFilter(safeFilters.fromDate);
		const toDate = parseOptionalDateFilter(safeFilters.toDate);
		if (fromDate || toDate) {
			where.date = {};
			if (fromDate) where.date.gte = fromDate;
			if (toDate) where.date.lte = toDate;
		}

		return normalizeExpenseRows(
			await prisma.expenseRecord.findMany({
				where,
				orderBy: { date: "desc" },
			}),
		);
	} catch (error) {
		console.error("Failed to fetch expenses:", error);
		return [];
	}
}

export async function createExpenseRecord(data) {
	await requireAuthenticatedSession();
	try {
		const validation = validateExpenseRecordInput(data);
		if (!validation.success) {
			return validation;
		}

		const payload = validation.data;
		if (!data.date || !data.category || !data.amount) {
			return { success: false, message: "날짜, 카테고리, 금액은 필수입니다." };
		}
		if (payload.cattleId) {
			const cattle = await prisma.cattle.findUnique({
				where: { id: payload.cattleId },
			});
			if (!cattle)
				return { success: false, message: "존재하지 않는 개체입니다." };
		}
		if (payload.buildingId) {
			const building = await prisma.building.findUnique({
				where: { id: payload.buildingId },
			});
			if (!building)
				return { success: false, message: "존재하지 않는 축사입니다." };
		}

		const created = await prisma.expenseRecord.create({
			data: {
				date: payload.date,
				cattleId: payload.cattleId,
				buildingId: payload.buildingId,
				category: payload.category,
				amount: payload.amount,
				description: payload.description,
			},
		});
		await createOutboxEvent({
			topic: DASHBOARD_EVENT_TOPICS.expenseRecorded,
			aggregateId: payload.cattleId || payload.buildingId || null,
			payload: { category: payload.category, amount: payload.amount },
		});
		await invalidateHomeCaches({ summary: true });
		revalidatePath("/");
		return { success: true, data: created };
	} catch (error) {
		console.error("Failed to create expense:", error);
		return { success: false, message: "비용 기록을 등록하지 못했습니다." };
	}
}

export async function getExpenseAggregation() {
	await requireAuthenticatedSession();
	try {
		const expenses = normalizeExpenseRows(await prisma.expenseRecord.findMany());
		const byCategory = {};
		expenses.forEach((expense) => {
			const category = normalizeExpenseCategory(expense.category);
			byCategory[category] =
				(byCategory[category] || 0) + toFiniteNumber(expense.amount);
		});
		return byCategory;
	} catch (error) {
		console.error("Failed to aggregate expenses:", error);
		return {};
	}
}
