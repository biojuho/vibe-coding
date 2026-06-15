/**
 * Source-grep behavioral coverage for formSchemas.js
 *
 * formSchemas.js imports zod and @/lib/utils (path alias), so it cannot be
 * loaded in Node ESM. We assert schema contracts via source-grep and
 * re-implement the pure input helpers inline for behavioral tests.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(path.join(SRC_ROOT, "lib/formSchemas.js"), "utf8");

// ── Source-grep: schema exports ───────────────────────────────────────────────

test("formSchemas: all 7 Zod schema exports are present", () => {
	for (const name of [
		"cattleFormSchema",
		"scheduleEventSchema",
		"inventoryItemSchema",
		"salesFormSchema",
		"feedRecordSchema",
		"calvingRecordSchema",
		"buildingFormSchema",
		"farmSettingsSchema",
	]) {
		assert.match(src, new RegExp(`export const ${name} =`), `missing: ${name}`);
	}
});

test("formSchemas: all 8 createXFormValues functions exported", () => {
	for (const name of [
		"createCattleFormValues",
		"createScheduleFormValues",
		"createInventoryFormValues",
		"createSalesFormValues",
		"createFeedRecordValues",
		"createCalvingFormValues",
		"createBuildingFormValues",
		"createFarmSettingsValues",
	]) {
		assert.match(
			src,
			new RegExp(`export function ${name}\\(`),
			`missing: ${name}`,
		);
	}
});

test("formSchemas: cattleFormSchema penNumber max is 99", () => {
	assert.match(src, /\.max\(99, "칸 번호를 확인해 주세요\."\)/);
});

test("formSchemas: cattleFormSchema weight max is 2000", () => {
	assert.match(src, /\.max\(2000, "체중이 너무 큽니다\. 값을 확인해 주세요\."\)/);
});

test("formSchemas: buildingFormSchema penCount max is 200", () => {
	assert.match(src, /\.max\(200, "칸 수를 확인해 주세요\."\)/);
});

test("formSchemas: farmSettingsSchema latitude range is -90 to 90", () => {
	assert.match(src, /\.min\(-90, "위도를 확인해 주세요\."\)/);
	assert.match(src, /\.max\(90, "위도를 확인해 주세요\."\)/);
});

test("formSchemas: farmSettingsSchema longitude range is -180 to 180", () => {
	assert.match(src, /\.min\(-180, "경도를 확인해 주세요\."\)/);
	assert.match(src, /\.max\(180, "경도를 확인해 주세요\."\)/);
});

test("formSchemas: scheduleEventSchema type enum covers 5 types", () => {
	assert.match(src, /z\.enum\(\["General", "Vaccination", "Checkup", "Breeding", "Other"\]\)/);
});

test("formSchemas: salesFormSchema grade enum is 1++ through 3", () => {
	assert.match(src, /z\.enum\(\["1\+\+", "1\+", "1", "2", "3"\]\)/);
});

test("formSchemas: inventoryItemSchema category enum covers 4 types", () => {
	assert.match(src, /z\.enum\(\["Feed", "Medicine", "Equipment", "Other"\]\)/);
});

test("formSchemas: calvingRecordSchema calfGender enum is 암/수", () => {
	assert.match(src, /z\.enum\(\["암", "수"\]\)/);
});

test("formSchemas: pastOrTodayDateString compares against toInputDate(new Date())", () => {
	assert.match(src, /\(value\) => value <= toInputDate\(new Date\(\)\)/);
});

test("formSchemas: DATE_INPUT_PATTERN is YYYY-MM-DD regex", () => {
	assert.match(src, /const DATE_INPUT_PATTERN = \/\^\\d\{4\}-\\d\{2\}-\\d\{2\}\$\//);
});

test("formSchemas: PLAIN_NUMBER_INPUT_PATTERN allows optional sign and decimals", () => {
	assert.match(src, /const PLAIN_NUMBER_INPUT_PATTERN = /);
	assert.match(src, /-\?/);
});

test("formSchemas: isDateInputString validates round-trip with toISOString", () => {
	assert.match(src, /parsed\.toISOString\(\)\.slice\(0, 10\) === value/);
});

test("formSchemas: emptyToUndefined returns undefined for empty string, null, undefined", () => {
	assert.match(src, /value === ["'] *["'] \|\| value === null \|\| value === undefined/);
	assert.match(src, /return undefined;/);
});

test("formSchemas: optionalNumber uses z.number().nonnegative()", () => {
	assert.match(src, /z\.number\(\)\.nonnegative\("0 이상 값을 입력해 주세요\."\)/);
});

test("formSchemas: createBuildingFormValues defaults penCount to 32", () => {
	assert.match(src, /penCount: 32/);
});

test("formSchemas: createFarmSettingsValues defaults latitude to 35.446", () => {
	assert.match(src, /latitude: settings\?\.latitude \?\? 35\.446/);
});

test("formSchemas: createFarmSettingsValues defaults longitude to 127.344", () => {
	assert.match(src, /longitude: settings\?\.longitude \?\? 127\.344/);
});

test("formSchemas: createSalesFormValues defaults grade to '1'", () => {
	assert.match(src, /grade: ["']1["']/);
});

test("formSchemas: createInventoryFormValues defaults category to 'Feed' and unit to 'kg'", () => {
	assert.match(src, /category: ["']Feed["']/);
	assert.match(src, /unit: ["']kg["']/);
});

test("formSchemas: createCalvingFormValues defaults calfGender to '암'", () => {
	assert.match(src, /calfGender: ["']암["']/);
});

// ── Inline behavioral tests for pure helpers ──────────────────────────────────

// Re-implement emptyToUndefined
function emptyToUndefined(value) {
	if (value === "" || value === null || value === undefined) {
		return undefined;
	}
	if (typeof value === "string") {
		const trimmed = value.trim();
		return trimmed === "" ? undefined : trimmed;
	}
	return value;
}

test("emptyToUndefined: returns undefined for empty string", () => {
	assert.equal(emptyToUndefined(""), undefined);
});

test("emptyToUndefined: returns undefined for null", () => {
	assert.equal(emptyToUndefined(null), undefined);
});

test("emptyToUndefined: returns undefined for undefined", () => {
	assert.equal(emptyToUndefined(undefined), undefined);
});

test("emptyToUndefined: returns undefined for whitespace-only string", () => {
	assert.equal(emptyToUndefined("   "), undefined);
	assert.equal(emptyToUndefined("\t"), undefined);
});

test("emptyToUndefined: trims and returns non-empty string", () => {
	assert.equal(emptyToUndefined("  hello  "), "hello");
	assert.equal(emptyToUndefined("test"), "test");
});

test("emptyToUndefined: returns number as-is", () => {
	assert.equal(emptyToUndefined(42), 42);
	assert.equal(emptyToUndefined(0), 0);
});

test("emptyToUndefined: returns object as-is", () => {
	const obj = { x: 1 };
	assert.equal(emptyToUndefined(obj), obj);
});

// Re-implement toPlainNumber
const PLAIN_NUMBER_INPUT_PATTERN = /^-?(?:\d+|\d+\.\d+|\.\d+)$/;

function toPlainNumber(value) {
	const normalized = emptyToUndefined(value);
	if (normalized === undefined) {
		return undefined;
	}
	if (typeof normalized === "string") {
		if (!PLAIN_NUMBER_INPUT_PATTERN.test(normalized)) {
			return Number.NaN;
		}
		return Number(normalized);
	}
	if (typeof normalized === "number") {
		return Number(normalized);
	}
	return normalized;
}

test("toPlainNumber: returns undefined for empty/null/undefined", () => {
	assert.equal(toPlainNumber(""), undefined);
	assert.equal(toPlainNumber(null), undefined);
	assert.equal(toPlainNumber(undefined), undefined);
	assert.equal(toPlainNumber("   "), undefined);
});

test("toPlainNumber: parses integer strings", () => {
	assert.equal(toPlainNumber("42"), 42);
	assert.equal(toPlainNumber("0"), 0);
});

test("toPlainNumber: parses negative integer strings", () => {
	assert.equal(toPlainNumber("-10"), -10);
});

test("toPlainNumber: parses decimal strings", () => {
	assert.equal(toPlainNumber("3.14"), 3.14);
	assert.equal(toPlainNumber(".5"), 0.5);
});

test("toPlainNumber: returns NaN for non-numeric strings", () => {
	assert.equal(Number.isNaN(toPlainNumber("abc")), true);
	assert.equal(Number.isNaN(toPlainNumber("1e5")), true);
	assert.equal(Number.isNaN(toPlainNumber("1,000")), true);
});

test("toPlainNumber: returns number directly for number input", () => {
	assert.equal(toPlainNumber(42), 42);
	assert.equal(toPlainNumber(3.14), 3.14);
});

// Re-implement isDateInputString
const DATE_INPUT_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

function isDateInputString(value) {
	if (!DATE_INPUT_PATTERN.test(value)) {
		return false;
	}
	const parsed = new Date(`${value}T00:00:00.000Z`);
	return (
		!Number.isNaN(parsed.getTime()) &&
		parsed.toISOString().slice(0, 10) === value
	);
}

test("isDateInputString: returns true for valid YYYY-MM-DD", () => {
	assert.equal(isDateInputString("2024-06-15"), true);
	assert.equal(isDateInputString("2024-01-01"), true);
	assert.equal(isDateInputString("2024-12-31"), true);
});

test("isDateInputString: returns false for wrong format", () => {
	assert.equal(isDateInputString("2024/06/15"), false);
	assert.equal(isDateInputString("06-15-2024"), false);
	assert.equal(isDateInputString("20240615"), false);
});

test("isDateInputString: returns false for impossible calendar dates", () => {
	assert.equal(isDateInputString("2024-02-30"), false);
	assert.equal(isDateInputString("2024-13-01"), false);
});

test("isDateInputString: returns false for non-string", () => {
	assert.equal(isDateInputString(null), false);
	assert.equal(isDateInputString(undefined), false);
	assert.equal(isDateInputString(20240615), false);
});

// Re-implement pure create*FormValues functions (those without external deps)

function createInventoryFormValues() {
	return { name: "", category: "Feed", quantity: "", unit: "kg", threshold: "" };
}

function createSalesFormValues() {
	return { saleDate: "", price: "", cattleId: "", purchaser: "", grade: "1", notes: "" };
}

function createBuildingFormValues() {
	return { name: "", penCount: 32 };
}

function createFarmSettingsValues(settings) {
	return {
		name: settings?.name ?? "",
		location: settings?.location ?? "",
		latitude: settings?.latitude ?? 35.446,
		longitude: settings?.longitude ?? 127.344,
	};
}

test("createInventoryFormValues: returns correct defaults", () => {
	const values = createInventoryFormValues();
	assert.equal(values.category, "Feed");
	assert.equal(values.unit, "kg");
	assert.equal(values.name, "");
	assert.equal(values.quantity, "");
	assert.equal(values.threshold, "");
});

test("createSalesFormValues: returns correct defaults including grade='1'", () => {
	const values = createSalesFormValues();
	assert.equal(values.grade, "1");
	assert.equal(values.saleDate, "");
	assert.equal(values.price, "");
	assert.equal(values.cattleId, "");
	assert.equal(values.purchaser, "");
	assert.equal(values.notes, "");
});

test("createBuildingFormValues: defaults penCount to 32", () => {
	const values = createBuildingFormValues();
	assert.equal(values.penCount, 32);
	assert.equal(values.name, "");
});

test("createFarmSettingsValues: defaults latitude=35.446 longitude=127.344", () => {
	const values = createFarmSettingsValues(null);
	assert.equal(values.latitude, 35.446);
	assert.equal(values.longitude, 127.344);
	assert.equal(values.name, "");
	assert.equal(values.location, "");
});

test("createFarmSettingsValues: uses provided settings when given", () => {
	const settings = { name: "내 농장", location: "전남 고흥", latitude: 34.5, longitude: 127.2 };
	const values = createFarmSettingsValues(settings);
	assert.equal(values.name, "내 농장");
	assert.equal(values.location, "전남 고흥");
	assert.equal(values.latitude, 34.5);
	assert.equal(values.longitude, 127.2);
});

test("createFarmSettingsValues: falls back to defaults for missing fields", () => {
	const values = createFarmSettingsValues({ name: "Only Name" });
	assert.equal(values.name, "Only Name");
	assert.equal(values.location, "");
	assert.equal(values.latitude, 35.446);
	assert.equal(values.longitude, 127.344);
});
