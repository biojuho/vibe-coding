"use server";

import { requireAuthenticatedSession } from "@/lib/auth-guard";
import {
	getNotificationSummary,
	saveNotificationSummary,
} from "../dashboard/read-models";
import { buildNotifications } from "../notifications";
import { prisma } from "./_helpers";

// ============================================================
// Notification Actions
// ============================================================

function isFreshNotificationSummary(summary, now = Date.now()) {
	if (!summary?.payload || !summary.generatedAt) {
		return false;
	}

	const generatedAt = new Date(summary.generatedAt);
	const age = now - generatedAt.getTime();
	return Number.isFinite(age) && age >= 0 && age < 60 * 1000;
}

function isNotificationActionCattleRow(value) {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

function normalizeNotificationActionCattleRows(rows) {
	return Array.isArray(rows)
		? rows.filter((row) => isNotificationActionCattleRow(row))
		: [];
}

export async function getNotifications() {
	await requireAuthenticatedSession();
	try {
		// Try pre-computed read model first
		const cached = await getNotificationSummary("default");
		if (isFreshNotificationSummary(cached)) {
			return cached.payload;
		}
	} catch (err) {
		console.warn("notification: cache read failed, computing live", err);
	}

	try {
		const [cattleRows, inventoryRows] = await Promise.all([
			prisma.cattle.findMany({ where: { isArchived: false } }),
			prisma.inventoryItem.findMany(),
		]);
		const cattle = normalizeNotificationActionCattleRows(cattleRows);
		const inventory = Array.isArray(inventoryRows) ? inventoryRows : [];
		const notifications = buildNotifications(cattle, inventory);

		// Persist for future cache hits
		try {
			await saveNotificationSummary({
				farmId: "default",
				payload: notifications,
			});
		} catch (err) {
			console.warn("notification: cache write failed (non-fatal)", err);
		}

		return notifications;
	} catch (error) {
		console.warn("Degraded notifications fetch:", error);
		return [];
	}
}
