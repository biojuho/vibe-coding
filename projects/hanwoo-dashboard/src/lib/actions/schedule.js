"use server";

import { requireAuthenticatedSession } from "@/lib/auth-guard";
import { validateScheduleEventInput } from "../action-validation.mjs";
import { prisma } from "./_helpers";

// ============================================================
// Schedule Actions
// ============================================================

function isScheduleActionRow(value) {
	return (
		value !== null &&
		typeof value === "object" &&
		!Array.isArray(value)
	);
}

function normalizeScheduleActionRows(rows) {
	return Array.isArray(rows)
		? rows.filter((row) => isScheduleActionRow(row))
		: [];
}

export async function getScheduleEvents() {
	await requireAuthenticatedSession();
	try {
		return normalizeScheduleActionRows(
			await prisma.scheduleEvent.findMany({ orderBy: { date: "asc" } }),
		);
	} catch (e) {
		console.warn("Degraded schedule fetch:", e);
		return [];
	}
}

export async function createScheduleEvent(data) {
	await requireAuthenticatedSession();
	try {
		const validation = validateScheduleEventInput(data);
		if (!validation.success) {
			return validation;
		}

		const payload = validation.data;
		const created = await prisma.scheduleEvent.create({
			data: {
				title: payload.title,
				date: payload.date,
				type: payload.type,
				cattleId: payload.cattleId,
			},
		});
		return { success: true, data: created };
	} catch (e) {
		console.error("Failed to create schedule event:", e);
		return { success: false, message: "일정을 등록하지 못했습니다." };
	}
}

export async function toggleEventCompletion(id, isCompleted) {
	await requireAuthenticatedSession();
	if (typeof isCompleted !== "boolean") {
		return { success: false, message: "일정 상태를 변경하지 못했습니다." };
	}

	const normalizedId = typeof id === "string" ? id.trim() : "";
	if (!normalizedId) {
		return { success: false, message: "일정 상태를 변경하지 못했습니다." };
	}

	try {
		const updated = await prisma.scheduleEvent.update({
			where: { id: normalizedId },
			data: { isCompleted },
		});
		return { success: true, data: updated };
	} catch (e) {
		console.error("Failed to update schedule event:", e);
		return { success: false, message: "일정 상태를 변경하지 못했습니다." };
	}
}
