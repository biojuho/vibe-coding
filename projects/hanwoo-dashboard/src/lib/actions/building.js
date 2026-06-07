"use server";

import { requireAuthenticatedSession } from "@/lib/auth-guard";
import { validateBuildingInput } from "../action-validation.mjs";
import { prisma } from "./_helpers";

// ============================================================
// Building Actions
// ============================================================

function isBuildingActionRow(value) {
	return (
		value !== null &&
		typeof value === "object" &&
		!Array.isArray(value)
	);
}

function normalizeBuildingActionRows(rows) {
	return Array.isArray(rows)
		? rows.filter((row) => isBuildingActionRow(row))
		: [];
}

export async function getBuildings() {
	await requireAuthenticatedSession();
	try {
		return normalizeBuildingActionRows(
			await prisma.building.findMany({ orderBy: { name: "asc" } }),
		);
	} catch (e) {
		console.warn("Degraded buildings fetch:", e);
		return [];
	}
}

export async function createBuilding(data) {
	await requireAuthenticatedSession();
	try {
		const validation = validateBuildingInput(data);
		if (!validation.success) {
			return validation;
		}

		const payload = validation.data;
		const created = await prisma.building.create({
			data: { name: payload.name, penCount: payload.penCount },
		});
		return { success: true, data: created };
	} catch (e) {
		console.error("Failed to create building:", e);
		return { success: false, message: "축사 정보를 추가하지 못했습니다." };
	}
}

export async function deleteBuilding(id) {
	await requireAuthenticatedSession();
	try {
		const cattleCount = await prisma.cattle.count({
			where: { buildingId: id, isArchived: false },
		});
		if (cattleCount > 0) {
			return {
				success: false,
				message: `이 축사에 ${cattleCount}두의 개체가 있어 삭제할 수 없습니다. 먼저 개체를 이동해 주세요.`,
			};
		}
		await prisma.building.delete({ where: { id } });
		return { success: true, data: { id } };
	} catch (e) {
		console.error("Failed to delete building:", e);
		return { success: false, message: "축사를 삭제하지 못했습니다." };
	}
}
