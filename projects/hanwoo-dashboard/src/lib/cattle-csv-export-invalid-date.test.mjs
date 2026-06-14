import assert from "node:assert/strict";
import test from "node:test";

import { buildCattleCsvRows } from "./cattle-csv-export.mjs";

test("buildCattleCsvRows leaves malformed birth dates blank", () => {
	const csv = buildCattleCsvRows([
		{
			id: "cow-3",
			name: "날짜깨짐",
			tagNumber: "410001111111",
			birthDate: "not-a-date",
			gender: "암",
			status: "사육중",
			buildingId: "barn-3",
			penNumber: "C-1",
			memo: "",
		},
	]);

	assert.match(csv, /cow-3,날짜깨짐,410001111111,,암,사육중,,barn-3,C-1,/);
	assert.doesNotMatch(csv, /Invalid Date/);
});
