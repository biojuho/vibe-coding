import assert from "node:assert/strict";
import test from "node:test";

import { buildCattleCsvRows } from "./cattle-csv-export.mjs";

test("buildCattleCsvRows exports cattle data with Korean headers", () => {
	const csv = buildCattleCsvRows([
		{
			id: "cow-1",
			name: "복순이",
			tagNumber: "410001234567",
			birthDate: "2025-01-02T00:00:00.000Z",
			gender: "암",
			status: "사육중",
			buildingId: "barn-1",
			penNumber: "A-1",
			memo: "예방접종, 확인",
		},
	]);

	assert.match(
		csv,
		/^\uFEFF개체 번호,이름,이력번호,생년월일,성별,상태,축사 번호,칸 번호,메모/,
	);
	assert.match(csv, /복순이/);
	assert.match(csv, /예방접종 확인/);
	assert.doesNotMatch(
		csv,
		/\bID\b|Name|Tag Number|Birth Date|Gender|Status|Building ID|Pen Number|Memo/,
	);
});

test("buildCattleCsvRows quotes cells that would otherwise break CSV columns", () => {
	const csv = buildCattleCsvRows([
		{
			id: "cow-2",
			name: '복"실,이',
			tagNumber: "410009999999",
			birthDate: null,
			gender: "암",
			status: "관찰중",
			buildingId: "barn-2",
			penNumber: "B-1",
			memo: "사료, 조정",
		},
	]);

	assert.match(csv, /"복""실,이"/);
	assert.match(csv, /사료 조정/);
});

test("buildCattleCsvRows ignores malformed collection payloads", () => {
	const csv = buildCattleCsvRows([
		null,
		"bad-row",
		{
			id: "cow-4",
			name: "CSV Safe",
			tagNumber: "410001234000",
			birthDate: "2025-02-03T00:00:00.000Z",
			gender: "F",
			status: "active",
			buildingId: "barn-4",
			penNumber: "D-1",
			memo: "OK",
		},
	]);

	assert.match(csv, /cow-4/);
	assert.doesNotMatch(csv, /bad-row/);

	const headerOnlyCsv = buildCattleCsvRows("not-an-array");

	assert.equal(headerOnlyCsv.split("\n").length, 1);
	assert.doesNotMatch(headerOnlyCsv, /not-an-array/);
});
