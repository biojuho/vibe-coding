"use server";

import { requireAdminSession, requireAuthenticatedSession } from "@/lib/auth-guard";
import { getProfitabilityEstimates } from "../dashboard/profitability-service";
import { prisma } from "./_helpers";

const DIAGNOSTICS_ERROR_MESSAGE = "진단 정보를 불러오지 못했습니다.";
const RAW_DATA_ERROR_MESSAGE = "원본 데이터를 불러오지 못했습니다.";
const UNSUPPORTED_DATA_TYPE_MESSAGE = "지원하지 않는 데이터 유형입니다.";

// ============================================================
// System Diagnostics & Utilities
// ============================================================

function isRawDataActionRow(value) {
	return (
		value !== null &&
		typeof value === "object" &&
		!Array.isArray(value)
	);
}

function normalizeRawDataActionRows(rows) {
	return Array.isArray(rows)
		? rows.filter((row) => isRawDataActionRow(row))
		: [];
}

export async function getSystemDiagnostics() {
	await requireAdminSession();
	try {
		const start = Date.now();
		const cattleCount = await prisma.cattle.count();
		const latency = Date.now() - start;
		return {
			success: true,
			timestamp: new Date().toISOString(),
			uptime: process.uptime(),
			memory: process.memoryUsage(),
			nodeVersion: process.version,
			database: {
				status: "정상",
				latency: `${latency}ms`,
				recordCounts: {
					cattle: cattleCount,
					sales: await prisma.salesRecord.count(),
					feed: await prisma.feedRecord.count(),
					expenses: await prisma.expenseRecord.count(),
					histories: await prisma.cattleHistory.count(),
				},
			},
		};
	} catch (error) {
		console.error("System diagnostics action failed:", error);
		return {
			success: false,
			timestamp: new Date().toISOString(),
			error: DIAGNOSTICS_ERROR_MESSAGE,
			database: { status: "연결 실패", latency: "DB 응답 시간 확인 불가" },
		};
	}
}

export async function getRawData(modelName) {
	await requireAdminSession();
	try {
		const allowedModels = [
			"cattle",
			"salesRecord",
			"feedRecord",
			"scheduleEvent",
			"inventoryItem",
			"building",
			"farmSettings",
			"expenseRecord",
			"cattleHistory",
		];
		if (!allowedModels.includes(modelName)) {
			throw new Error(UNSUPPORTED_DATA_TYPE_MESSAGE);
		}
		const data = await prisma[modelName].findMany({
			take: 50,
			orderBy: { createdAt: "desc" },
		});
		return { success: true, data: normalizeRawDataActionRows(data) };
	} catch (error) {
		if (error.message === UNSUPPORTED_DATA_TYPE_MESSAGE) {
			return { success: false, message: UNSUPPORTED_DATA_TYPE_MESSAGE };
		}

		console.error("Raw diagnostics data action failed:", error);
		return { success: false, message: RAW_DATA_ERROR_MESSAGE };
	}
}

export async function lookupCattleTag(tagNumber) {
	await requireAuthenticatedSession();
	const { lookupCattleByTag } = await import("../mtrace");
	return lookupCattleByTag(tagNumber);
}

// ============================================================
// Profitability Actions
// ============================================================

export async function getProfitabilityData() {
	await requireAuthenticatedSession();
	return await getProfitabilityEstimates();
}

// ============================================================
// Account Deletion
// ============================================================

const DELETE_ACCOUNT_ERROR_MESSAGE = "계정 삭제 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";

export async function deleteAccount() {
	const session = await requireAuthenticatedSession();
	const userId = session.user?.id;
	if (!userId) {
		return { ok: false, error: "세션 정보를 확인할 수 없습니다." };
	}
	try {
		// Anonymize subscription records so payment audit trail is preserved
		await prisma.subscription.updateMany({
			where: { userId },
			data: { userId: null },
		});
		await prisma.user.delete({ where: { id: userId } });
		return { ok: true };
	} catch (error) {
		console.error("deleteAccount failed:", error);
		return { ok: false, error: DELETE_ACCOUNT_ERROR_MESSAGE };
	}
}
