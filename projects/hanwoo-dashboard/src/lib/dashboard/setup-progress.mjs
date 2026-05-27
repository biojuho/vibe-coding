function hasText(value) {
	return typeof value === "string" && value.trim().length > 0;
}

function countItems(value) {
	return Array.isArray(value)
		? value.filter((item) => item && typeof item === "object").length
		: 0;
}

export function buildSetupProgressItems({
	farmSettings = {},
	buildings = [],
	cattleList = [],
	inventoryList = [],
	scheduleEvents = [],
} = {}) {
	const items = [
		{
			id: "farm-profile",
			title: "농장 기본 정보",
			detail:
				hasText(farmSettings?.name) && hasText(farmSettings?.location)
					? `${farmSettings.name} · ${farmSettings.location}`
					: "농장명과 지역을 설정하면 날씨·알림 기준이 정확해집니다.",
			done: hasText(farmSettings?.name) && hasText(farmSettings?.location),
			targetTab: "settings",
		},
		{
			id: "buildings",
			title: "축사 구조",
			detail:
				countItems(buildings) > 0
					? `${countItems(buildings)}개 축사 등록됨`
					: "축사와 칸을 먼저 잡아야 개체 배치가 쉬워집니다.",
			done: countItems(buildings) > 0,
			targetTab: "settings",
			actionId: "add-building",
		},
		{
			id: "cattle",
			title: "개체 등록",
			detail:
				countItems(cattleList) > 0
					? `${countItems(cattleList)}두 관리 중`
					: "첫 개체를 등록하면 사료·분만·출하 흐름이 연결됩니다.",
			done: countItems(cattleList) > 0,
			actionId: "add-cattle",
		},
		{
			id: "inventory",
			title: "재고 기준",
			detail:
				countItems(inventoryList) > 0
					? `${countItems(inventoryList)}개 품목 추적 중`
					: "사료와 약품을 등록하면 부족 알림을 받을 수 있습니다.",
			done: countItems(inventoryList) > 0,
			targetTab: "inventory",
		},
		{
			id: "schedule",
			title: "첫 일정",
			detail:
				countItems(scheduleEvents) > 0
					? `${countItems(scheduleEvents)}개 일정 등록됨`
					: "접종·검진·출하 예정일을 캘린더에 올려두세요.",
			done: countItems(scheduleEvents) > 0,
			targetTab: "schedule",
		},
	];

	const completed = items.filter((item) => item.done).length;

	return {
		completed,
		total: items.length,
		percent: Math.round((completed / items.length) * 100),
		items,
		nextItem: items.find((item) => !item.done) || null,
	};
}
