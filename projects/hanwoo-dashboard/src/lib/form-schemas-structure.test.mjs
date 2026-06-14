import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

function readSource(relativePath) {
	return readFileSync(path.join(SRC_ROOT, relativePath), "utf8");
}

const source = readSource("lib/formSchemas.js");

test("cattleFormSchema validates core required fields with Korean error messages", () => {
	assert.match(source, /cattleFormSchema\s*=\s*z\.object\(/);
	assert.match(source, /name:\s*requiredText\("[^"]+", 40\)/);
	assert.match(source, /tagNumber:\s*requiredText\("[^"]+", 30\)/);
	assert.match(source, /buildingId:\s*requiredText\("[^"]+", 40\)/);
	assert.match(source, /개체 이름을 입력해 주세요/);
	assert.match(source, /이력번호를 입력해 주세요/);
	assert.match(source, /축사를 선택해 주세요/);
});

test("cattleFormSchema validates numeric fields with range checks", () => {
	assert.match(source, /penNumber:\s*z\.preprocess/);
	assert.match(source, /\.min\(1,\s*"칸 번호를 선택해 주세요\."\)/);
	assert.match(source, /\.max\(99,\s*"칸 번호를 확인해 주세요\."\)/);
	assert.match(source, /weight:\s*z\.preprocess/);
	assert.match(source, /체중은 0보다 커야 합니다/);
});

test("formSchemas exports all 8 schema objects", () => {
	const schemas = [
		"cattleFormSchema",
		"scheduleEventSchema",
		"inventoryItemSchema",
		"salesFormSchema",
		"feedRecordSchema",
		"calvingRecordSchema",
		"buildingFormSchema",
		"farmSettingsSchema",
	];
	for (const schema of schemas) {
		assert.ok(
			source.includes(schema),
			`Missing schema export: ${schema}`,
		);
	}
});

test("formSchemas exports 8 createXxxValues factory functions", () => {
	const factories = [
		"createCattleFormValues",
		"createScheduleFormValues",
		"createInventoryFormValues",
		"createSalesFormValues",
		"createFeedRecordValues",
		"createCalvingFormValues",
		"createBuildingFormValues",
		"createFarmSettingsValues",
	];
	for (const factory of factories) {
		assert.ok(
			source.includes(factory),
			`Missing factory: ${factory}`,
		);
	}
});

test("formSchemas uses pastOrTodayDateString for date fields to block future dates", () => {
	// pastOrTodayDateString is an arrow-function const, not a named function declaration
	assert.match(source, /const pastOrTodayDateString\s*=/);
	assert.match(source, /이후일 수 없습니다/);
	assert.match(source, /birthDate:\s*pastOrTodayDateString\(/);
});

test("formSchemas rejects empty strings via requiredText helper", () => {
	// requiredText is an arrow-function const using z.string().trim().min(1)
	assert.match(source, /const requiredText\s*=/);
	assert.match(source, /z\.string\(\)\.trim\(\)\.min\(1,\s*message\)/);
	// optionalText uses emptyToUndefined through z.preprocess
	assert.match(source, /const emptyToUndefined\s*=/);
	assert.match(source, /z\.preprocess\(\s*emptyToUndefined/);
});
