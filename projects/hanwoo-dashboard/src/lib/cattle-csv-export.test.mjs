import assert from "node:assert/strict";
import test from "node:test";

import { buildCattleCsvRows } from "./cattle-csv-export.mjs";

test("buildCattleCsvRows exports cattle data with Korean headers", () => {
	const csv = buildCattleCsvRows(
		[
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
				weight: 450,
			},
		],
		[{ id: "barn-1", name: "1번 축사" }],
	);

	assert.match(csv, /개체 번호,이름,이력번호,생년월일,성별,상태,체중\(kg\),축사 이름,칸 번호,메모/);
	assert.match(csv, /복순이/);
	assert.match(csv, /예방접종 확인/);
	assert.match(csv, /450/);
	assert.match(csv, /1번 축사/);
	assert.doesNotMatch(
		csv,
		/\bID\b|Name|Tag Number|Birth Date|Gender|Status|Building ID|Pen Number|Memo/,
	);
});

test("buildCattleCsvRows resolves buildingId to building name", () => {
	const csv = buildCattleCsvRows(
		[
			{
				id: "cow-5",
				name: "황소",
				tagNumber: "410005555555",
				birthDate: "2024-06-01T00:00:00.000Z",
				gender: "수",
				status: "사육중",
				buildingId: "barn-99",
				penNumber: "E-1",
				memo: "",
			},
		],
		[{ id: "barn-99", name: "서쪽 축사" }],
	);

	assert.match(csv, /서쪽 축사/);
	assert.doesNotMatch(csv, /barn-99/);
});

test("buildCattleCsvRows falls back to buildingId when building not found", () => {
	const csv = buildCattleCsvRows(
		[
			{
				id: "cow-6",
				name: "황순",
				tagNumber: "410006666666",
				birthDate: null,
				gender: "암",
				status: "사육중",
				buildingId: "barn-unknown",
				penNumber: "F-1",
				memo: "",
			},
		],
		[],
	);

	assert.match(csv, /barn-unknown/);
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

test("buildCattleCsvRows prefixes formula-start characters to prevent CSV injection", () => {
	const csv = buildCattleCsvRows([
		{
			id: "cow-x",
			name: "=1+1",
			tagNumber: "@HYPERLINK",
			birthDate: null,
			gender: "암",
			status: "+cmd",
			buildingId: "-harm",
			penNumber: 1,
			memo: "=SUM(A1:A10)",
		},
	]);

	// Name starting with = should be prefixed with single quote
	assert.match(csv, /\\'=1\+1|'=1\+1/);
	// @HYPERLINK prefix guard
	assert.match(csv, /'@HYPERLINK/);
	// Status +cmd prefix guard
	assert.match(csv, /'\+cmd/);
	// buildingId -harm prefix guard (no building mapping, falls back to buildingId)
	assert.match(csv, /'-harm/);
	// Memo =SUM gets prefixed
	assert.match(csv, /'=SUM/);
	// Cells should NOT appear as raw formulas
	assert.doesNotMatch(csv, /(?<!'),(?<!'),(?<!'),(?<!'),(?<!'),=1\+1/);
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

test("buildCattleCsvRows starts with UTF-8 BOM for Excel encoding compatibility", () => {
	const csv = buildCattleCsvRows([]);
	// First char of output must be the BOM (U+FEFF)
	assert.equal(csv.charCodeAt(0), 0xfeff, "CSV must start with BOM U+FEFF");
});

test("buildCattleCsvRows resolves building name via buildingName field when name is absent", () => {
	// Prisma may return a different field name depending on the include alias
	const csv = buildCattleCsvRows(
		[
			{
				id: "cow-7",
				name: "임마",
				tagNumber: "410007777777",
				birthDate: null,
				gender: "암",
				status: "사육중",
				buildingId: "barn-alias",
				penNumber: "G-1",
				memo: "",
			},
		],
		[{ id: "barn-alias", buildingName: "별관 축사" }],
	);

	assert.match(csv, /별관 축사/);
	assert.doesNotMatch(csv, /barn-alias/);
});

test("buildCattleCsvRows normalizes memo newlines to single space", () => {
	const csv = buildCattleCsvRows([
		{
			id: "cow-8",
			name: "메모우",
			tagNumber: "410008888888",
			birthDate: null,
			gender: "수",
			status: "사육중",
			buildingId: "barn-8",
			penNumber: "H-1",
			memo: "1행\n2행\t3행",
		},
	]);

	assert.match(csv, /1행 2행 3행/);
	assert.doesNotMatch(csv, /\n.*1행.*\n/); // no raw newline in the memo cell
});
