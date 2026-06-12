"use server";

import { requireAuthenticatedSession } from "@/lib/auth-guard";
import {
	validateCalvingRecordInput,
	validateCattleMutationInput,
} from "../action-validation.mjs";
import { normalizeCattleHistoryRows } from "../cattle-history.mjs";
import {
	createOutboxEvent,
	DASHBOARD_EVENT_TOPICS,
	invalidateHomeCaches,
	prisma,
	recordCattleHistory,
} from "./_helpers";

// ============================================================
// Cattle Actions
// ============================================================

const CATTLE_TAG_DUPLICATE_MESSAGE =
	"이미 등록된 이력번호입니다. 다른 이력번호를 입력해 주세요.";

function isCattleTagDuplicateError(error) {
	if (error?.code !== "P2002") {
		return false;
	}

	const target = error?.meta?.target;
	if (Array.isArray(target)) {
		return target.includes("tagNumber");
	}

	return typeof target === "string" && target.includes("tagNumber");
}

function isCattleActionRow(value) {
	return (
		value !== null &&
		typeof value === "object" &&
		!Array.isArray(value)
	);
}

function normalizeCattleActionRows(rows) {
	return Array.isArray(rows)
		? rows.filter((row) => isCattleActionRow(row))
		: [];
}

export async function getCattleList() {
	await requireAuthenticatedSession();
	try {
		const cattle = normalizeCattleActionRows(
			await prisma.cattle.findMany({
				where: { isArchived: false },
				orderBy: { updatedAt: "desc" },
			}),
		);
		return cattle;
	} catch (error) {
		console.error("Failed to fetch cattle:", error);
		throw new Error("개체 목록을 불러오지 못했습니다.");
	}
}

export async function getArchivedCattle() {
	await requireAuthenticatedSession();
	try {
		return normalizeCattleActionRows(
			await prisma.cattle.findMany({
				where: { isArchived: true },
				orderBy: { archivedAt: "desc" },
			}),
		);
	} catch (error) {
		console.error("Failed to fetch archived cattle:", error);
		return [];
	}
}

export async function createCattle(data) {
	await requireAuthenticatedSession();
	try {
		if (!data.tagNumber || !data.name) {
			return { success: false, message: "이름과 이력번호는 필수입니다." };
		}

		const validation = validateCattleMutationInput(data);
		if (!validation.success) {
			return validation;
		}

		const payload = validation.data;
		// Row + history + outbox commit atomically: if the outbox insert fails
		// after the cattle row was written, the whole unit rolls back, so the
		// caller's failure response is truthful and a retry won't hit the
		// tagNumber unique constraint for a row the user thinks was never saved.
		const created = await prisma.$transaction(async (tx) => {
			const row = await tx.cattle.create({
				data: {
					tagNumber: payload.tagNumber,
					name: payload.name,
					birthDate: payload.birthDate,
					gender: payload.gender,
					status: payload.status,
					weight: payload.weight,
					buildingId: payload.buildingId,
					penNumber: payload.penNumber,
					memo: payload.memo,
					geneticFather: payload.geneticInfo.father,
					geneticMother: payload.geneticInfo.mother,
					geneticGrade: payload.geneticInfo.grade,
					lastEstrus: payload.lastEstrus,
					pregnancyDate: payload.pregnancyDate,
					purchasePrice: payload.purchasePrice,
					purchaseDate: payload.purchaseDate,
				},
			});

			await recordCattleHistory(
				row.id,
				"purchase",
				new Date(),
				`신규 등록: ${data.name} (${data.tagNumber})`,
				{
					purchasePrice: payload.purchasePrice,
				},
				tx,
			);

			await createOutboxEvent(
				{
					topic: DASHBOARD_EVENT_TOPICS.cattleCreated,
					aggregateId: row.id,
					payload: { tagNumber: payload.tagNumber, name: payload.name },
				},
				tx,
			);

			return row;
		});

		await invalidateHomeCaches({
			summary: true,
			notifications: true,
			cattleListPages: true,
		});
		return { success: true, data: created };
	} catch (error) {
		console.error("Failed to create cattle:", error);
		if (isCattleTagDuplicateError(error)) {
			return { success: false, message: CATTLE_TAG_DUPLICATE_MESSAGE };
		}
		return { success: false, message: "개체를 등록하지 못했습니다." };
	}
}

