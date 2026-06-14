import { buildNotificationTiming } from "./notification-timing.mjs";
import {
	getDaysUntilCalving,
	getDaysUntilEstrus,
	isCalvingAlert,
	isEstrusAlert,
} from "./utils";

function isNotificationCattleRow(row) {
	return row && typeof row === "object" && !Array.isArray(row);
}

function normalizeNotificationCattle(cattle) {
	return Array.isArray(cattle) ? cattle.filter(isNotificationCattleRow) : [];
}

function isLowStock(item) {
	if (!item || typeof item !== "object" || Array.isArray(item)) return false;
	const qty = Number(item.quantity);
	const thr = Number(item.threshold);
	return Number.isFinite(qty) && Number.isFinite(thr) && thr > 0 && qty <= thr;
}

export function buildNotifications(cattle = [], inventory = []) {
	const notifications = [];
	const safeCattle = normalizeNotificationCattle(cattle);

	safeCattle.forEach((cow) => {
		if (
			(cow.status === "번식우" || cow.status === "육성우") &&
			cow.lastEstrus &&
			isEstrusAlert(cow.lastEstrus)
		) {
			const daysLeft = getDaysUntilEstrus(cow.lastEstrus);
			const timing = buildNotificationTiming("estrus", cow.lastEstrus);

			notifications.push({
				id: `estrus-${cow.id}`,
				type: "estrus",
				level: daysLeft <= 1 ? "critical" : "warning",
				title: daysLeft === 0 ? "오늘 발정 예정" : "발정 임박",
				message: `${cow.name ?? "이름 없음"} (${cow.tagNumber ?? "번호 없음"}) 발정 예정일이 ${daysLeft}일 남았습니다.`,
				daysLeft,
				cattleId: cow.id,
				cattleName: cow.name ?? null,
				tagNumber: cow.tagNumber ?? null,
				buildingId: cow.buildingId,
				penNumber: cow.penNumber,
				...timing,
			});
		}

		if (
			cow.status === "임신우" &&
			cow.pregnancyDate &&
			isCalvingAlert(cow.pregnancyDate)
		) {
			const daysLeft = getDaysUntilCalving(cow.pregnancyDate);
			const timing = buildNotificationTiming("calving", cow.pregnancyDate);

			notifications.push({
				id: `calving-${cow.id}`,
				type: "calving",
				level: daysLeft <= 3 ? "critical" : "warning",
				title: daysLeft === 0 ? "오늘 분만 예정" : "분만 임박",
				message: `${cow.name ?? "이름 없음"} (${cow.tagNumber ?? "번호 없음"}) 분만 예정일이 ${daysLeft}일 남았습니다.`,
				daysLeft,
				cattleId: cow.id,
				cattleName: cow.name ?? null,
				tagNumber: cow.tagNumber ?? null,
				buildingId: cow.buildingId,
				penNumber: cow.penNumber,
				...timing,
			});
		}
	});

	// Inventory low-stock alerts
	if (Array.isArray(inventory)) {
		inventory.filter(isLowStock).forEach((item) => {
			const name =
				typeof item.name === "string" ? item.name.trim() : "재고 항목";
			const qty = Number(item.quantity);
			const thr = Number(item.threshold);
			const isCritical = qty === 0;
			notifications.push({
				id: `inventory-${item.id ?? name}`,
				type: "alert",
				level: isCritical ? "critical" : "warning",
				title: isCritical ? "재고 소진" : "재고 부족",
				message: isCritical
					? `${name} 재고가 소진되었습니다. 즉시 보충이 필요합니다.`
					: `${name} 재고가 ${qty}${item.unit ?? ""}로 기준(${thr}${item.unit ?? ""})에 미달합니다.`,
				inventoryId: item.id,
				inventoryName: name,
			});
		});
	}

	notifications.sort((a, b) => {
		if (a.level === "critical" && b.level !== "critical") return -1;
		if (a.level !== "critical" && b.level === "critical") return 1;
		return 0;
	});

	return notifications;
}
