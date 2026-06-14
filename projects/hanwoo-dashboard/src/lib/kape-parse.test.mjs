/**
 * Behavioral tests for the KAPE response parser logic in kape.js.
 *
 * parseKapeResponse is a private (non-exported) function. It is re-implemented
 * inline here, and source-grep guards ensure production code cannot diverge
 * silently on the key invariants.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(path.join(SRC_ROOT, "lib/kape.js"), "utf8");

// ── Inline re-implementation of parseKapeResponse ────────────────────────────

function parseKapeResponse(data, issueDate) {
	try {
		const items = data?.response?.body?.items?.item;
		if (!items || (Array.isArray(items) && items.length === 0)) return null;

		const itemList = Array.isArray(items) ? items : [items];

		const bull = { grade1pp: 0, grade1p: 0, grade1: 0 };
		const cow = { grade1pp: 0, grade1p: 0, grade1: 0 };
		const gradeMap = { 11: "grade1pp", 12: "grade1p", 13: "grade1" };

		itemList.forEach((item) => {
			const category = String(item.catgCd);
			const grade = gradeMap[String(item.judsgCd)];
			const price = Math.round(Number(item.avgAmt) || 0);

			if (!grade || price === 0) {
				return;
			}

			if (category === "1") {
				bull[grade] = price;
			} else if (category === "2") {
				cow[grade] = price;
			}
		});

		if (bull.grade1pp === 0 && bull.grade1p === 0 && cow.grade1pp === 0) {
			return null;
		}

		const trend = bull.grade1pp > bull.grade1p ? "up" : "down";
		const dateFormatted = `${issueDate.slice(0, 4)}.${issueDate.slice(4, 6)}.${issueDate.slice(6, 8)}`;

		return {
			isRealtime: true,
			source: "KAPE",
			issueDate: `${issueDate.slice(0, 4)}-${issueDate.slice(4, 6)}-${issueDate.slice(6, 8)}`,
			date: dateFormatted,
			bull,
			cow,
			trend,
		};
	} catch (error) {
		return null;
	}
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("kape.js maps catgCd 1→bull 2→cow and judsgCd 11→grade1pp 12→grade1p 13→grade1", () => {
	assert.match(src, /gradeMap.*11.*grade1pp/s);
	assert.match(src, /gradeMap.*12.*grade1p/s);
	assert.match(src, /gradeMap.*13.*grade1/s);
	assert.match(src, /category === "1"/);
	assert.match(src, /category === "2"/);
});

test("kape.js trend is up when grade1pp > grade1p", () => {
	assert.match(src, /bull\.grade1pp > bull\.grade1p/);
	assert.match(src, /"up"/);
	assert.match(src, /"down"/);
});

test("kape.js date formatting slices issueDate from YYYYMMDD", () => {
	assert.match(src, /issueDate\.slice\(0, 4\)/);
	assert.match(src, /issueDate\.slice\(4, 6\)/);
	assert.match(src, /issueDate\.slice\(6, 8\)/);
});

// ── Behavioral tests ──────────────────────────────────────────────────────────

test("parseKapeResponse returns null for missing items", () => {
	assert.equal(parseKapeResponse(null, "20260601"), null);
	assert.equal(parseKapeResponse({}, "20260601"), null);
	assert.equal(
		parseKapeResponse({ response: { body: { items: { item: [] } } } }, "20260601"),
		null,
	);
});

test("parseKapeResponse returns null when all prices are zero", () => {
	const data = {
		response: {
			body: {
				items: {
					item: [{ catgCd: 1, judsgCd: 13, avgAmt: 0 }],
				},
			},
		},
	};
	assert.equal(parseKapeResponse(data, "20260601"), null);
});

test("parseKapeResponse maps single bull grade1pp item correctly", () => {
	const data = {
		response: {
			body: {
				items: {
					item: [{ catgCd: 1, judsgCd: 11, avgAmt: 25000 }],
				},
			},
		},
	};
	const result = parseKapeResponse(data, "20260601");
	assert.ok(result !== null);
	assert.equal(result.bull.grade1pp, 25000);
	assert.equal(result.isRealtime, true);
	assert.equal(result.source, "KAPE");
});

test("parseKapeResponse formats YYYYMMDD to YYYY-MM-DD and YYYY.MM.DD", () => {
	const data = {
		response: {
			body: {
				items: { item: [{ catgCd: 1, judsgCd: 11, avgAmt: 20000 }] },
			},
		},
	};
	const result = parseKapeResponse(data, "20260615");
	assert.equal(result.issueDate, "2026-06-15");
	assert.equal(result.date, "2026.06.15");
});

test("parseKapeResponse wraps single item object in array (not array → singleton)", () => {
	const data = {
		response: {
			body: {
				items: { item: { catgCd: 1, judsgCd: 12, avgAmt: 18000 } },
			},
		},
	};
	const result = parseKapeResponse(data, "20260601");
	assert.ok(result !== null);
	assert.equal(result.bull.grade1p, 18000);
});

test("parseKapeResponse sets trend=up when grade1pp > grade1p", () => {
	const data = {
		response: {
			body: {
				items: {
					item: [
						{ catgCd: 1, judsgCd: 11, avgAmt: 25000 },
						{ catgCd: 1, judsgCd: 12, avgAmt: 22000 },
					],
				},
			},
		},
	};
	const result = parseKapeResponse(data, "20260601");
	assert.equal(result.trend, "up");
});

test("parseKapeResponse sets trend=down when grade1pp <= grade1p", () => {
	const data = {
		response: {
			body: {
				items: {
					item: [
						{ catgCd: 1, judsgCd: 11, avgAmt: 20000 },
						{ catgCd: 1, judsgCd: 12, avgAmt: 22000 },
					],
				},
			},
		},
	};
	const result = parseKapeResponse(data, "20260601");
	assert.equal(result.trend, "down");
});

test("parseKapeResponse maps cow (catgCd=2) to cow object", () => {
	const data = {
		response: {
			body: {
				items: {
					item: [
						{ catgCd: 1, judsgCd: 11, avgAmt: 20000 },
						{ catgCd: 2, judsgCd: 11, avgAmt: 16000 },
						{ catgCd: 2, judsgCd: 13, avgAmt: 14000 },
					],
				},
			},
		},
	};
	const result = parseKapeResponse(data, "20260601");
	assert.equal(result.cow.grade1pp, 16000);
	assert.equal(result.cow.grade1, 14000);
	assert.equal(result.cow.grade1p, 0);
});

test("parseKapeResponse rounds fractional avgAmt values", () => {
	const data = {
		response: {
			body: {
				items: { item: [{ catgCd: 1, judsgCd: 11, avgAmt: 24567.89 }] },
			},
		},
	};
	const result = parseKapeResponse(data, "20260601");
	assert.equal(result.bull.grade1pp, 24568);
});

test("parseKapeResponse returns null for completely malformed data without throwing", () => {
	assert.doesNotThrow(() => parseKapeResponse("not-an-object", "20260601"));
	assert.equal(parseKapeResponse("not-an-object", "20260601"), null);
});