export async function updateCattle(id, data) {
	await requireAuthenticatedSession();
	try {
		// 변경 전 기존값 조회 (이력 비교용)
		const validation = validateCattleMutationInput(data);
		if (!validation.success) {
			return validation;
		}

		const payload = validation.data;
		// 변경 전 기존값 조회 (이력 비교용)
		const existing = await prisma.cattle.findUnique({ where: { id } });

		const updated = await prisma.$transaction(async (tx) => {
			const row = await tx.cattle.update({
				where: { id },
				data: {
					tagNumber: payload.tagNumber,
					name: payload.name,
					birthDate: payload.birthDate,
					gender: payload.gender,
					status: payload.status,
					weight: payload.weight,
					buildingId: payload.buildingId,
					penNumber: payload.penNumber,
					memo: payload.memo,
					geneticFather: payload.geneticInfo.father,
					geneticMother: payload.geneticInfo.mother,
					geneticGrade: payload.geneticInfo.grade,
					lastEstrus: payload.lastEstrus,
					pregnancyDate: payload.pregnancyDate,
					purchasePrice: payload.purchasePrice,
					purchaseDate: payload.purchaseDate,
				},
			});

			// 상태 변경 이력
			if (existing && existing.status !== payload.status) {
				await recordCattleHistory(
					id,
					"status_change",
					new Date(),
					`상태 변경: ${existing.status} → ${data.status}`,
					{
						from: existing.status,
						to: payload.status,
					},
					tx,
				);
			}
			// 체중 변경 이력
			if (existing && existing.weight !== payload.weight) {
				await recordCattleHistory(
					id,
					"weight",
					new Date(),
					`체중 변경: ${existing.weight}kg → ${data.weight}kg`,
					{
						from: existing.weight,
						to: payload.weight,
					},
					tx,
				);
			}
			// 이동 이력
			if (
				existing &&
				(existing.buildingId !== payload.buildingId ||
					existing.penNumber !== payload.penNumber)
			) {
				await recordCattleHistory(
					id,
					"movement",
					new Date(),
					`이동: ${existing.buildingId} ${existing.penNumber}번 → ${data.buildingId} ${data.penNumber}번`,
					{
						fromBuilding: existing.buildingId,
						fromPen: existing.penNumber,
						toBuilding: payload.buildingId,
						toPen: payload.penNumber,
					},
					tx,
				);
			}

			await createOutboxEvent(
				{
					topic: DASHBOARD_EVENT_TOPICS.cattleUpdated,
					aggregateId: id,
					payload: { tagNumber: payload.tagNumber, name: payload.name },
				},
				tx,
			);

			return row;
		});

		await invalidateHomeCaches({
			summary: true,
			notifications: true,
			cattleListPages: true,
		});
		return { success: true, data: updated };
	} catch (error) {
		console.error("Failed to update cattle:", error);
		if (isCattleTagDuplicateError(error)) {
			return { success: false, message: CATTLE_TAG_DUPLICATE_MESSAGE };
		}
		return { success: false, message: "개체 정보를 수정하지 못했습니다." };
	}
}

