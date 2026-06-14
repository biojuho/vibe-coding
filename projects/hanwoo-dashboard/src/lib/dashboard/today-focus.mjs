function startOfDay(value) {
	const date = value instanceof Date ? new Date(value) : new Date(value);
	date.setHours(0, 0, 0, 0);
	return date;
}

function toValidDate(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? null : date;
}

function toFiniteNumberOrNull(value) {
	if (value === null || value === undefined || value === "") {
		return null;
	}

	const amount = Number(value);
	return Number.isFinite(amount) ? amount : null;
}

function toObjectRows(value) {
	return Array.isArray(value)
		? value.filter(
				(item) => item && typeof item === "object" && !Array.isArray(item),
			)
		: [];
}

function normalizeTodayFocusOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function isLowStock(item) {
	const quantity = toFiniteNumberOrNull(item?.quantity);
	const threshold = toFiniteNumberOrNull(item?.threshold);
	return quantity !== null && threshold !== null && quantity <= threshold;
}

function isFeedCategory(item) {
	if (!item || typeof item !== "object" || Array.isArray(item)) return false;
	const category =
		typeof item.category === "string" ? item.category.toLowerCase() : "";
	return (
		category === "feed" || category === "concentrate" || category === "roughage"
	);
}

function getInventoryItemKey(item) {
	if (!item || typeof item !== "object" || Array.isArray(item)) return null;
	if (item.id !== null && item.id !== undefined && item.id !== "") {
		return `id:${String(item.id)}`;
	}

	const name = typeof item.name === "string" ? item.name.trim() : "";
	return name.length > 0 ? `name:${name.toLowerCase()}` : null;
}

/**
 * Predict per-day feed consumption from the recent feed log.
 *
 * Inputs:
 *  - feedHistory: array of { date, roughage, concentrate, ... }
 *  - lookbackDays: how many days back to consider (default 30)
 *  - now: reference "today"
 *
 * Returns kg/day (number), or null if there isn't enough data to predict.
 */
export function estimateDailyFeedConsumptionKg(options = {}) {
	const {
		feedHistory = [],
		lookbackDays = 30,
		now = new Date(),
	} = normalizeTodayFocusOptions(options);
	const safeLookbackDays =
		Number.isFinite(lookbackDays) && lookbackDays > 0 ? lookbackDays : 30;
	if (!Array.isArray(feedHistory) || feedHistory.length === 0) return null;
	const today = startOfDay(now);
	const cutoff = new Date(today.getTime() - safeLookbackDays * 86400000);

	let totalKg = 0;
	let samples = 0;
	for (const record of feedHistory) {
		if (!record || typeof record !== "object" || Array.isArray(record)) {
			continue;
		}
		const date = toValidDate(record.date);
		if (!date || date < cutoff || date > today) continue;
		const roughage = toFiniteNumberOrNull(record.roughage) ?? 0;
		const concentrate = toFiniteNumberOrNull(record.concentrate) ?? 0;
		if (roughage <= 0 && concentrate <= 0) continue;
		totalKg += roughage + concentrate;
		samples += 1;
	}

	if (samples === 0) return null;
	return totalKg / safeLookbackDays;
}

function formatDaysLeft(target, today) {
	const daysLeft = Math.ceil((startOfDay(target) - today) / 86400000);
	if (daysLeft <= 0) return "오늘";
	if (daysLeft === 1) return "내일";
	return `${daysLeft}일 남음`;
}

function buildFeedDepletionFocusItem(options = {}) {
	const {
		inventoryList = [],
		feedHistory = [],
		now = new Date(),
	} = normalizeTodayFocusOptions(options);
	const dailyFeedKg = estimateDailyFeedConsumptionKg({ feedHistory, now });
	if (dailyFeedKg === null || dailyFeedKg <= 0) return null;

	const projections = toObjectRows(inventoryList)
		.filter(isFeedCategory)
		.map((item) => {
			const quantity = toFiniteNumberOrNull(item?.quantity);
			if (quantity === null || quantity <= 0) return null;
			const daysRemaining = quantity / dailyFeedKg;
			return { item, daysRemaining };
		})
		.filter(Boolean)
		.sort((a, b) => a.daysRemaining - b.daysRemaining);

	const soonest = projections[0];
	if (!soonest || soonest.daysRemaining > 14) return null;

	const daysLabel = Math.max(0, Math.floor(soonest.daysRemaining));
	const critical = soonest.daysRemaining <= 7;
	return {
		item: {
			id: "feed-depletion",
			type: "stock",
			title: critical
				? `사료 ${daysLabel}일 후 소진 예상`
				: `사료 잔여 ${daysLabel}일, 재고를 점검해 주세요`,
			detail: `${soonest.item.name}: ${soonest.item.quantity}${soonest.item.unit || ""} (최근 사용량 기준)`,
			meta: "사료 발주",
			tone: critical ? "danger" : "warning",
			targetTab: "inventory",
		},
		inventoryItem: soonest.item,
		inventoryKey: getInventoryItemKey(soonest.item),
	};
}

