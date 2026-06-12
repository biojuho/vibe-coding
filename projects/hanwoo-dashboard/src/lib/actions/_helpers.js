import { revalidateTag } from "next/cache";
import { createOutboxEvent, DASHBOARD_EVENT_TOPICS } from "../dashboard/events";
import { invalidateDashboardCaches } from "../dashboard/read-models";
import prisma from "../db";

// ============================================================
// Shared Helpers — used across multiple action domains
// ============================================================

/**
 * Record a CattleHistory entry. Failures are logged but never
 * propagate to the caller so caller operations remain atomic.
 */
function serializeCattleHistoryMetadata(metadata) {
	if (!metadata) {
		return null;
	}

	try {
		return JSON.stringify(metadata);
	} catch (error) {
		console.error("Failed to serialize cattle history metadata:", error);
		return null;
	}
}

function normalizeCattleHistoryEventDate(value) {
	const date = value instanceof Date ? value : new Date(value);
	return Number.isNaN(date.getTime()) ? new Date() : date;
}

export async function recordCattleHistory(
	cattleId,
	eventType,
	eventDate,
	description,
	metadata = null,
	client = prisma,
) {
	const db = client ?? prisma;
	try {
		await db.cattleHistory.create({
			data: {
				cattleId,
				eventType,
				eventDate: normalizeCattleHistoryEventDate(eventDate),
				description,
				metadata: serializeCattleHistoryMetadata(metadata),
			},
		});
	} catch (error) {
		console.error("Failed to record cattle history:", error);
	}
}

/**
 * Invalidate dashboard read-model caches for the default farm.
 * Also invalidates Next.js framework-level "use cache" entries
 * via revalidateTag() so both cache layers stay consistent.
 */
function normalizeObject(value) {
	return value && typeof value === "object" && !Array.isArray(value)
		? value
		: {};
}

export async function invalidateHomeCaches(options = {}) {
	const safeOptions = normalizeObject(options);

	try {
		await invalidateDashboardCaches({
			farmId: "default",
			...safeOptions,
		});
	} catch (error) {
		console.error("Failed to invalidate dashboard caches:", error);
	}

	// Invalidate Next.js "use cache" tags based on mutation scope
	try {
		revalidateTag("dashboard-summary");

		if (safeOptions.cattleListPages) {
			revalidateTag("cattle-list");
		}

		if (safeOptions.salesListPages) {
			revalidateTag("sales-list");
		}
	} catch (error) {
		console.error("Failed to revalidate cache tags:", error);
	}
}

export { createOutboxEvent, DASHBOARD_EVENT_TOPICS, prisma };