export async function recordCalving(data) {
	await requireAuthenticatedSession();
	try {
		const validation = validateCalvingRecordInput(data);
		if (!validation.success) {
			return validation;
		}

		const payload = validation.data;
		const mother = await prisma.cattle.findUnique({
			where: { id: payload.motherId },
		});

		if (!mother || mother.isArchived) {
			return { success: false, message: "분만 대상 개체를 찾을 수 없습니다." };
		}

		const calvingDate = payload.calvingDate;
		const calfTagNumber = payload.calfTagNumber;
		const calfGender = payload.calfGender;
		const nextMemo = mother.memo
			? `${mother.memo}\n[분만] ${calvingDate.toISOString().split("T")[0]} ${calfGender} 송아지 분만`
			: `[분만] ${calvingDate.toISOString().split("T")[0]} ${calfGender} 송아지 분만`;

		const result = await prisma.$transaction(async (tx) => {
			const updatedMother = await tx.cattle.update({
				where: { id: mother.id },
				data: {
					status: "번식우",
					pregnancyDate: null,
					lastEstrus: null,
					memo: nextMemo,
				},
			});

			const calf = await tx.cattle.create({
				data: {
					tagNumber: calfTagNumber,
					name: `${mother.name}의 송아지`,
					birthDate: calvingDate,
					gender: calfGender,
					status: "송아지",
					weight: 25,
					buildingId: mother.buildingId,
					penNumber: mother.penNumber,
					memo: `모체 ${mother.tagNumber} (${mother.name})`,
					geneticFather: mother.geneticFather || "미상",
					geneticMother: mother.tagNumber,
					geneticGrade: "-",
				},
			});

			const historyItems = [
				{
					cattleId: mother.id,
					eventType: "calving",
					eventDate: calvingDate,
					description: `분만 완료: ${calfGender} 송아지 (${calfTagNumber})`,
					metadata: JSON.stringify({
						calfId: calf.id,
						calfTagNumber,
						calfGender,
					}),
				},
			];

			if (mother.status !== "번식우") {
				historyItems.push({
					cattleId: mother.id,
					eventType: "status_change",
					eventDate: calvingDate,
					description: `상태 변경: ${mother.status} → 번식우`,
					metadata: JSON.stringify({
						from: mother.status,
						to: "번식우",
					}),
				});
			}

			await tx.cattleHistory.createMany({
				data: historyItems,
			});

			await createOutboxEvent(
				{
					topic: DASHBOARD_EVENT_TOPICS.cattleUpdated,
					aggregateId: payload.motherId,
					payload: { event: "calving", calfTagNumber },
				},
				tx,
			);

			return {
				mother: updatedMother,
				calf,
			};
		});

		await invalidateHomeCaches({
			summary: true,
			notifications: true,
			cattleListPages: true,
		});
		return { success: true, data: result };
	} catch (error) {
		console.error("Failed to record calving:", error);
		if (isCattleTagDuplicateError(error)) {
			return { success: false, message: CATTLE_TAG_DUPLICATE_MESSAGE };
		}
		return { success: false, message: "분만 처리를 완료하지 못했습니다." };
	}
}

export async function deleteCattle(id) {
	await requireAuthenticatedSession();
	try {
		// 판매기록 있으면 삭제 불가
		const salesCount = await prisma.salesRecord.count({
			where: { cattleId: id },
		});
		if (salesCount > 0) {
			return {
				success: false,
				message: `이 개체에 ${salesCount}건의 판매 기록이 있어 보관 처리할 수 없습니다.`,
			};
		}

		// 소프트 삭제
		await prisma.$transaction(async (tx) => {
			await tx.cattle.update({
				where: { id },
				data: { isArchived: true, archivedAt: new Date() },
			});

			await recordCattleHistory(
				id,
				"status_change",
				new Date(),
				"아카이브 처리됨",
				{ action: "archive" },
				tx,
			);

			await createOutboxEvent(
				{
					topic: DASHBOARD_EVENT_TOPICS.cattleArchived,
					aggregateId: id,
					payload: { action: "archive" },
				},
				tx,
			);
		});

		await invalidateHomeCaches({
			summary: true,
			notifications: true,
			cattleListPages: true,
		});
		return { success: true, data: { id } };
	} catch (error) {
		console.error("Failed to archive cattle:", error);
		return { success: false, message: "개체 보관 처리에 실패했습니다." };
	}
}

// ============================================================
// CattleHistory Actions
// ============================================================

export async function getCattleHistory(cattleId) {
	await requireAuthenticatedSession();
	try {
		const history = await prisma.cattleHistory.findMany({
			where: { cattleId },
			orderBy: { eventDate: "desc" },
		});
		return normalizeCattleHistoryRows(history);
	} catch (error) {
		console.error("Failed to fetch cattle history:", error);
		return [];
	}
}
