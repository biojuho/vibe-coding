export function buildCattleCsvRows(cattleList, buildings = []) {
	const headers = [
		"개체 번호",
		"이름",
		"이력번호",
		"생년월일",
		"성별",
		"상태",
		"체중(kg)",
		"축사 이름",
		"칸 번호",
		"메모",
	];

	const buildingMap = Array.isArray(buildings)
		? Object.fromEntries(buildings.map((b) => [b.id, b.name || b.buildingName || ""]))
		: {};

	const safeCattleList = normalizeCattleCsvRows(cattleList);

	const rows = safeCattleList.map((cattle) => [
		cattle.id,
		cattle.name,
		cattle.tagNumber,
		formatCsvDate(cattle.birthDate),
		cattle.gender || "",
		cattle.status || "",
		cattle.weight != null ? String(cattle.weight) : "",
		buildingMap[cattle.buildingId] || cattle.buildingId || "",
		cattle.penNumber || "",
		(cattle.memo || "").replace(/,/g, " ").replace(/\s+/g, " ").trim(),
	]);

	return [
		"\uFEFF" + headers.join(","),
		...rows.map((row) => row.map(formatCsvCell).join(",")),
	].join("\n");
}

function normalizeCattleCsvRows(cattleList) {
	return Array.isArray(cattleList)
		? cattleList.filter(
				(cattle) =>
					cattle && typeof cattle === "object" && !Array.isArray(cattle),
			)
		: [];
}

function formatCsvDate(value) {
	if (!value) {
		return "";
	}

	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString("ko-KR");
}

function formatCsvCell(value) {
	const text = String(value ?? "");
	if (!/[",\r\n]/.test(text)) {
		return text;
	}
	return `"${text.replace(/"/g, '""')}"`;
}