export function buildTodayFocusItems(options = {}) {
	const {
		notifications = [],
		scheduleEvents = [],
		inventoryList = [],
		feedHistory = [],
		monthlySalesCount = 0,
		isOnline = true,
		now = new Date(),
	} = normalizeTodayFocusOptions(options);
	const today = startOfDay(now);
	const items = [];
	const safeNotifications = toObjectRows(notifications);
	const safeScheduleEvents = toObjectRows(scheduleEvents);
	const safeInventoryList = toObjectRows(inventoryList);
	const feedDepletion = buildFeedDepletionFocusItem({
		inventoryList: safeInventoryList,
		feedHistory,
		now,
	});
	const feedDepletionInventoryKey = feedDepletion?.inventoryKey ?? null;

	if (!isOnline) {
		items.push({
			id: "offline",
			type: "offline",
			title: "오프라인 작업 대기",
			detail: "연결이 복구되면 저장된 작업을 자동 동기화합니다.",
			meta: "동기화 확인",
			tone: "warning",
			targetTab: "settings",
		});
	}

	const criticalNotifications = safeNotifications.filter(
		(notification) => notification.level === "critical",
	);
	if (criticalNotifications.length > 0) {
		const first = criticalNotifications[0];
		items.push({
			id: "critical-alerts",
			type: "alert",
			title: `${criticalNotifications.length}건의 긴급 알림`,
			detail: first.message || first.title || "발정/분만 알림을 확인해 주세요.",
			meta: "알림 보기",
			tone: "danger",
			targetTab: "home",
		});
	}

	const nextEvent = safeScheduleEvents
		.map((event) => ({ event, date: toValidDate(event.date) }))
		.filter(({ event, date }) => date && !event.isCompleted && date >= today)
		.sort((first, second) => first.date - second.date)[0]?.event;
	if (nextEvent) {
		items.push({
			id: "next-schedule",
			type: "schedule",
			title: nextEvent.title,
			detail: `${formatDaysLeft(nextEvent.date, today)} 예정`,
			meta: "일정 열기",
			tone: "info",
			targetTab: "schedule",
		});
	}

	const lowStockItems = safeInventoryList.filter((item) => {
		if (!isLowStock(item)) return false;
		if (feedDepletion?.inventoryItem === item) return false;
		return (
			feedDepletionInventoryKey === null ||
			getInventoryItemKey(item) !== feedDepletionInventoryKey
		);
	});
	if (lowStockItems.length > 0) {
		const first = lowStockItems[0];
		items.push({
			id: "low-stock",
			type: "stock",
			title: `${lowStockItems.length}개 재고 부족`,
			detail: `${first.name}: ${first.quantity}${first.unit || ""} 남음`,
			meta: "재고 보충",
			tone: "warning",
			targetTab: "inventory",
		});
	}

	// Predict feed depletion from actual feed-log consumption — surfaces a
	// "사료가 N일 후 떨어집니다" warning before the operator-set threshold
	// catches it. Only fires for feed-category inventory rows.
	if (feedDepletion) {
		items.push(feedDepletion.item);
	}

	items.push({
		id: "monthly-sales",
		type: "sales",
		title: `이번 달 출하 ${monthlySalesCount}두`,
		detail:
			monthlySalesCount > 0
				? "판매 흐름을 분석 탭에서 확인해 주세요."
				: "출하 기록을 추가하면 월간 흐름이 살아납니다.",
		meta: monthlySalesCount > 0 ? "분석 보기" : "출하 기록",
		tone: monthlySalesCount > 0 ? "success" : "neutral",
		targetTab: monthlySalesCount > 0 ? "analysis" : "sales",
		actionId: monthlySalesCount > 0 ? undefined : "record-sale",
	});

	return items.slice(0, 5);
}
